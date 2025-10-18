use async_trait::async_trait;
use reqwest::Client;
use serde::{Deserialize, Serialize};
use anyhow::Result;
use chrono::Utc;

use crate::providers::{LLMProvider, ParseRequest, ParsedResult};

#[derive(Debug, Serialize)]
struct OllamaRequest {
    model: String,
    prompt: String,
    stream: bool,
    options: OllamaOptions,
}

#[derive(Debug, Serialize)]
struct OllamaOptions {
    temperature: f32,
    num_predict: usize,
}

#[derive(Debug, Deserialize)]
struct OllamaResponse {
    response: String,
}

pub struct OllamaProvider {
    client: Client,
    base_url: String,
    model: String,
    max_tokens: usize,
    temperature: f32,
}

impl OllamaProvider {
    pub fn new(base_url: String, model: String) -> Self {
        Self {
            client: Client::new(),
            base_url,
            model,
            max_tokens: 2000,
            temperature: 0.1,
        }
    }

    fn build_prompt(&self, request: &ParseRequest) -> String {
        format!(
            "Parse tool output into structured JSON. Tool: {}, Target: {}\n\n\
            Rules:\n\
            1. Extract only factual information from the output\n\
            2. Return valid JSON only - no explanations\n\
            3. Use this schema: {{\"findings\":[{{\"type\":\"\",\"data\":{{}},\"severity\":\"\"}}],\"summary\":\"\",\"confidence\":0.0}}\n\
            4. Types: port, service, dns, vulnerability, error\n\
            5. Severity: info, low, medium, high, critical\n\
            6. If no data, return {{\"findings\":[],\"summary\":\"No actionable data\",\"confidence\":0.0}}\n\n\
            Output:\n{}",
            request.tool_name,
            request.target,
            request.raw_output
        )
    }

    async fn check_model_available(&self) -> bool {
        let url = format!("{}/api/tags", self.base_url);
        match self.client.get(&url).send().await {
            Ok(response) => {
                if response.status().is_success() {
                    if let Ok(models) = response.json::<serde_json::Value>().await {
                        if let Some(model_list) = models["models"].as_array() {
                            return model_list.iter().any(|m| {
                                m["name"].as_str().unwrap_or("") == self.model
                            });
                        }
                    }
                }
                false
            }
            Err(_) => false,
        }
    }
}

#[async_trait]
impl LLMProvider for OllamaProvider {
    async fn parse(&self, request: ParseRequest) -> Result<ParsedResult> {
        // Check if model is available
        if !self.check_model_available().await {
            return Err(anyhow::anyhow!("Model {} not available in Ollama", self.model));
        }

        let prompt = self.build_prompt(&request);
        
        let ollama_request = OllamaRequest {
            model: self.model.clone(),
            prompt,
            stream: false,
            options: OllamaOptions {
                temperature: self.temperature,
                num_predict: request.max_tokens.unwrap_or(self.max_tokens),
            },
        };

        let url = format!("{}/api/generate", self.base_url);
        let response = self.client
            .post(&url)
            .header("Content-Type", "application/json")
            .json(&ollama_request)
            .send()
            .await?;

        if !response.status().is_success() {
            return Err(anyhow::anyhow!("Ollama API error: {}", response.status()));
        }

        let ollama_response: OllamaResponse = response.json().await?;
        
        // Parse the JSON response
        let findings: serde_json::Value = serde_json::from_str(&ollama_response.response)
            .unwrap_or_else(|_| serde_json::json!({
                "findings": [],
                "summary": "Failed to parse LLM response",
                "confidence": 0.0
            }));

        let summary = findings["summary"].as_str().unwrap_or("No summary").to_string();
        let confidence = findings["confidence"].as_f64().unwrap_or(0.0) as f32;
        // Estimate tokens (Ollama doesn't provide exact token count)
        let estimated_tokens = self.estimate_tokens(&request.raw_output);

        Ok(ParsedResult {
            tool_name: request.tool_name,
            target: request.target,
            timestamp: Utc::now().to_rfc3339(),
            findings,
            summary,
            confidence,
            tokens_used: Some(estimated_tokens),
            cost: Some(0.0), // Local hosting is free
        })
    }

    fn estimate_tokens(&self, text: &str) -> usize {
        // Rough estimation: ~4 characters per token
        (text.len() / 4) + 100 // Add buffer for prompt
    }

    fn get_cost_per_1k_tokens(&self) -> f64 {
        0.0 // Local hosting is free
    }

    fn is_available(&self) -> bool {
        // Check if Ollama is running and model is available
        // This is a basic check - in practice, we'd want to test the connection
        true
    }

    fn provider_name(&self) -> &'static str {
        "ollama"
    }
}