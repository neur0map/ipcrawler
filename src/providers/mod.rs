use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use anyhow::Result;

pub mod openai;
pub mod groq;
pub mod openrouter;
pub mod ollama;

pub use openai::OpenAIProvider;
pub use groq::GroqProvider;
pub use openrouter::OpenRouterProvider;
pub use ollama::OllamaProvider;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ParseRequest {
    pub tool_name: String,
    pub raw_output: String,
    pub target: String,
    pub max_tokens: Option<usize>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ParsedResult {
    pub tool_name: String,
    pub target: String,
    pub timestamp: String,
    pub findings: serde_json::Value,
    pub summary: String,
    pub confidence: f32,
    pub tokens_used: Option<usize>,
    pub cost: Option<f64>,
}

#[async_trait]
pub trait LLMProvider: Send + Sync {
    async fn parse(&self, request: ParseRequest) -> Result<ParsedResult>;
    fn estimate_tokens(&self, text: &str) -> usize;
    fn get_cost_per_1k_tokens(&self) -> f64;
    fn is_available(&self) -> bool;
    fn provider_name(&self) -> &'static str;
}

