# LLM Integration Guide

## Overview

IPCrawler features advanced LLM integration for intelligent security analysis, supporting multiple providers and specialized security-focused prompts.

## Supported Providers

### OpenAI
- **Models**: GPT-3.5, GPT-4, GPT-4-turbo
- **API**: OpenAI API
- **Features**: Strong security analysis, comprehensive reporting

### Claude (Anthropic)
- **Models**: Claude-3-sonnet, Claude-3-opus, Claude-3-haiku
- **API**: Anthropic API
- **Features**: Detailed analysis, safety-focused responses

### Ollama
- **Models**: Llama3.1, CodeLlama, Mistral, and custom models
- **API**: Local Ollama server
- **Features**: Offline processing, privacy, custom models

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# OpenAI Configuration
OPENAI_API_KEY=sk-your-openai-api-key
OPENAI_MODEL=gpt-4
OPENAI_BASE_URL=https://api.openai.com

# Claude Configuration
ANTHROPIC_API_KEY=sk-ant-your-claude-api-key
CLAUDE_MODEL=claude-3-sonnet-20240229
CLAUDE_BASE_URL=https://api.anthropic.com

# Ollama Configuration
OLLAMA_MODEL=llama3.1
OLLAMA_BASE_URL=http://localhost:11434

# Generic fallback
LLM_API_KEY=your-api-key
```

### CLI Configuration

```bash
# Basic LLM usage
ipcrawler -t 192.168.1.1 -p 80 --use-llm

# Specify provider
ipcrawler -t 192.168.1.1 -p 80 --use-llm --llm-provider openai
ipcrawler -t 192.168.1.1 -p 80 --use-llm --llm-provider claude
ipcrawler -t 192.168.1.1 -p 80 --use-llm --llm-provider ollama

# Custom model
ipcrawler -t 192.168.1.1 -p 80 --use-llm --llm-model gpt-4-turbo

# Custom endpoint (for self-hosted or proxy)
ipcrawler -t 192.168.1.1 -p 80 --use-llm --llm-base-url http://localhost:8080

# API key via CLI (not recommended for production)
ipcrawler -t 192.168.1.1 -p 80 --use-llm --llm-api-key your-key
```

## LLM Features

### 1. Security Analysis Prompts

Specialized prompts for different types of security analysis:

#### Network Scan Analysis
```rust
// Automatically generated for nmap, masscan, etc.
let prompt = SecurityAnalysisPrompt::network_scan_prompt("nmap", output);
```

#### DNS Reconnaissance Analysis
```rust
// For dig, dnsenum, sublist3r, etc.
let prompt = SecurityAnalysisPrompt::dns_recon_prompt("dig", output);
```

#### Vulnerability Scan Analysis
```rust
// For nikto, sqlmap, nuclei, etc.
let prompt = SecurityAnalysisPrompt::vulnerability_scan_prompt("nikto", output);
```

#### Generic Analysis
```rust
// For any security tool output
let prompt = SecurityAnalysisPrompt::generic_analysis_prompt("tool", output);
```

### 2. Template System

Customizable prompt templates for specific use cases:

```rust
let template = PromptTemplate::new(
    "Web Application Security".to_string(),
    "Analyze this web scan for vulnerabilities: {tool_name}\nOutput: {output}\nFocus on OWASP Top 10.".to_string(),
);

let analysis = llm_client.analyze_with_template(&template, "nikto", output).await?;
```

### 3. Context-Aware Analysis

Maintain conversation context for better analysis:

```rust
let context = vec![
    Message { role: "system".to_string(), content: "You are a security expert".to_string() },
    Message { role: "user".to_string(), content: "Previous scan found open port 80".to_string() },
];

let analysis = llm_client.analyze_with_context("nmap", new_output, &context).await?;
```

## Universal Output Parser Integration

The LLM integrates seamlessly with the Universal Output Parser:

### Parsing Methods

1. **Standard Parsing** (`parse`)
   - Pattern-based parsing first
   - LLM enhancement for ambiguous findings
   - Best for general use

2. **LLM-Enhanced Parsing** (`parse_with_llm`)
   - Full LLM analysis of all output
   - Context-aware finding extraction
   - Enhanced severity assessment

3. **Synchronous Parsing** (`parse_sync`)
   - No LLM integration
   - Used in dry-run mode
   - Fast and lightweight

### Content Analysis

The `ContentAnalyzer` provides specialized analysis:

```rust
// Network scan analysis
let network_analysis = analyzer.analyze_network_scan("nmap", output);

