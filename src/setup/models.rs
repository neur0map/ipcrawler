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

    pub fn available_groq_models() -> Vec<ModelInfo> {
        vec![
            ModelInfo {
                name: "llama-3.3-70b-versatile".to_string(),
                provider: "Groq".to_string(),
                size: None,
                description: "Llama 3.3 70B - Most capable, versatile model".to_string(),
                requires_api_key: true,
            },
            ModelInfo {
                name: "llama-3.1-70b-versatile".to_string(),
                provider: "Groq".to_string(),
                size: None,
                description: "Llama 3.1 70B - High performance on hardware".to_string(),
                requires_api_key: true,
            },
            ModelInfo {
                name: "llama-3.1-8b-instant".to_string(),
                provider: "Groq".to_string(),
                size: None,
                description: "Llama 3.1 8B - Fast, lightweight model".to_string(),
                requires_api_key: true,
            },
            ModelInfo {
                name: "mixtral-8x7b-32768".to_string(),
                provider: "Groq".to_string(),
                size: None,
                description: "Mixtral 8x7B - Large context window (32k tokens)".to_string(),
                requires_api_key: true,
            },
            ModelInfo {
                name: "gemma2-9b-it".to_string(),
                provider: "Groq".to_string(),
                size: None,
                description: "Google Gemma 2 9B - Efficient instruction-tuned model".to_string(),
                requires_api_key: true,
            },
        ]
    }

    pub fn available_openrouter_models() -> Vec<ModelInfo> {
        vec![
            ModelInfo {
                name: "openai/gpt-4o".to_string(),
                provider: "OpenRouter".to_string(),
                size: None,
                description: "GPT-4o via OpenRouter - Most capable".to_string(),
                requires_api_key: true,
            },
            ModelInfo {
                name: "anthropic/claude-3.5-sonnet".to_string(),
                provider: "OpenRouter".to_string(),
                size: None,
                description: "Claude 3.5 Sonnet - Excellent reasoning".to_string(),
                requires_api_key: true,
            },
            ModelInfo {
                name: "google/gemini-pro-1.5".to_string(),
                provider: "OpenRouter".to_string(),
                size: None,
                description: "Gemini Pro 1.5 - Large context window".to_string(),
                requires_api_key: true,
            },
            ModelInfo {
                name: "meta-llama/llama-3.1-70b-instruct".to_string(),
                provider: "OpenRouter".to_string(),
                size: None,
                description: "Llama 3.1 70B Instruct - Open source, powerful".to_string(),
                requires_api_key: true,
            },
            ModelInfo {
                name: "mistralai/mixtral-8x7b-instruct".to_string(),
                provider: "OpenRouter".to_string(),
                size: None,
                description: "Mixtral 8x7B Instruct - Fast and capable".to_string(),
                requires_api_key: true,
            },
        ]
    }

    pub fn available_huggingface_models() -> Vec<ModelInfo> {
        vec![
            ModelInfo {
                name: "meta-llama/Llama-3.1-70B-Instruct".to_string(),
                provider: "Huggingface".to_string(),
                size: None,
                description: "Llama 3.1 70B Instruct - Powerful instruction-following".to_string(),
                requires_api_key: true,
            },
            ModelInfo {
                name: "meta-llama/Llama-3.1-8B-Instruct".to_string(),
                provider: "Huggingface".to_string(),
                size: None,
                description: "Llama 3.1 8B Instruct - Fast and efficient".to_string(),
                requires_api_key: true,
            },
            ModelInfo {
                name: "mistralai/Mixtral-8x7B-Instruct-v0.1".to_string(),
                provider: "Huggingface".to_string(),
                size: None,
                description: "Mixtral 8x7B - Mixture of experts model".to_string(),
                requires_api_key: true,
            },
            ModelInfo {
                name: "microsoft/Phi-3-medium-4k-instruct".to_string(),
                provider: "Huggingface".to_string(),
                size: None,
                description: "Phi-3 Medium - Small but powerful".to_string(),
                requires_api_key: true,
            },
            ModelInfo {
                name: "Qwen/Qwen2.5-72B-Instruct".to_string(),
                provider: "Huggingface".to_string(),
                size: None,
                description: "Qwen 2.5 72B - Strong reasoning capabilities".to_string(),
                requires_api_key: true,
            },
        ]
    }

    pub fn available_huggingface_embeddings() -> Vec<ModelInfo> {
        vec![
            ModelInfo {
                name: "sentence-transformers/all-MiniLM-L6-v2".to_string(),
                provider: "Huggingface".to_string(),
                size: None,
                description: "Fast, lightweight embedding model (384 dimensions)".to_string(),
                requires_api_key: false,
            },
            ModelInfo {
                name: "sentence-transformers/all-mpnet-base-v2".to_string(),
                provider: "Huggingface".to_string(),
                size: None,
                description: "High quality embeddings (768 dimensions)".to_string(),
                requires_api_key: false,
            },
            ModelInfo {
                name: "BAAI/bge-large-en-v1.5".to_string(),
                provider: "Huggingface".to_string(),
                size: None,
                description: "Best quality embeddings (1024 dimensions)".to_string(),
                requires_api_key: false,
            },
        ]
    }
}
