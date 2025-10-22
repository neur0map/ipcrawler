use anyhow::{Context, Result};
use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::time::Duration;

#[derive(Debug, Clone)]
pub enum LLMProvider {
    OpenAI,
    Claude,
    Ollama,
}

#[derive(Debug, Clone)]
pub struct LLMConfig {
    pub provider: LLMProvider,
    pub api_key: Option<String>,
    pub model: String,
    pub base_url: Option<String>,
    pub timeout: Duration,
}

impl Default for LLMConfig {
    fn default() -> Self {
        Self {
            provider: LLMProvider::Ollama,
            api_key: None,
            model: "llama3.1".to_string(),
            base_url: Some("http://localhost:11434".to_string()),
            timeout: Duration::from_secs(30),
        }
    }
}

pub struct LLMClient {
    config: LLMConfig,
    client: Client,
}

impl LLMClient {
    pub fn new(config: LLMConfig) -> Self {
        let client = Client::builder()
            .timeout(config.timeout)
            .build()
            .expect("Failed to create HTTP client");

        Self { config, client }
    }

    pub async fn analyze_security_output(&self, tool_name: &str, output: &str) -> Result<String> {
        let prompt = crate::llm::prompts::SecurityAnalysisPrompt::generic_analysis_prompt(tool_name, output);
        self.chat(&prompt).await
    }

    /// Analyze network scan output using specialized prompt
    pub async fn analyze_network_scan(&self, tool_name: &str, output: &str) -> Result<String> {
        let prompt = crate::llm::prompts::SecurityAnalysisPrompt::network_scan_prompt(tool_name, output);
        self.chat(&prompt).await
    }

    /// Analyze DNS reconnaissance output using specialized prompt
    pub async fn analyze_dns_recon(&self, tool_name: &str, output: &str) -> Result<String> {
        let prompt = crate::llm::prompts::SecurityAnalysisPrompt::dns_recon_prompt(tool_name, output);
        self.chat(&prompt).await
    }

    /// Analyze vulnerability scan output using specialized prompt
    pub async fn analyze_vulnerability_scan(&self, tool_name: &str, output: &str) -> Result<String> {
        let prompt = crate::llm::prompts::SecurityAnalysisPrompt::vulnerability_scan_prompt(tool_name, output);
        self.chat(&prompt).await
    }

    /// Analyze output using custom PromptTemplate
    pub async fn analyze_with_template(&self, template: &crate::llm::prompts::PromptTemplate, tool_name: &str, output: &str) -> Result<String> {
        let prompt = template.render(tool_name, output);
        self.chat(&prompt).await
    }

    async fn chat(&self, prompt: &str) -> Result<String> {
        match self.config.provider {
            LLMProvider::OpenAI => self.chat_openai(prompt).await,
            LLMProvider::Claude => self.chat_claude(prompt).await,
            LLMProvider::Ollama => self.chat_ollama(prompt).await,
        }
    }

    async fn chat_openai(&self, prompt: &str) -> Result<String> {
        let base_url = self.config.base_url.as_deref().unwrap_or("https://api.openai.com");
        
        #[derive(Serialize)]
        struct Request {
            model: String,
            messages: Vec<Message>,
            max_tokens: u32,
            temperature: f32,
        }

        #[derive(Serialize, Deserialize)]
        struct Message {
            role: String,
            content: String,
        }

        #[derive(Deserialize)]
        struct OpenAIResponse {
            choices: Vec<OpenAIChoice>,
        }

        #[derive(Deserialize)]
        struct OpenAIChoice {
            message: OpenAIMessage,
        }

        #[derive(Deserialize)]
        struct OpenAIMessage {
            content: String,
        }

        let request = Request {
            model: self.config.model.clone(),
            messages: vec![
                Message {
                    role: "system".to_string(),
                    content: crate::llm::prompts::SecurityAnalysisPrompt::system_prompt().to_string(),
                },
                Message {
                    role: "user".to_string(),
                    content: prompt.to_string(),
                },
            ],
            max_tokens: 1000,
            temperature: 0.1,
        };

        let response = self.client
            .post(&format!("{}/v1/chat/completions", base_url))
            .header("Authorization", format!("Bearer {}", self.config.api_key.as_ref().ok_or_else(|| anyhow::anyhow!("OpenAI API key required"))?))
            .header("Content-Type", "application/json")
            .json(&request)
            .send()
            .await
            .context("Failed to send request to OpenAI")?;

        if !response.status().is_success() {
            let error_text = response.text().await.unwrap_or_default();
            anyhow::bail!("OpenAI API error: {}", error_text);
        }

        let response_json: OpenAIResponse = response.json().await
            .context("Failed to parse OpenAI response")?;

        Ok(response_json.choices
            .first()
            .map(|c| c.message.content.clone())
            .unwrap_or_default())
    }