// DNS reconnaissance analysis
let dns_analysis = analyzer.analyze_dns_recon("dig", output);

// Vulnerability analysis
let vuln_analysis = analyzer.analyze_vulnerability_scan("nikto", output);
```

## Error Handling

### Graceful Degradation

If LLM analysis fails, IPCrawler continues with standard parsing:

```rust
match llm_client.analyze_security_output(tool_name, output).await {
    Ok(analysis) => {
        // Use LLM-enhanced analysis
        findings.extend(parse_llm_findings(analysis));
    }
    Err(e) => {
        eprintln!("LLM analysis failed: {}, using standard parsing", e);
        // Fallback to pattern-based parsing
        findings.extend(parse_standard_patterns(output));
    }
}
```

### Connection Testing

Automatic connection testing on startup:

```rust
if let Err(e) = llm_client.test_connection().await {
    eprintln!("Warning: LLM connection failed: {}", e);
    eprintln!("Continuing without LLM analysis...");
    // Continue without LLM
}
```

## Performance Considerations

### Timeout Configuration

Default timeout is 30 seconds per LLM request:

```rust
let config = LLMConfig {
    timeout: Duration::from_secs(30),
    // ... other config
};
```

### Concurrent Requests

LLM requests are made sequentially to avoid rate limiting, but can be parallelized if needed.

### Caching

Consider implementing response caching for repeated analyses to reduce API calls and costs.

## Security Considerations

### API Key Management

- Use environment variables, not CLI arguments
- Rotate keys regularly
- Monitor API usage and costs
- Use least-privilege access

### Data Privacy

- OpenAI/Claude: Data sent to external servers
- Ollama: Local processing, full privacy
- Consider data sensitivity when choosing providers

### Input Sanitization

All tool outputs are sanitized before sending to LLMs to prevent injection attacks.

## Troubleshooting

### Common Issues

1. **API Key Errors**
   ```bash
   # Check environment variables
   echo $OPENAI_API_KEY
   
   # Test connection
   ipcrawler -t 127.0.0.1 -p 80 --use-llm --dry-run
   ```

2. **Connection Timeouts**
   ```bash
   # Increase timeout in code or use faster model
   ipcrawler -t 192.168.1.1 -p 80 --use-llm --llm-model gpt-3.5-turbo
   ```

3. **Ollama Connection Issues**
   ```bash
   # Check Ollama server
   curl http://localhost:11434/api/tags
   
   # Start Ollama server
   ollama serve
   ```

### Debug Mode

Enable verbose logging to debug LLM issues:

```bash
RUST_LOG=debug ipcrawler -t 192.168.1.1 -p 80 --use-llm --verbose
```

## Best Practices

### Prompt Engineering

- Use specific, security-focused prompts
- Include context about the tool and target
- Request structured output when possible
- Test prompts with different providers

### Cost Management

- Monitor API usage and costs
- Use local models (Ollama) for sensitive data
- Implement caching for repeated analyses
- Choose appropriate models for tasks

### Reliability

- Always have fallback parsing methods
- Test LLM connectivity before scans
- Handle rate limits gracefully
- Log LLM failures for debugging

## Examples

### Basic Security Analysis

```bash
# Analyze nmap results with GPT-4
ipcrawler -t 192.168.1.1 -p 1-1000 --use-llm --llm-provider openai --llm-model gpt-4
```

### Local Analysis with Ollama

```bash
# Private analysis with local Llama3.1
ipcrawler -t 192.168.1.0/24 -p common --use-llm --llm-provider ollama --llm-model llama3.1
```

### Comprehensive Web Assessment

```bash
# Full web assessment with Claude
ipcrawler -t example.com -p 80,443 --use-llm --llm-provider claude --verbose
```

The LLM integration transforms IPCrawler from a simple tool executor into an intelligent security analysis platform, providing context-aware insights and automated vulnerability assessments.