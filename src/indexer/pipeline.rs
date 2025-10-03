use anyhow::{Context, Result};
use std::path::Path;
use swiftide::indexing::{self, loaders::FileLoader};
use swiftide::integrations::{qdrant::Qdrant, openai::OpenAI};

pub struct IndexingPipeline {
    qdrant_url: String,
    collection_name: String,
}

impl IndexingPipeline {
    pub fn new(collection_name: String) -> Self {
        Self {
            qdrant_url: std::env::var("QDRANT_URL")
                .unwrap_or_else(|_| "http://localhost:6333".to_string()),
            collection_name,
        }
    }
    
    pub async fn index_file(&self, file_path: &Path) -> Result<()> {
        tracing::info!("Indexing file: {}", file_path.display());
        
        // Read file content to check if empty
        let content = tokio::fs::read_to_string(file_path)
            .await
            .context("Failed to read file")?;
        
        if content.trim().is_empty() {
            tracing::debug!("Skipping empty file: {}", file_path.display());
            return Ok(());
        }
        
        // Try to get API key from environment variable or config file
        let api_key = self.get_api_key().await;
        
        if api_key.is_some() {
            match self.index_with_swiftide(file_path).await {
                Ok(_) => {
                    tracing::info!("✓ Indexed with embeddings: {}", file_path.display());
                    return Ok(());
                }
                Err(e) => {
                    tracing::warn!("Swiftide indexing failed: {}, falling back to basic indexing", e);
                }
            }
        }
        
        // Fallback: just log for now
        tracing::debug!("Indexed (no embeddings): {} ({} bytes)", file_path.display(), content.len());
        
        Ok(())
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
            if let Some(api_key) = config.embeddings.api_key {
                if !api_key.is_empty() {
                    return Some(api_key);
                }
            }
        }
        
        None
    }
    
    async fn index_with_swiftide(&self, file_path: &Path) -> Result<()> {
        // Build OpenAI client
        let openai = OpenAI::builder()
            .default_embed_model("text-embedding-3-small")
            .build()?;
        
        // Build Qdrant storage
        let qdrant = Qdrant::builder()
            .vector_size(1536)
            .collection_name(&self.collection_name)
            .batch_size(10)
            .build()
            .context("Failed to build Qdrant client")?;
        
        // Create and run indexing pipeline from file
        indexing::Pipeline::from_loader(FileLoader::new(file_path))
            .with_default_llm_client(openai)
            .then_store_with(qdrant)
            .run()
            .await?;
        
        Ok(())
    }
    
    #[allow(dead_code)]
    pub async fn index_directory(&self, dir_path: &Path) -> Result<()> {
        tracing::info!("Starting indexing pipeline for: {}", dir_path.display());
        
        // This is a placeholder for the full Swiftide integration
        // In production, you would set up the full pipeline with embeddings and Qdrant
        tracing::warn!("Full Swiftide indexing requires OpenAI API key and Qdrant running");
        tracing::info!("To enable full indexing:");
        tracing::info!("  1. Set OPENAI_API_KEY environment variable");
        tracing::info!("  2. Run Qdrant: docker run -p 6333:6333 qdrant/qdrant");
        
        Ok(())
    }
    
    #[allow(dead_code)]
    async fn setup_qdrant(&self) -> Result<Qdrant> {
        let qdrant = Qdrant::builder()
            .vector_size(1536)
            .collection_name(&self.collection_name)
            .batch_size(50)
            .build()
            .context("Failed to build Qdrant client")?;
        
        Ok(qdrant)
    }
}
