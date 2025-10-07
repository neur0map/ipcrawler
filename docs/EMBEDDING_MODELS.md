# Embedding Models Documentation

This document explains the embedding models supported by IPCrawler and how to configure them for RAG (Retrieval-Augmented Generation) functionality.

## What are Embedding Models?

Embedding models convert text into numerical vectors that capture semantic meaning. These vectors are used to:
- Find relevant context from scan results
- Improve LLM understanding of technical security terms
- Enable better information retrieval from reports
- Enhance semantic search across vulnerability data

## Supported Providers

IPCrawler supports three types of embedding models:
1. **Ollama** - Local models, easy installation
2. **ONNX** - Optimized local models, fast inference
3. **Cloud** - OpenAI, Anthropic (API-based)

### Ollama Models (Local, Recommended)

Ollama provides free, open-source embedding models that run locally:

#### Available Models:

1. **nomic-embed-text** ⭐ (Recommended)
   - Parameters: 137M
   - Dimensions: 768
   - Context: 8192 tokens
   - Best for: General security/technical text
   - Performance: Outperforms OpenAI text-embedding-ada-002
   - Size: ~523 MB
   - Install: `ollama pull nomic-embed-text`

2. **mxbai-embed-large**
   - Parameters: 335M
   - Dimensions: 1024
   - Context: 512 tokens
   - Best for: High-accuracy retrieval
   - Performance: State-of-the-art for technical docs
   - Size: ~670 MB
   - Install: `ollama pull mxbai-embed-large`

3. **all-minilm**
   - Parameters: 23M
   - Dimensions: 384
   - Context: 256 tokens
   - Best for: Fast prototyping, limited resources
   - Performance: Good balance of speed/quality
   - Size: ~90 MB
   - Install: `ollama pull all-minilm`

4. **snowflake-arctic-embed-m**
   - Parameters: 109M
   - Dimensions: 768
   - Context: 512 tokens
   - Best for: Retrieval-focused tasks
   - Performance: Strong on search benchmarks
   - Size: ~220 MB
   - Install: `ollama pull snowflake-arctic-embed-m`

5. **bge-small-en-v1.5**
   - Parameters: 33M
   - Dimensions: 384
   - Context: 512 tokens
   - Best for: Efficient general-purpose use
   - Performance: Competitive with larger models
   - Size: ~130 MB
   - Install: `ollama pull bge-small-en-v1.5`

### ONNX Models (Local, Ultra-Fast)

ONNX models are optimized for fast CPU inference using sentence-transformers:

1. **all-MiniLM-L6-v2** ⭐ (Fastest)
   - Size: 80 MB
   - Dimensions: 384
   - Context: 256 tokens
   - Best for: Maximum speed, low resource usage
   - Inference: ~10ms per sentence on CPU
   - Install: Automatic on first use

2. **bge-small-en-v1.5**
   - Size: 130 MB
   - Dimensions: 384
   - Context: 512 tokens
   - Best for: Balanced speed/accuracy
   - Performance: Good for technical terminology
   - Install: Automatic on first use

3. **e5-small-v2**
   - Size: 130 MB
   - Dimensions: 384
   - Context: 512 tokens
   - Best for: Multilingual support
   - Languages: 100+ languages
   - Install: Automatic on first use

**Note**: ONNX models don't require Ollama and run purely via Python sentence-transformers library. They're automatically downloaded from HuggingFace on first use.

### Cloud Providers

#### OpenAI
- **text-embedding-3-small** (default) - Cost-effective, good performance
- **text-embedding-3-large** - Higher accuracy, more expensive
- **text-embedding-ada-002** - Legacy model

#### Anthropic
- Built-in embedding with Claude models
- No separate model configuration needed

#### Groq
- Uses model's built-in embedding capabilities
- No separate embedding model needed

## Configuration

### Using Setup Wizard

Run `ipcrawler setup` and follow the prompts. The wizard will:
1. Detect your LLM provider
2. Show recommended embedding models
3. Allow you to choose a custom model (for Ollama)
4. Automatically use defaults for cloud providers

