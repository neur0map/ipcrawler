use async_trait::async_trait;
use reqwest::Client;
use serde::{Deserialize, Serialize};
use anyhow::Result;
use chrono::Utc;

use crate::providers::{LLMProvider, ParseRequest, ParsedResult};

#[derive(Debug, Serialize)]
struct OpenRouterRequest {
    model: String,
    messages: Vec<OpenRouterMessage>,
    max_tokens: usize,
    temperature: f32,
}

#[derive(Debug, Serialize, Deserialize)]
struct OpenRouterMessage {
    role: String,
    content: String,
}

#[derive(Debug, Deserialize)]
struct OpenRouterResponse {
    choices: Vec<OpenRouterChoice>,
    usage: OpenRouterUsage,
}

#[derive(Debug, Deserialize)]
struct OpenRouterChoice {
    message: OpenRouterMessage,
}

#[derive(Debug, Deserialize)]
struct OpenRouterUsage {
    total_tokens: usize,
}

pub struct OpenRouterProvider {
    client: Client,
    api_key: String,
    model: String,
    max_tokens: usize,
    temperature: f32,
}

impl OpenRouterProvider {
    pub fn new(api_key: String, model: String) -> Self {
        Self {
            client: Client::new(),
            api_key,
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
}

#[async_trait]
impl LLMProvider for OpenRouterProvider {
    async fn parse(&self, request: ParseRequest) -> Result<ParsedResult> {
        let prompt = self.build_prompt(&request);
        
        let openrouter_request = OpenRouterRequest {
            model: self.model.clone(),
            messages: vec![
                OpenRouterMessage {
                    role: "system".to_string(),
                    content: "You are an expert penetration testing output parser. Convert raw tool output into structured JSON. Be accurate and concise.".to_string(),
                },
                OpenRouterMessage {
                    role: "user".to_string(),
                    content: prompt,
                },
            ],
            max_tokens: request.max_tokens.unwrap_or(self.max_tokens),
            temperature: self.temperature,
        };

        let response = self.client
            .post("https://openrouter.ai/api/v1/chat/completions")
            .header("Authorization", format!("Bearer {}", self.api_key))
            .header("Content-Type", "application/json")
            .header("HTTP-Referer", "https://github.com/neur0map/ipcrawler")
            .header("X-Title", "IPCrawler")
            .json(&openrouter_request)
            .send()
            .await?;

        if !response.status().is_success() {
            return Err(anyhow::anyhow!("OpenRouter API error: {}", response.status()));
        }

        let openrouter_response: OpenRouterResponse = response.json().await?;
        
        if openrouter_response.choices.is_empty() {
            return Err(anyhow::anyhow!("No response from OpenRouter"));
        }

        let content = &openrouter_response.choices[0].message.content;
        
        // Parse the JSON response
        let findings: serde_json::Value = serde_json::from_str(content)
            .unwrap_or_else(|_| serde_json::json!({
                "findings": [],
                "summary": "Failed to parse LLM response",
                "confidence": 0.0
            }));

        let summary = findings["summary"].as_str().unwrap_or("No summary").to_string();
        let confidence = findings["confidence"].as_f64().unwrap_or(0.0) as f32;
        let cost = (openrouter_response.usage.total_tokens as f64 / 1000.0) * self.get_cost_per_1k_tokens();

        Ok(ParsedResult {
            tool_name: request.tool_name,
            target: request.target,
            timestamp: Utc::now().to_rfc3339(),
            findings,
            summary,
            confidence,
            tokens_used: Some(openrouter_response.usage.total_tokens),
            cost: Some(cost),
        })
    }

    fn estimate_tokens(&self, text: &str) -> usize {
        // Rough estimation: ~4 characters per token
        (text.len() / 4) + 100 // Add buffer for prompt
    }

    fn get_cost_per_1k_tokens(&self) -> f64 {
        match self.model.as_str() {
            "meta-llama/llama-3.1-8b-instruct:free" => 0.0,
            "meta-llama/llama-3.1-70b-instruct" => 0.00059,
            "meta-llama/llama-3.1-8b-instruct" => 0.00003,
            "mistralai/mistral-7b-instruct" => 0.00003,
            "microsoft/wizardlm-2-8x22b" => 0.0001,
            _ => 0.00059,
        }
    }

    fn is_available(&self) -> bool {
        !self.api_key.is_empty()
    }

    fn provider_name(&self) -> &'static str {
        "openrouter"
    }


    }
}