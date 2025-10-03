use anyhow::{Result, Context};
use std::path::Path;
use qdrant_client::{Qdrant as QdrantClient, qdrant::{SearchPoints, with_payload_selector::SelectorOptions, WithPayloadSelector}};

pub struct QueryEngine {
    collection_name: String,
    top_k: usize,
}

impl QueryEngine {
    pub fn new(collection_name: String, top_k: usize) -> Self {
        Self {
            collection_name,
            top_k,
        }
    }
    
    pub async fn query(&self, question: &str, output_dir: &Path) -> Result<String> {
        tracing::info!("Querying: {}", question);
        
        // Try to get API key from environment variable or config file
        let api_key = self.get_api_key().await;
        
        if let Some(key) = api_key {
            if !key.is_empty() {
                tracing::info!("Attempting RAG query with vector search...");
                match self.query_with_rag_internal(question, &key).await {
                    Ok(response) => {
                        tracing::info!("✓ RAG query successful");
                        return Ok(response);
                    }
                    Err(e) => {
                        tracing::warn!("RAG query failed: {}, falling back to text search", e);
                    }
                }
            }
        } else {
            tracing::debug!("No API key available (check OPENAI_API_KEY env var or config file)");
        }
        
        self.fallback_search(question, output_dir).await
    }
    
    async fn get_api_key(&self) -> Option<String> {
        // First try environment variable
        if let Ok(key) = std::env::var("OPENAI_API_KEY") {
            if !key.is_empty() {
                return Some(key);
            }
        }
        
        // Then try config file
        if let Ok(config) = crate::setup::config::Config::load() {
            if let Some(api_key) = config.llm.api_key {
                if !api_key.is_empty() {
                    return Some(api_key);
                }
            }
        }
        
        None
    }
    
    async fn query_with_rag_internal(&self, question: &str, api_key: &str) -> Result<String> {
        // Step 1: Create embedding for the question using OpenAI
        let embedding = self.create_embedding(question, api_key).await?;
        
        // Step 2: Search Qdrant for similar vectors
        let qdrant_url = std::env::var("QDRANT_URL")
            .unwrap_or_else(|_| "http://localhost:6333".to_string());
        
        let client = QdrantClient::from_url(&qdrant_url)
            .build()
            .context("Failed to connect to Qdrant")?;
        
        let search_result = client
            .search_points(SearchPoints {
                collection_name: self.collection_name.clone(),
                vector: embedding.clone(),
                limit: self.top_k as u64,
                with_payload: Some(WithPayloadSelector {
                    selector_options: Some(SelectorOptions::Enable(true)),
                }),
                ..Default::default()
            })
            .await
            .context("Failed to search Qdrant")?;
        
        // Step 3: Extract context from retrieved chunks
        let context = search_result
            .result
            .iter()
            .filter_map(|point| {
                point.payload.get("chunk").and_then(|v| {
                    if let Some(qdrant_client::qdrant::value::Kind::StringValue(s)) = &v.kind {
                        Some(s.clone())
                    } else {
                        None
                    }
                })
            })
            .collect::<Vec<_>>()
            .join("\n\n---\n\n");
        
        if context.trim().is_empty() {
            anyhow::bail!("No relevant context found in vector database");
        }
        
        tracing::debug!("Retrieved {} chunks from Qdrant", search_result.result.len());
        
        // Step 4: Build prompt with context
        let prompt = format!(
            "You are a penetration testing assistant analyzing scan results.\n\n\
            Based on the following reconnaissance data, please answer the question.\n\n\
            Context from scans:\n{}\n\n\
            Question: {}\n\n\
            Please provide a clear, concise answer focusing on security findings and recommendations.",
            context, question
        );
        
        // Step 5: Get completion from OpenAI
        let answer = self.get_completion(&prompt, api_key).await?;
        
        Ok(answer)
    }
    
    async fn create_embedding(&self, text: &str, api_key: &str) -> Result<Vec<f32>> {
        let client = reqwest::Client::new();
        
        let response = client
            .post("https://api.openai.com/v1/embeddings")
            .header("Authorization", format!("Bearer {}", api_key))
            .header("Content-Type", "application/json")
            .json(&serde_json::json!({
                "input": text,
                "model": "text-embedding-3-small"
            }))
            .send()
            .await
            .context("Failed to call OpenAI embeddings API")?;
        
        let json: serde_json::Value = response.json().await?;
        
        let embedding = json["data"][0]["embedding"]
            .as_array()
            .context("Invalid embedding response")?
            .iter()
            .filter_map(|v| v.as_f64().map(|f| f as f32))
            .collect();
        
        Ok(embedding)
    }
    
