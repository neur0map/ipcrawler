use clap::{Args, Subcommand};
use anyhow::Result;
use clap::Args;
use clap::Subcommand;
use colored::*;
use crate::storage::secure::SecureKeyStore;
use crate::providers::{LLMProvider, groq::GroqProvider, openai::OpenAIProvider, openrouter::OpenRouterProvider, ollama::OllamaProvider};

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
                Some(_) => {
                    // TODO: Implement actual API key testing
                    println!("{} API key test not yet implemented for provider: {}", "Info:".blue(), provider);
                }
                None => println!("{} No API key found for provider: {}", "Error:".red(), provider),
            }
        }
    }
    
    Ok(())
}