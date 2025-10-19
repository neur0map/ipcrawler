use anyhow::Result;
use clap::{Args, Subcommand};
use colored::*;
use crate::storage::secure::SecureKeyStore;


#[derive(Args)]
pub struct KeyCommands {
    #[command(subcommand)]
    pub action: KeyAction,
}

#[derive(Subcommand)]
pub enum KeyAction {
    /// Set API key for a provider
    Set {
        #[arg(short, long)]
        provider: String,
        #[arg(short, long)]
        key: String,
    },
    /// Get stored API key
    Get {
        #[arg(short, long)]
        provider: String,
    },
    /// List all configured providers
    List,
    /// Remove API key
    Remove {
        #[arg(short, long)]
        provider: String,
    },
    /// Test API key validity
    Test {
        #[arg(short, long)]
        provider: String,
    },
}

pub async fn handle_keys_command(cmd: KeyCommands) -> anyhow::Result<()> {
    let key_store = SecureKeyStore::new()?;
    
    match cmd.action {
        KeyAction::Set { provider, key } => {
            key_store.store_key(&provider, &key)?;
            println!("{} API key stored for provider: {}", "✓".green(), provider);
        }
        KeyAction::Get { provider } => {
            match key_store.get_key(&provider)? {
                Some(key) => println!("API key for {}: {}...", provider, &key[..8.min(key.len())]),
                None => println!("{} No API key found for provider: {}", "Warning:".yellow(), provider),
            }
        }
        KeyAction::List => {
            let providers = ["openai", "groq", "openrouter", "ollama"];
            println!("Configured providers:");
            for provider in providers {
                match key_store.get_key(provider)? {
                    Some(_) => println!("  {} ✓", provider),
                    None => println!("  {} ✗", provider),
                }
            }
        }
        KeyAction::Remove { provider } => {
            key_store.remove_key(&provider)?;
            println!("{} API key removed for provider: {}", "✓".green(), provider);
        }
        KeyAction::Test { provider } => {
            match key_store.get_key(&provider)? {
                Some(api_key) => {
                    println!("{} Testing API key for provider: {}...", "Info:".blue(), provider);
                    match test_api_key(&provider, &api_key).await {
                        Ok(()) => println!("{} API key is valid for provider: {}", "Success:".green(), provider),
                        Err(e) => println!("{} API key test failed for provider {}: {}", "Error:".red(), provider, e),
                    }
                }
                None => println!("{} No API key found for provider: {}", "Error:".red(), provider),
            }
        }
    }
    
    Ok(())
}

async fn test_api_key(provider: &str, api_key: &str) -> Result<()> {
    match provider.to_lowercase().as_str() {
        "groq" => {
            // Test with a direct API call to verify connectivity
            let client = reqwest::Client::new();
            let response = client
                .post("https://api.groq.com/openai/v1/chat/completions")
                .header("Authorization", format!("Bearer {}", api_key))
                .header("Content-Type", "application/json")
                .json(&serde_json::json!({
                    "model": "llama-3.1-8b-instant",
                    "messages": [
                        {
                            "role": "user",
                            "content": "Respond with just 'OK' to test the connection."
                        }
                    ],
                    "max_tokens": 10
                }))
                .send()
                .await?;

            if response.status().is_success() {
                let json: serde_json::Value = response.json().await?;
                if let Some(choices) = json["choices"].as_array() {
                    if let Some(choice) = choices.first() {
                        if let Some(content) = choice["message"]["content"].as_str() {
                            if content.contains("OK") {
                                return Ok(());
                            }
                        }
                    }
                }
                Err(anyhow::anyhow!("Unexpected response format: {}", json))
            } else {
                Err(anyhow::anyhow!("API error: {}", response.status()))
            }
        }
        "openai" => {
            let client = reqwest::Client::new();
            let response = client
                .post("https://api.openai.com/v1/chat/completions")
                .header("Authorization", format!("Bearer {}", api_key))
                .header("Content-Type", "application/json")
                .json(&serde_json::json!({
                    "model": "gpt-3.5-turbo",
                    "messages": [
                        {
                            "role": "user",
                            "content": "Respond with just 'OK' to test the connection."
                        }
                    ],
                    "max_tokens": 10
                }))
                .send()
                .await?;

            if response.status().is_success() {
                let json: serde_json::Value = response.json().await?;
                if let Some(choices) = json["choices"].as_array() {
                    if let Some(choice) = choices.first() {
                        if let Some(content) = choice["message"]["content"].as_str() {
                            if content.contains("OK") {
                                return Ok(());
                            }
                        }
                    }
                }
                Err(anyhow::anyhow!("Unexpected response format: {}", json))
            } else {
                Err(anyhow::anyhow!("API error: {}", response.status()))
            }
        }
        "openrouter" => {
            let client = reqwest::Client::new();
            let response = client
                .post("https://openrouter.ai/api/v1/chat/completions")
                .header("Authorization", format!("Bearer {}", api_key))
                .header("Content-Type", "application/json")
                .json(&serde_json::json!({
                    "model": "meta-llama/llama-3.1-8b-instruct:free",
                    "messages": [
                        {
                            "role": "user",
                            "content": "Respond with just 'OK' to test the connection."
                        }
                    ],
                    "max_tokens": 10
                }))
                .send()
                .await?;

            if response.status().is_success() {
                let json: serde_json::Value = response.json().await?;
                if let Some(choices) = json["choices"].as_array() {
                    if let Some(choice) = choices.first() {
                        if let Some(content) = choice["message"]["content"].as_str() {
                            if content.contains("OK") {
                                return Ok(());
                            }
                        }
                    }
                }
                Err(anyhow::anyhow!("Unexpected response format: {}", json))
            } else {
                Err(anyhow::anyhow!("API error: {}", response.status()))
            }
        }
        "ollama" => {
            // Ollama uses a URL instead of API key, so we test connectivity
            let client = reqwest::Client::new();
            let response = client
                .post(&format!("{}/api/generate", api_key))
                .header("Content-Type", "application/json")
                .json(&serde_json::json!({
                    "model": "llama3.1:8b",
                    "prompt": "Respond with just 'OK' to test the connection.",
                    "stream": false
                }))
                .send()
                .await?;

            if response.status().is_success() {
                let json: serde_json::Value = response.json().await?;
                if let Some(response) = json["response"].as_str() {
                    if response.contains("OK") {
                        return Ok(());
                    }
                }
                Err(anyhow::anyhow!("Unexpected response format: {}", json))
            } else {
                Err(anyhow::anyhow!("API error: {}", response.status()))
            }
        }
        _ => Err(anyhow::anyhow!("Unsupported provider: {}", provider)),
    }
}