    async fn get_completion(&self, prompt: &str, api_key: &str) -> Result<String> {
        let client = reqwest::Client::new();
        
        let response = client
            .post("https://api.openai.com/v1/chat/completions")
            .header("Authorization", format!("Bearer {}", api_key))
            .header("Content-Type", "application/json")
            .json(&serde_json::json!({
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful penetration testing assistant."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.3
            }))
            .send()
            .await
            .context("Failed to call OpenAI chat API")?;
        
        let json: serde_json::Value = response.json().await?;
        
        let answer = json["choices"][0]["message"]["content"]
            .as_str()
            .context("Invalid completion response")?
            .to_string();
        
        Ok(answer)
    }
    
    async fn fallback_search(&self, question: &str, output_dir: &Path) -> Result<String> {
        tracing::info!("Using fallback text search (RAG not available)");
        
        let mut results = Vec::new();
        let question_lower = question.to_lowercase();
        
        // Simple grep-like search through files
        if let Ok(entries) = tokio::fs::read_dir(output_dir).await {
            let mut entries = entries;
            while let Ok(Some(entry)) = entries.next_entry().await {
                let path = entry.path();
                
                if path.is_file() {
                    if let Ok(content) = tokio::fs::read_to_string(&path).await {
                        // Search for question terms in content
                        let matching_lines: Vec<_> = content
                            .lines()
                            .enumerate()
                            .filter(|(_, line)| {
                                let line_lower = line.to_lowercase();
                                question_lower.split_whitespace().any(|term| {
                                    term.len() > 3 && line_lower.contains(term)
                                })
                            })
                            .take(3)
                            .collect();
                        
                        if !matching_lines.is_empty() {
                            results.push(format!(
                                "\n📄 {}:\n{}",
                                path.display(),
                                matching_lines
                                    .iter()
                                    .map(|(num, line)| format!("  Line {}: {}", num + 1, line.trim()))
                                    .collect::<Vec<_>>()
                                    .join("\n")
                            ));
                        }
                    }
                }
                
                // Also search subdirectories
                if path.is_dir() {
                    if let Ok(sub_results) = self.search_directory(&path, &question_lower).await {
                        results.extend(sub_results);
                    }
                }
            }
        }
        
        if results.is_empty() {
            Ok(format!(
                "No results found for: '{}'\n\nTo enable AI-powered querying:\n  \
                1. Set OPENAI_API_KEY environment variable\n  \
                2. Run Qdrant: docker run -p 6333:6333 qdrant/qdrant\n  \
                3. Re-run reconnaissance to index data",
                question
            ))
        } else {
            Ok(format!(
                "Found {} matching files (basic search):\n{}",
                results.len(),
                results.join("\n")
            ))
        }
    }
    
    async fn search_directory(&self, dir: &Path, query: &str) -> Result<Vec<String>> {
        let mut results = Vec::new();
        
        if let Ok(entries) = tokio::fs::read_dir(dir).await {
            let mut entries = entries;
            while let Ok(Some(entry)) = entries.next_entry().await {
                let path = entry.path();
                
                if path.is_file() {
                    if let Ok(content) = tokio::fs::read_to_string(&path).await {
                        let matching_lines: Vec<_> = content
                            .lines()
                            .enumerate()
                            .filter(|(_, line)| {
                                let line_lower = line.to_lowercase();
                                query.split_whitespace().any(|term| {
                                    term.len() > 3 && line_lower.contains(term)
                                })
                            })
                            .take(3)
                            .collect();
                        
                        if !matching_lines.is_empty() {
                            results.push(format!(
                                "\n📄 {}:\n{}",
                                path.display(),
                                matching_lines
                                    .iter()
                                    .map(|(num, line)| format!("  Line {}: {}", num + 1, line.trim()))
                                    .collect::<Vec<_>>()
                                    .join("\n")
                            ));
                        }
                    }
                }
            }
        }
        
        Ok(results)
    }
}