### Manual Configuration

Edit `~/.config/ipcrawler/config.toml`:

```toml
[llm]
provider = "ollama"
model = "llama3.2"
embedding_model = "nomic-embed-text"  # Optional for Ollama

[defaults]
templates_dir = "templates"
verbose = false
```

## Installation

### Ollama Models

Install embedding models with:

```bash
# Install the recommended model
ollama pull nomic-embed-text

# Install other options
ollama pull mxbai-embed-large
ollama pull all-minilm
ollama pull snowflake-arctic-embed
```

### Cloud Provider Setup

For cloud providers, ensure your API key has access to embedding endpoints:
- OpenAI: Requires standard API key
- Anthropic: Works with Claude API
- Groq: Works with Groq API key

## Performance Comparison

Based on MTEB (Massive Text Embedding Benchmark) and real-world usage:

### Ollama Models

| Model | Parameters | Dimensions | Size | Speed | Quality | Best For |
|-------|------------|------------|------|-------|---------|----------|
| nomic-embed-text | 137M | 768 | 523MB | Fast | Excellent | General security text ⭐ |
| mxbai-embed-large | 335M | 1024 | 670MB | Medium | Excellent | High-accuracy retrieval |
| snowflake-arctic-embed-m | 109M | 768 | 220MB | Fast | Very Good | Search-focused tasks |
| bge-small-en-v1.5 | 33M | 384 | 130MB | Very Fast | Good | Resource-efficient |
| all-minilm | 23M | 384 | 90MB | Ultra Fast | Good | Speed-critical apps |

### ONNX Models (CPU-Optimized)

| Model | Size | Dimensions | Inference Time | Quality | Best For |
|-------|------|------------|----------------|---------|----------|
| all-MiniLM-L6-v2 | 80MB | 384 | ~10ms | Good | Maximum speed ⚡ |
| bge-small-en-v1.5 | 130MB | 384 | ~15ms | Very Good | Balanced use |
| e5-small-v2 | 130MB | 384 | ~15ms | Very Good | Multilingual |

### Cloud Models

| Model | Dimensions | Speed | Cost | Quality |
|-------|------------|-------|------|---------|
| text-embedding-3-small | 1536 | Fast | $0.02/1M tokens | Very Good |
| text-embedding-3-large | 3072 | Fast | $0.13/1M tokens | Excellent |
| text-embedding-ada-002 | 1536 | Fast | $0.10/1M tokens | Good (legacy) |

**Recommendations by Use Case:**
- **Best overall**: nomic-embed-text (Ollama)
- **Fastest**: all-MiniLM-L6-v2 (ONNX)
- **Highest quality**: mxbai-embed-large (Ollama)
- **Most efficient**: bge-small-en-v1.5 (Ollama or ONNX)
- **Cloud/API**: text-embedding-3-small (OpenAI)

## Troubleshooting

### Common Issues

1. **Model not found** - Ensure the model is installed:
   ```bash
   ollama pull nomic-embed-text
   ```

2. **API permission errors** - Check that your API key has embedding permissions

3. **Performance issues** - Try smaller models like `all-minilm` for faster processing

4. **Memory constraints** - Use smaller embedding models if you have limited RAM

### Testing Embeddings

Test your embedding configuration:

```bash
# Check configuration
ipcrawler config

# Run a quick scan to test
ipcrawler --target example.com --verbose
```

## Future Enhancements

Planned improvements include:
- Automatic model selection based on system resources
- Fine-tuned cybersecurity embeddings
- Support for additional providers (Cohere, HuggingFace)
- Distributed embedding processing

## References

- [Ollama Embeddings Blog](https://ollama.com/blog/embedding-models)
- [Nomic Embed Text](https://ollama.com/library/nomic-embed-text)
- [MTEB Benchmark](https://huggingface.co/spaces/mteb/leaderboard)
- [OpenAI Embeddings](https://platform.openai.com/docs/guides/embeddings)
