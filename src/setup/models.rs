use anyhow::Result;
use reqwest::Client;
use serde::Deserialize;
use std::time::Duration;

#[derive(Debug, Clone)]
pub struct ModelInfo {
    pub name: String,
    pub provider: String,
    pub size: Option<String>,
    pub description: String,
    pub requires_api_key: bool,
}

#[derive(Debug, Deserialize)]
struct OllamaModel {
    name: String,
    #[allow(dead_code)]
    modified_at: String,
    size: i64,
}

#[derive(Debug, Deserialize)]
struct OllamaListResponse {
    models: Vec<OllamaModel>,
}

pub struct ModelDetector {
    client: Client,
}

impl ModelDetector {
    pub fn new() -> Self {
        Self {
            client: Client::builder()
                .timeout(Duration::from_secs(5))
                .build()
                .unwrap(),
        }
    }

    pub async fn check_ollama(&self) -> Result<bool> {
        match self.client
            .get("http://localhost:11434/api/tags")
            .send()
            .await
        {
            Ok(resp) => Ok(resp.status().is_success()),
            Err(_) => Ok(false),
        }
    }

    pub async fn check_qdrant(&self) -> Result<bool> {
        match self.client
            .get("http://localhost:6333/")
            .send()
            .await
        {
            Ok(resp) => Ok(resp.status().is_success()),
            Err(_) => Ok(false),
        }
    }

    pub async fn list_ollama_models(&self) -> Result<Vec<ModelInfo>> {
        let response = self.client
            .get("http://localhost:11434/api/tags")
            .send()
            .await?;

        let list: OllamaListResponse = response.json().await?;

        Ok(list.models.iter().map(|m| {
            ModelInfo {
                name: m.name.clone(),
                provider: "Ollama".to_string(),
                size: Some(format!("{:.1} GB", m.size as f64 / 1_000_000_000.0)),
                description: format!("Local model: {}", m.name),
                requires_api_key: false,
            }
        }).collect())
    }

    pub fn available_openai_models() -> Vec<ModelInfo> {
        vec![
            ModelInfo {
                name: "gpt-4o".to_string(),
                provider: "OpenAI".to_string(),
                size: None,
                description: "Most capable GPT-4 model (fast, multimodal)".to_string(),
                requires_api_key: true,
            },
            ModelInfo {
                name: "gpt-4-turbo".to_string(),
                provider: "OpenAI".to_string(),
                size: None,
                description: "GPT-4 Turbo with vision capabilities".to_string(),
                requires_api_key: true,
            },
            ModelInfo {
                name: "gpt-4".to_string(),
                provider: "OpenAI".to_string(),
                size: None,
                description: "Standard GPT-4 model".to_string(),
                requires_api_key: true,
            },
            ModelInfo {
                name: "gpt-3.5-turbo".to_string(),
                provider: "OpenAI".to_string(),
                size: None,
                description: "Fast and cost-effective".to_string(),
                requires_api_key: true,
            },
        ]
    }

    pub fn available_embedding_models() -> Vec<ModelInfo> {
        vec![
            ModelInfo {
                name: "text-embedding-3-large".to_string(),
                provider: "OpenAI".to_string(),
                size: None,
                description: "Most capable embedding model (3072 dimensions)".to_string(),
                requires_api_key: true,
            },
            ModelInfo {
                name: "text-embedding-3-small".to_string(),
                provider: "OpenAI".to_string(),
                size: None,
                description: "Efficient embedding model (1536 dimensions)".to_string(),
                requires_api_key: true,
            },
            ModelInfo {
                name: "text-embedding-ada-002".to_string(),
                provider: "OpenAI".to_string(),
                size: None,
                description: "Legacy embedding model".to_string(),
                requires_api_key: true,
            },
            ModelInfo {
                name: "nomic-embed-text".to_string(),
                provider: "Ollama".to_string(),
                size: Some("274 MB".to_string()),
                description: "Local embedding model (768 dimensions)".to_string(),
                requires_api_key: false,
            },
            ModelInfo {
                name: "mxbai-embed-large".to_string(),
                provider: "Ollama".to_string(),
                size: Some("670 MB".to_string()),
                description: "Local embedding model (1024 dimensions)".to_string(),
                requires_api_key: false,
            },
        ]
    }

    pub fn recommended_ollama_models() -> Vec<ModelInfo> {
        vec![
            ModelInfo {
                name: "llama3.1".to_string(),
                provider: "Ollama".to_string(),
                size: Some("4.7 GB".to_string()),
                description: "Meta's latest Llama model (8B parameters)".to_string(),
                requires_api_key: false,
            },
            ModelInfo {
                name: "llama3.1:70b".to_string(),
                provider: "Ollama".to_string(),
                size: Some("40 GB".to_string()),
                description: "Larger Llama model (70B parameters) - Best quality".to_string(),
                requires_api_key: false,
            },
            ModelInfo {
                name: "mistral".to_string(),
                provider: "Ollama".to_string(),
                size: Some("4.1 GB".to_string()),
                description: "Mistral 7B - Fast and capable".to_string(),
                requires_api_key: false,
            },
            ModelInfo {
                name: "phi3".to_string(),
                provider: "Ollama".to_string(),
                size: Some("2.3 GB".to_string()),
                description: "Microsoft Phi-3 - Small but powerful".to_string(),
                requires_api_key: false,
            },
            ModelInfo {
                name: "qwen2.5".to_string(),
                provider: "Ollama".to_string(),
                size: Some("4.7 GB".to_string()),
                description: "Qwen 2.5 - Strong reasoning capabilities".to_string(),
                requires_api_key: false,
            },
        ]
    }
}
