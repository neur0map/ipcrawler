use anyhow::{Context, Result};
use reqwest::Client;
use serde::{Deserialize, Serialize};
use tracing::{debug, info};

#[derive(Debug, Clone)]
pub struct LlmParser {
    provider: LlmProvider,
    model: String,
    api_key: String,
    client: Client,
}

#[derive(Debug, Clone)]
pub enum LlmProvider {
    OpenAI,
    Anthropic,
    Groq,
    Ollama { base_url: String },
}

impl LlmParser {
    pub fn new(provider: &str, model: Option<String>, api_key: String) -> Result<Self> {
        let (provider, default_model) = match provider.to_lowercase().as_str() {
            "openai" => (LlmProvider::OpenAI, "gpt-4o-mini"),
            "anthropic" => (LlmProvider::Anthropic, "claude-3-5-sonnet-20241022"),
            "groq" => (LlmProvider::Groq, "llama-3.3-70b-versatile"),
            "ollama" => (
                LlmProvider::Ollama {
                    base_url: "http://localhost:11434".to_string(),
                },
                "llama3.2",
            ),
            _ => anyhow::bail!("Unsupported LLM provider: {}", provider),
        };

        let model = model.unwrap_or_else(|| default_model.to_string());

        Ok(Self {
            provider,
            model,
            api_key,
            client: Client::new(),
        })
    }

    pub async fn parse_output(&self, tool_name: &str, output: &str) -> Result<String> {
        if output.trim().is_empty() {
            return Ok(String::new());
        }

        let prompt = self.build_extraction_prompt(tool_name, output);

        info!("Parsing output from '{}' using LLM", tool_name);
        debug!("Output length: {} bytes", output.len());

        let response = match &self.provider {
            LlmProvider::OpenAI => self.call_openai(&prompt).await?,
            LlmProvider::Anthropic => self.call_anthropic(&prompt).await?,
            LlmProvider::Groq => self.call_groq(&prompt).await?,
            LlmProvider::Ollama { base_url } => self.call_ollama(base_url, &prompt).await?,
        };

        Ok(response)
    }

    fn get_system_prompt(&self) -> String {
        r#"You are a penetration testing output parser. Your ONLY job is to extract data from security tool outputs.

CRITICAL RULES:
1. DO NOT analyze, interpret, or add commentary
2. DO NOT suggest fixes or recommendations
3. DO NOT explain the vulnerabilities
4. ONLY extract what is explicitly present in the output
5. Return ONLY valid JSON, no markdown, no explanation

Your purpose: Convert unstructured tool output into structured JSON data.
Nothing more, nothing less."#.to_string()
    }

    fn build_extraction_prompt(&self, tool_name: &str, output: &str) -> String {
        let truncated_output = if output.len() > 50000 {
            format!("{}...[truncated]", &output[..50000])
        } else {
            output.to_string()
        };

        format!(
            r#"Extract data from this {} output.

Required JSON format:
{{
  "ips": ["1.2.3.4"],
  "domains": ["example.com"],
  "urls": ["http://example.com/path"],
  "ports": [{{"port": 80, "protocol": "tcp", "service": "http", "version": "Apache 2.4"}}],
  "vulnerabilities": [{{"name": "CVE-2021-1234", "severity": "high", "description": "SQL injection"}}],
  "findings": ["Admin panel accessible"]
}}

Tool output:
{}

Return JSON only:"#,
            tool_name, truncated_output
        )
    }

    async fn call_openai(&self, prompt: &str) -> Result<String> {
        #[derive(Serialize)]
        struct OpenAIRequest {
            model: String,
            messages: Vec<Message>,
            temperature: f32,
            response_format: ResponseFormat,
        }

        #[derive(Serialize)]
        struct Message {
            role: String,
            content: String,
        }

        #[derive(Serialize)]
        struct ResponseFormat {
            #[serde(rename = "type")]
            format_type: String,
        }

        #[derive(Deserialize)]
        struct OpenAIResponse {
            choices: Vec<Choice>,
        }

        #[derive(Deserialize)]
        struct Choice {
            message: MessageResponse,
        }

        #[derive(Deserialize)]
        struct MessageResponse {
            content: String,
        }

        let request = OpenAIRequest {
            model: self.model.clone(),
            messages: vec![
                Message {
                    role: "system".to_string(),
                    content: self.get_system_prompt(),
                },
                Message {
                    role: "user".to_string(),
                    content: prompt.to_string(),
                },
            ],
            temperature: 0.1,
            response_format: ResponseFormat {
                format_type: "json_object".to_string(),
            },
        };

        let response = self
            .client
            .post("https://api.openai.com/v1/chat/completions")
            .header("Authorization", format!("Bearer {}", self.api_key))
            .header("Content-Type", "application/json")
            .json(&request)
            .send()
            .await
            .context("Failed to call OpenAI API")?;

        if !response.status().is_success() {
            let error_text = response.text().await?;
            anyhow::bail!("OpenAI API error: {}", error_text);
        }

        let response: OpenAIResponse = response.json().await?;
        Ok(response
            .choices
            .first()
            .map(|c| c.message.content.clone())
            .unwrap_or_default())
    }

