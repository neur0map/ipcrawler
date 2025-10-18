use std::collections::HashMap;

#[derive(Clone)]
pub struct TokenManager {
    token_estimates: HashMap<String, f32>,
}

impl TokenManager {
    pub fn new() -> Self {
        let mut token_estimates = HashMap::new();
        
        // Average characters per token for different types of content
        token_estimates.insert("english".to_string(), 4.0);
        token_estimates.insert("code".to_string(), 3.5);
        token_estimates.insert("json".to_string(), 3.0);
        token_estimates.insert("numbers".to_string(), 5.0);
        token_estimates.insert("mixed".to_string(), 3.8);
        
        Self { token_estimates }
    }

    pub fn estimate_tokens(&self, text: &str, content_type: &str) -> usize {
        let chars_per_token = self.token_estimates
            .get(content_type)
            .unwrap_or(&self.token_estimates["mixed"]);
        
        ((text.len() as f32 / chars_per_token) as usize).max(1)
    }

    pub fn estimate_input_tokens(&self, prompt: &str, tool_output: &str) -> usize {
        let prompt_tokens = self.estimate_tokens(prompt, "english");
        let output_tokens = self.estimate_tokens(tool_output, "mixed");
        
        prompt_tokens + output_tokens
    }

    pub fn estimate_output_tokens(&self, tool_name: &str, output_size: usize) -> usize {
        // Estimate how many tokens the LLM response will be
        match tool_name {
            "nmap" => {
                // Nmap typically produces structured port data
                (output_size / 20).max(50).min(500) // 50-500 tokens
            }
            "dig" => {
                // DNS records are usually concise
                (output_size / 30).max(30).min(200) // 30-200 tokens
            }
            "whois" => {
                // Whois data can be verbose
                (output_size / 15).max(100).min(800) // 100-800 tokens
            }
            "ping" => {
                // Ping results are usually short
                (output_size / 40).max(20).min(150) // 20-150 tokens
            }
            _ => {
                // Default estimation
                (output_size / 25).max(40).min(400) // 40-400 tokens
            }
        }
    }

    pub fn estimate_total_tokens(&self, prompt: &str, tool_output: &str, tool_name: &str) -> TokenEstimate {
        let input_tokens = self.estimate_input_tokens(prompt, tool_output);
        let output_tokens = self.estimate_output_tokens(tool_name, tool_output.len());
        
        TokenEstimate {
            input_tokens,
            output_tokens,
            total_tokens: input_tokens + output_tokens,
        }
    }

    
}

impl Default for TokenManager {
    fn default() -> Self {
        Self::new()
    }
}

#[derive(Debug, Clone)]
pub struct TokenEstimate {
    pub input_tokens: usize,
    pub output_tokens: usize,
    pub total_tokens: usize,
}

#[derive(Debug, Clone)]
pub struct CostEstimate {
    pub total_cost: f64,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_token_estimation() {
        let token_manager = TokenManager::new();
        
        let text = "This is a simple test string with some words.";
        let tokens = token_manager.estimate_tokens(text, "english");
        
        assert!(tokens > 0);
        assert!(tokens < text.len()); // Should be less than character count
    }

    #[test]
    fn test_cost_calculation() {
        let token_manager = TokenManager::new();
        
        let tokens = TokenEstimate {
            input_tokens: 1000,
            output_tokens: 500,
            total_tokens: 1500,
        };
        
        let cost = token_manager.calculate_cost(tokens, 0.001, 0.002);
        
        assert_eq!(cost.input_cost, 0.001); // 1000/1000 * 0.001
        assert_eq!(cost.output_cost, 0.001); // 500/1000 * 0.002
        assert_eq!(cost.total_cost, 0.002);
    }

    #[test]
    fn test_optimization() {
        let token_manager = TokenManager::new();
        
        let long_text = "A".repeat(1000);
        let optimized = token_manager.optimize_for_token_limit(&long_text, 100, "english");
        
        assert!(optimized.len() <= long_text.len());
        assert!(optimized.len() > 0);
    }
}