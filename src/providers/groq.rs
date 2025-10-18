use async_trait::async_trait;
use reqwest::Client;
use serde::{Deserialize, Serialize};
use anyhow::Result;
use chrono::Utc;

use crate::providers::{LLMProvider, ParseRequest, ParsedResult};

#[derive(Debug, Serialize)]
struct GroqRequest {
    model: String,
    messages: Vec<GroqMessage>,
    max_tokens: usize,
    temperature: f32,
}

#[derive(Debug, Serialize, Deserialize)]
struct GroqMessage {
    role: String,
    content: String,
}

#[derive(Debug, Deserialize)]
struct GroqResponse {
    choices: Vec<GroqChoice>,
    usage: GroqUsage,
}

#[derive(Debug, Deserialize)]
struct GroqChoice {
    message: GroqMessage,
}

#[derive(Debug, Deserialize)]
struct GroqUsage {
    total_tokens: usize,
}

pub struct GroqProvider {
    client: Client,
    api_key: String,
    model: String,
    max_tokens: usize,
    temperature: f32,
}

impl GroqProvider {
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
impl LLMProvider for GroqProvider {
    async fn parse(&self, request: ParseRequest) -> Result<ParsedResult> {
        let prompt = self.build_prompt(&request);
        
        let groq_request = GroqRequest {
            model: self.model.clone(),
            messages: vec![
                GroqMessage {
                    role: "system".to_string(),
                    content: "You are an expert penetration testing output parser. Convert raw tool output into structured JSON. Be accurate and concise.".to_string(),
                },
                GroqMessage {
                    role: "user".to_string(),
                    content: prompt,
                },
            ],
            max_tokens: request.max_tokens.unwrap_or(self.max_tokens),
            temperature: self.temperature,
        };

        let response = self.client
            .post("https://api.groq.com/openai/v1/chat/completions")
            .header("Authorization", format!("Bearer {}", self.api_key))
            .header("Content-Type", "application/json")
            .json(&groq_request)
            .send()
            .await?;

        if !response.status().is_success() {
            return Err(anyhow::anyhow!("Groq API error: {}", response.status()));
        }

        let groq_response: GroqResponse = response.json().await?;
        
        if groq_response.choices.is_empty() {
            return Err(anyhow::anyhow!("No response from Groq"));
        }

        let content = &groq_response.choices[0].message.content;
        
        // Parse the JSON response
        let findings: serde_json::Value = serde_json::from_str(content)
            .unwrap_or_else(|_| serde_json::json!({
                "findings": [],
                "summary": "Failed to parse LLM response",
                "confidence": 0.0
            }));

        let summary = findings["summary"].as_str().unwrap_or("No summary").to_string();
        let confidence = findings["confidence"].as_f64().unwrap_or(0.0) as f32;
        let cost = (groq_response.usage.total_tokens as f64 / 1000.0) * self.get_cost_per_1k_tokens();

        Ok(ParsedResult {
            tool_name: request.tool_name,
            target: request.target,
            timestamp: Utc::now().to_rfc3339(),
            findings,
            summary,
            confidence,
            tokens_used: Some(groq_response.usage.total_tokens),
            cost: Some(cost),
        })
    }

    fn estimate_tokens(&self, text: &str) -> usize {
        // Rough estimation: ~4 characters per token
        (text.len() / 4) + 100 // Add buffer for prompt
    }

    fn get_cost_per_1k_tokens(&self) -> f64 {
        match self.model.as_str() {
            "llama-3.1-70b-versatile" => 0.00059,
            "llama-3.1-8b-instant" => 0.00005,
            "mixtral-8x7b-32768" => 0.00024,
            "gemma-7b-it" => 0.00007,
            _ => 0.00059,
        }
    }

    fn is_available(&self) -> bool {
        !self.api_key.is_empty()
    }

    fn provider_name(&self) -> &'static str {
        "groq"
    }


    }
}