    async fn call_anthropic(&self, prompt: &str) -> Result<String> {
        #[derive(Serialize)]
        struct AnthropicRequest {
            model: String,
            max_tokens: u32,
            temperature: f32,
            system: String,
            messages: Vec<Message>,
        }

        #[derive(Serialize)]
        struct Message {
            role: String,
            content: String,
        }

        #[derive(Deserialize)]
        struct AnthropicResponse {
            content: Vec<ContentBlock>,
        }

        #[derive(Deserialize)]
        struct ContentBlock {
            text: String,
        }

        let request = AnthropicRequest {
            model: self.model.clone(),
            max_tokens: 4096,
            temperature: 0.1,
            system: self.get_system_prompt(),
            messages: vec![Message {
                role: "user".to_string(),
                content: prompt.to_string(),
            }],
        };

        let response = self
            .client
            .post("https://api.anthropic.com/v1/messages")
            .header("x-api-key", &self.api_key)
            .header("anthropic-version", "2023-06-01")
            .header("Content-Type", "application/json")
            .json(&request)
            .send()
            .await
            .context("Failed to call Anthropic API")?;

        if !response.status().is_success() {
            let error_text = response.text().await?;
            anyhow::bail!("Anthropic API error: {}", error_text);
        }

        let response: AnthropicResponse = response.json().await?;
        Ok(response
            .content
            .first()
            .map(|c| c.text.clone())
            .unwrap_or_default())
    }

    async fn call_groq(&self, prompt: &str) -> Result<String> {
        #[derive(Serialize)]
        struct GroqRequest {
            model: String,
            messages: Vec<Message>,
            temperature: f32,
            response_format: ResponseFormat,
        }

        #[derive(Serialize)]
        struct Message {
            role: String,
            content: String,
        }

        #[derive(Serialize)]
        struct ResponseFormat {
            #[serde(rename = "type")]
            format_type: String,
        }

        #[derive(Deserialize)]
        struct GroqResponse {
            choices: Vec<Choice>,
        }

        #[derive(Deserialize)]
        struct Choice {
            message: MessageResponse,
        }

        #[derive(Deserialize)]
        struct MessageResponse {
            content: String,
        }

        let request = GroqRequest {
            model: self.model.clone(),
            messages: vec![
                Message {
                    role: "system".to_string(),
                    content: self.get_system_prompt(),
                },
                Message {
                    role: "user".to_string(),
                    content: prompt.to_string(),
                },
            ],
            temperature: 0.1,
            response_format: ResponseFormat {
                format_type: "json_object".to_string(),
            },
        };

        let response = self
            .client
            .post("https://api.groq.com/openai/v1/chat/completions")
            .header("Authorization", format!("Bearer {}", self.api_key))
            .header("Content-Type", "application/json")
            .json(&request)
            .send()
            .await
            .context("Failed to call Groq API")?;

        if !response.status().is_success() {
            let error_text = response.text().await?;
            anyhow::bail!("Groq API error: {}", error_text);
        }

        let response: GroqResponse = response.json().await?;
        Ok(response
            .choices
            .first()
            .map(|c| c.message.content.clone())
            .unwrap_or_default())
    }

    async fn call_ollama(&self, base_url: &str, prompt: &str) -> Result<String> {
        #[derive(Serialize)]
        struct OllamaRequest {
            model: String,
            prompt: String,
            stream: bool,
            system: String,
            format: String,
            #[serde(skip_serializing_if = "Option::is_none")]
            options: Option<OllamaOptions>,
        }

        #[derive(Serialize)]
        struct OllamaOptions {
            temperature: f32,
        }

        #[derive(Deserialize)]
        struct OllamaResponse {
            response: String,
        }

        let full_prompt = format!("{}\n\n{}", self.get_system_prompt(), prompt);

        let request = OllamaRequest {
            model: self.model.clone(),
            prompt: full_prompt,
            stream: false,
            system: self.get_system_prompt(),
            format: "json".to_string(),
            options: Some(OllamaOptions { temperature: 0.1 }),
        };

        let url = format!("{}/api/generate", base_url);
        let response = self
            .client
            .post(&url)
            .json(&request)
            .send()
            .await
            .context("Failed to call Ollama API")?;

        if !response.status().is_success() {
            let error_text = response.text().await?;
            anyhow::bail!("Ollama API error: {}", error_text);
        }

        let response: OllamaResponse = response.json().await?;
        Ok(response.response)
    }
}
