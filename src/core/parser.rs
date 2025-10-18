use anyhow::Result;
use std::sync::Arc;
use tokio::sync::RwLock;

use crate::providers::{LLMProvider, ParseRequest, ParsedResult};
use crate::storage::{SecureKeyStore, ResultCache};
use crate::cost::CostTracker;
use crate::optimization::{OutputPreprocessor, TokenManager};

#[derive(Clone)]
pub struct LLMParser {
    key_store: SecureKeyStore,
    cost_tracker: Arc<RwLock<CostTracker>>,
    cache: Arc<RwLock<ResultCache>>,
    preprocessor: OutputPreprocessor,
    token_manager: TokenManager,
    default_provider: Option<String>,
    verbose: bool,
}

impl LLMParser {
    pub fn new(
        key_store: SecureKeyStore,
        cost_tracker: CostTracker,
        default_provider: Option<String>,
        verbose: bool,
    ) -> Result<Self> {
        let cache = ResultCache::new()?;
        
        Ok(Self {
            key_store,
            cost_tracker: Arc::new(RwLock::new(cost_tracker)),
            cache: Arc::new(RwLock::new(cache)),
            preprocessor: OutputPreprocessor::new(),
            token_manager: TokenManager::new(),
            default_provider,
            verbose,
        })
    }

    pub async fn parse(&self, request: ParseRequest) -> Result<ParsedResult> {
        // Check cache first
        {
            let mut cache = self.cache.write().await;
            if let Some(cached_result) = cache.get(&request.tool_name, &request.target, &request.raw_output) {
                if self.verbose {
                    println!("Cache hit for {} on {}", request.tool_name, request.target);
                }
                return Ok(cached_result);
            }
        }

        // Preprocess output to reduce tokens
        let optimized_output = self.preprocessor.optimize_for_llm(&request.raw_output, &request.tool_name);
        
        if self.verbose {
            let savings = self.preprocessor.estimate_token_savings(&request.raw_output, &request.tool_name);
            println!("Token optimization saved {:.1}% for {}", savings * 100.0, request.tool_name);
        }

        // Check if LLM parsing is even needed
        if !self.preprocessor.should_use_llm(&optimized_output, &request.tool_name) {
            let result = self.create_simple_result(&request, &optimized_output)?;
            
            // Cache the result
            {
                let mut cache = self.cache.write().await;
                cache.store(&request.tool_name, &request.target, &request.raw_output, &result)?;
            }
            
            return Ok(result);
        }

        // Get provider and parse
        let result = self.parse_with_provider(&request, &optimized_output).await?;
        
        // Cache the result
        {
            let mut cache = self.cache.write().await;
            cache.store(&request.tool_name, &request.target, &request.raw_output, &result)?;
        }
        
        Ok(result)
    }

    async fn parse_with_provider(&self, request: &ParseRequest, optimized_output: &str) -> Result<ParsedResult> {
        let provider = self.get_provider().await?;
        
        // Estimate tokens and cost
        let prompt = self.build_prompt(request, optimized_output);
        let token_estimate = self.token_manager.estimate_total_tokens(&prompt, optimized_output, &request.tool_name);
        let estimated_cost = (token_estimate.total_tokens as f64 / 1000.0) * provider.get_cost_per_1k_tokens();
        
        // Check cost limits
        {
            let cost_tracker = self.cost_tracker.read().await;
            if !cost_tracker.should_proceed(estimated_cost, provider.provider_name()) {
                return Err(anyhow::anyhow!(
                    "Estimated cost ${:.6} exceeds limits for provider {}",
                    estimated_cost,
                    provider.provider_name()
                ));
            }
        }

        if self.verbose {
            println!("Parsing {} output with {} (estimated {} tokens, ${:.6})",
                request.tool_name,
                provider.provider_name(),
                token_estimate.total_tokens,
                estimated_cost
            );
        }

        // Create modified request with optimized output
        let mut modified_request = request.clone();
        modified_request.raw_output = optimized_output.to_string();
        modified_request.max_tokens = Some(token_estimate.output_tokens);

        // Execute parsing
        let result = provider.parse(modified_request).await?;
        
        // Track usage
        {
            let mut cost_tracker = self.cost_tracker.write().await;
            let actual_tokens = crate::optimization::tokens::TokenEstimate {
                input_tokens: result.tokens_used.unwrap_or(token_estimate.input_tokens),
                output_tokens: token_estimate.output_tokens,
                total_tokens: result.tokens_used.unwrap_or(token_estimate.total_tokens),
            };
            
            let actual_cost = crate::optimization::tokens::CostEstimate {
                input_cost: result.cost.unwrap_or(estimated_cost) * 0.7, // Rough split
                output_cost: result.cost.unwrap_or(estimated_cost) * 0.3,
                total_cost: result.cost.unwrap_or(estimated_cost),
                tokens: actual_tokens.clone(),
            };
            
            cost_tracker.track_usage(provider.provider_name(), &actual_tokens, &actual_cost)?;
        }

        if self.verbose {
            if let Some(cost) = result.cost {
                println!("Parsing completed: ${:.6}", cost);
            }
        }

        Ok(result)
    }