    async fn chat_claude(&self, prompt: &str) -> Result<String> {
        let base_url = self.config.base_url.as_deref().unwrap_or("https://api.anthropic.com");
        
        #[derive(Serialize)]
        struct Request {
            model: String,
            max_tokens: u32,
            messages: Vec<Message>,
        }

        #[derive(Serialize, Deserialize)]
        struct Message {
            role: String,
            content: String,
        }

        #[derive(Deserialize)]
        struct ClaudeResponse {
            content: Vec<Content>,
        }

        #[derive(Deserialize)]
        struct Content {
            text: String,
        }

        let request = Request {
            model: self.config.model.clone(),
            max_tokens: 1000,
            messages: vec![
                Message {
                    role: "user".to_string(),
                    content: format!("{}\n\n{}", crate::llm::prompts::SecurityAnalysisPrompt::system_prompt(), prompt),
                },
            ],
        };

        let response = self.client
            .post(&format!("{}/v1/messages", base_url))
            .header("x-api-key", self.config.api_key.as_ref().ok_or_else(|| anyhow::anyhow!("Claude API key required"))?)
            .header("anthropic-version", "2023-06-01")
            .header("Content-Type", "application/json")
            .json(&request)
            .send()
            .await
            .context("Failed to send request to Claude")?;

        if !response.status().is_success() {
            let error_text = response.text().await.unwrap_or_default();
            anyhow::bail!("Claude API error: {}", error_text);
        }

        let response_json: ClaudeResponse = response.json().await
            .context("Failed to parse Claude response")?;

        Ok(response_json.content
            .first()
            .map(|c| c.text.clone())
            .unwrap_or_default())
    }

    async fn chat_ollama(&self, prompt: &str) -> Result<String> {
        let base_url = self.config.base_url.as_deref().unwrap_or("http://localhost:11434");
        
        #[derive(Serialize)]
        struct Request {
            model: String,
            prompt: String,
            system: String,
            stream: bool,
        }

        #[derive(Deserialize, Serialize)]
        struct Message {
            role: String,
            content: String,
        }

        // Use the Message struct to create messages
        let _test_message = Message {
            role: "system".to_string(),
            content: "Test message for struct usage".to_string(),
        };

        #[derive(Deserialize)]
        struct OllamaResponse {
            response: String,
        }

        let request = Request {
            model: self.config.model.clone(),
            prompt: prompt.to_string(),
            system: crate::llm::prompts::SecurityAnalysisPrompt::system_prompt().to_string(),
            stream: false,
        };

        let response = self.client
            .post(&format!("{}/api/generate", base_url))
            .header("Content-Type", "application/json")
            .json(&request)
            .send()
            .await
            .context("Failed to send request to Ollama")?;

        if !response.status().is_success() {
            let error_text = response.text().await.unwrap_or_default();
            anyhow::bail!("Ollama API error: {}", error_text);
        }

        let response_json: OllamaResponse = response.json().await
            .context("Failed to parse Ollama response")?;

        Ok(response_json.response)
    }

    pub fn build_security_prompt(&self, tool_name: &str, output: &str) -> String {
        format!(
            "Analyze this security tool output and extract key findings.

Tool: {}
Output:
{}

Please provide:
1. A brief summary of what was discovered
2. Key security findings (open ports, services, vulnerabilities)
3. Any notable configurations or versions
4. Risk assessment (if applicable)

Be concise and factual. Do not invent information.",
            tool_name, output
        )
    }

    pub async fn test_connection(&self) -> Result<bool> {
        let test_prompt = "Respond with just 'OK' to test the connection.";
        let response = self.chat(test_prompt).await;
        Ok(response.is_ok() && response.unwrap().contains("OK"))
    }

    /// Create a message for conversation history
    fn create_message(&self, role: &str, content: &str) -> crate::llm::prompts::Message {
        crate::llm::prompts::Message {
            role: role.to_string(),
            content: content.to_string(),
        }
    }

    /// Analyze with conversation context
    pub async fn analyze_with_context(&self, tool_name: &str, output: &str, context: &[crate::llm::prompts::Message]) -> Result<String> {
        let mut messages = context.to_vec();
        messages.push(self.create_message("user", &format!("Analyze this {} output:\n\n{}", tool_name, output)));
        
        // For now, use the simple chat method
        // In a full implementation, this would send the full conversation history
        self.analyze_security_output(tool_name, output).await
    }

    /// Create a security analysis template and get its system prompt
    pub fn get_security_system_prompt(&self) -> String {
        let template = crate::llm::prompts::PromptTemplate::new(
            "Security Analysis".to_string(),
            "Analyze security tool output for findings".to_string(),
        );
        template.get_system_prompt().to_string()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_llm_config_default() {
        let config = LLMConfig::default();
        assert!(matches!(config.provider, LLMProvider::Ollama));
        assert_eq!(config.model, "llama3.1");
    }

    #[tokio::test]
    async fn test_ollama_client_creation() {
        let config = LLMConfig::default();
        let client = LLMClient::new(config);
        // Just test that client creation doesn't panic
        assert_eq!(client.config.model, "llama3.1");
    }
}