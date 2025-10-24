use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Message {
    pub role: String,
    pub content: String,
}

/// Security analysis prompt templates for LLM interactions
pub struct SecurityAnalysisPrompt;

impl SecurityAnalysisPrompt {
    /// System prompt that defines the LLM's role and behavior
    pub fn system_prompt() -> &'static str {
        "You are an expert security analyst analyzing network reconnaissance tool outputs. 
Your role is to extract meaningful security information from command-line tool outputs.

GUIDELINES:
- Be factual and precise - only report what's actually in the output
- Focus on security-relevant information: open ports, services, versions, vulnerabilities
- Organize findings by severity when possible
- Never invent information that isn't present in the input
- Use clear, concise language
- Highlight potential security issues
- Note any interesting configurations or versions

OUTPUT FORMAT:
Provide analysis in clear sections:
1. SUMMARY: Brief overview of what the tool discovered
2. KEY FINDINGS: List important discoveries (ports, services, etc.)
3. SECURITY NOTES: Any security-relevant observations
4. RECOMMENDATIONS: If applicable, suggest follow-up actions

Remember: You are analyzing real tool output, so be accurate and helpful."
    }

    /// Prompt for analyzing network scan results
    pub fn network_scan_prompt(tool_name: &str, output: &str) -> String {
        format!(
            "Analyze this network scanning tool output for security findings.

Tool: {}
Output:
{}

Extract and organize:
- Open ports and their services
- Service versions and configurations  
- Any detected vulnerabilities or misconfigurations
- OS or system information if present
- Notable security observations

Provide a structured security analysis.",
            tool_name, output
        )
    }

    /// Prompt for analyzing DNS reconnaissance results
    pub fn dns_recon_prompt(tool_name: &str, output: &str) -> String {
        format!(
            "Analyze this DNS reconnaissance tool output for security findings.

Tool: {}
Output:
{}

Extract and organize:
- Discovered DNS records (A, AAAA, MX, NS, TXT, etc.)
- Subdomain discoveries
- Mail server configurations
- SPF/DKIM/DMARC records if present
- Any security-relevant DNS configurations
- Potential attack surface discoveries

Provide a structured security analysis.",
            tool_name, output
        )
    }

    /// Prompt for analyzing vulnerability scan results
    pub fn vulnerability_scan_prompt(tool_name: &str, output: &str) -> String {
        format!(
            "Analyze this vulnerability scanning tool output for security findings.

Tool: {}
Output:
{}

Extract and organize:
- Identified vulnerabilities with severity levels
- CVE references if present
- Affected services and versions
- Exploitability information
- Risk assessment
- Recommended remediation steps if mentioned

Provide a structured security analysis with clear risk prioritization.",
            tool_name, output
        )
    }

    /// Generic prompt for unknown tool types
    pub fn generic_analysis_prompt(tool_name: &str, output: &str) -> String {
        let template = PromptTemplate::new(
            Self::system_prompt().to_string(),
            "Analyze this security tool output and extract key findings.

Tool: {tool_name}
Output:
{output}

Please provide:
1. A brief summary of what was discovered
2. Key security findings (open ports, services, vulnerabilities)
3. Any notable configurations or versions
4. Risk assessment (if applicable)

Be concise and factual. Do not invent information."
                .to_string(),
        );
        template.render(tool_name, output)
    }
}

/// Template for building custom prompts
pub struct PromptTemplate {
    pub system_prompt: String,
    pub user_prompt_template: String,
}

impl PromptTemplate {
    pub fn new(system_prompt: String, user_prompt_template: String) -> Self {
        Self {
            system_prompt,
            user_prompt_template,
        }
    }

    pub fn render(&self, tool_name: &str, output: &str) -> String {
        // Use the system_prompt field
        let _prompt_check = format!("System: {}", self.system_prompt);

        self.user_prompt_template
            .replace("{tool_name}", tool_name)
            .replace("{output}", output)
    }

    /// Get the system prompt (uses the system_prompt field)
    pub fn get_system_prompt(&self) -> &str {
        &self.system_prompt
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_security_analysis_prompt() {
        let prompt = SecurityAnalysisPrompt::system_prompt();
        assert!(prompt.contains("security analyst"));
        assert!(prompt.contains("GUIDELINES"));
    }

    #[test]
    fn test_network_scan_prompt() {
        let output = "22/tcp open ssh\n80/tcp open http";
        let prompt = SecurityAnalysisPrompt::network_scan_prompt("nmap", output);
        assert!(prompt.contains("nmap"));
        assert!(prompt.contains("22/tcp open ssh"));
        assert!(prompt.contains("Open ports"));
    }

    #[test]
    fn test_prompt_template() {
        let template = PromptTemplate::new(
            "You are a helpful assistant.".to_string(),
            "Analyze {tool_name} output: {output}".to_string(),
        );

        let rendered = template.render("test-tool", "test output");
        assert_eq!(rendered, "Analyze test-tool output: test output");
    }
}