    async fn get_provider(&self) -> Result<Box<dyn LLMProvider>> {
        let provider_names = if let Some(ref default) = self.default_provider {
            vec![default.clone()]
        } else {
            vec!["groq".to_string(), "openrouter".to_string(), "openai".to_string(), "ollama".to_string()]
        };

        for provider_name in provider_names {
            if let Some(api_key) = self.key_store.get_key(&provider_name)? {
                let provider: Box<dyn LLMProvider> = match provider_name.as_str() {
                    "openai" => {
                        let model = "gpt-4o-mini".to_string();
                        Box::new(crate::providers::OpenAIProvider::new(api_key, model))
                    }
                    "groq" => {
                        let model = "llama-3.1-8b-instant".to_string();
                        Box::new(crate::providers::GroqProvider::new(api_key, model))
                    }
                    "openrouter" => {
                        let model = "meta-llama/llama-3.1-8b-instruct".to_string();
                        Box::new(crate::providers::OpenRouterProvider::new(api_key, model))
                    }
                    "ollama" => {
                        let model = "llama3.1:8b".to_string();
                        let base_url = "http://localhost:11434".to_string();
                        Box::new(crate::providers::OllamaProvider::new(base_url, model))
                    }
                    _ => continue,
                };

                if provider.is_available() {
                    return Ok(provider);
                }
            }
        }

        Err(anyhow::anyhow!(
            "No LLM provider available. Configure API keys with: ipcrawler keys set --provider <provider> --key <key>"
        ))
    }

    fn build_prompt(&self, request: &ParseRequest, optimized_output: &str) -> String {
        format!(
            "Parse tool output into structured JSON. Tool: {}, Target: {}\n\n\
            Rules:\n\
            1. Extract only factual information from the output\n\
            2. Return valid JSON only - no explanations\n\
            3. Use this schema: {{\"findings\":[{{\"type\":\"\",\"data\":{{}},\"severity\":\"\"}}],\"summary\":\"\",\"confidence\":0.0}}\n\
            4. Types: port, service, dns, vulnerability, error, host\n\
            5. Severity: info, low, medium, high, critical\n\
            6. If no data, return {{\"findings\":[],\"summary\":\"No actionable data\",\"confidence\":0.0}}\n\
            7. Be accurate and concise\n\n\
            Output:\n{}",
            request.tool_name,
            request.target,
            optimized_output
        )
    }

    fn create_simple_result(&self, request: &ParseRequest, output: &str) -> Result<ParsedResult> {
        let findings = if output.trim().is_empty() {
            serde_json::json!([])
        } else {
            // Create a simple finding for basic outputs
            serde_json::json!([{
                "type": "raw_output",
                "data": {
                    "content": output.trim(),
                    "tool": request.tool_name,
                    "target": request.target
                },
                "severity": "info"
            }])
        };

        Ok(ParsedResult {
            tool_name: request.tool_name.clone(),
            target: request.target.clone(),
            timestamp: chrono::Utc::now().to_rfc3339(),
            findings,
            summary: format!("Raw output from {}", request.tool_name),
            confidence: 0.5,
            tokens_used: None,
            cost: None,
        })
    }

    
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::cost::CostTracker;

    #[test]
    fn test_parser_creation() -> Result<()> {
        let key_store = crate::storage::SecureKeyStore::new()?;
        let cost_tracker = CostTracker::new(0.01)?;
        
        let parser = LLMParser::new(
            key_store,
            cost_tracker,
            Some("groq".to_string()),
            false,
        )?;
        
        assert!(parser.get_default_provider().is_some());
        
        Ok(())
    }
}