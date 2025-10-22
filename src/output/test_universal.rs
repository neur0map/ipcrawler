#[cfg(test)]
mod tests {
    use crate::config::schema::{Tool, OutputType, OutputConfig, InstallerConfig};
    use crate::OutputParser;
    use crate::executor::runner::TaskResult;
    use crate::executor::queue::{TaskStatus, TaskId};
    use std::time::Duration;

    #[tokio::test]
    async fn test_universal_nmap_parsing() {
        let tool = Tool {
            name: "nmap".to_string(),
            description: "Network mapper".to_string(),
            command: "nmap".to_string(),
            sudo_command: None,
            script_path: None,
            installer: InstallerConfig::default(),
            timeout: 60,
            output: OutputConfig {
                output_type: OutputType::Raw,
                json_flag: None,
            },
        };

        let stdout = "Starting Nmap scan...
Nmap scan report for 192.168.1.1
Host is up (0.001s latency).
PORT   STATE SERVICE
22/tcp open  ssh
80/tcp open  http
443/tcp open  https";

        let result = TaskResult {
            task_id: TaskId("test1".to_string()),
            tool_name: "nmap".to_string(),
            target: "192.168.1.1".to_string(),
            port: None,
            status: TaskStatus::Completed {
                duration: Duration::from_millis(100),
                exit_code: 0,
            },
            stdout: stdout.to_string(),
            stderr: String::new(),
        };

        let findings = OutputParser::parse(&tool, &result, false).await.unwrap();
        
        assert!(!findings.is_empty());
        assert_eq!(findings.len(), 1);
        
        let finding = &findings[0];
        assert_eq!(finding.title, "nmap execution");
        assert!(finding.description.contains("port scan results"));
        assert_eq!(finding.full_stdout, stdout);
        assert!(finding.full_stderr.is_empty());
    }

    #[tokio::test]
    async fn test_universal_dig_parsing() {
        let tool = Tool {
            name: "dig".to_string(),
            description: "DNS lookup".to_string(),
            command: "dig".to_string(),
            sudo_command: None,
            script_path: None,
            installer: InstallerConfig::default(),
            timeout: 60,
            output: OutputConfig {
                output_type: OutputType::Raw,
                json_flag: None,
            },
        };

        let stdout = "Querying DNS for example.com...
example.com.		3600	IN	A	93.184.216.34
example.com.		3600	IN	AAAA	2606:2800:220:1:248:1893:25c8:1946";

        let result = TaskResult {
            task_id: TaskId("test2".to_string()),
            tool_name: "dig".to_string(),
            target: "example.com".to_string(),
            port: None,
            status: TaskStatus::Completed {
                duration: Duration::from_millis(50),
                exit_code: 0,
            },
            stdout: stdout.to_string(),
            stderr: String::new(),
        };

        let findings = OutputParser::parse(&tool, &result, false).await.unwrap();
        
        assert!(!findings.is_empty());
        assert_eq!(findings.len(), 1);
        
        let finding = &findings[0];
        assert_eq!(finding.title, "dig execution");
        assert!(finding.description.contains("lines of output"));
        assert_eq!(finding.full_stdout, stdout);
    }

    #[tokio::test]
    async fn test_universal_error_handling() {
        let tool = Tool {
            name: "nmap".to_string(),
            description: "Network mapper".to_string(),
            command: "nmap".to_string(),
            sudo_command: None,
            script_path: None,
            installer: InstallerConfig::default(),
            timeout: 60,
            output: OutputConfig {
                output_type: OutputType::Raw,
                json_flag: None,
            },
        };

        let stderr = "nmap: invalid option
Usage: nmap [Scan Type(s)] [Options] {target specification}";

        let result = TaskResult {
            task_id: TaskId("test3".to_string()),
            tool_name: "nmap".to_string(),
            target: "invalid".to_string(),
            port: None,
            status: TaskStatus::Failed {
                error: "Command failed".to_string(),
            },
            stdout: String::new(),
            stderr: stderr.to_string(),
        };

        let findings = OutputParser::parse(&tool, &result, false).await.unwrap();
        
        assert!(!findings.is_empty());
        assert_eq!(findings.len(), 1);
        
        let finding = &findings[0];
        assert_eq!(finding.title, "nmap execution");
        assert!(finding.description.contains("errors/warnings"));
        assert!(finding.full_stderr.contains("invalid option"));
    }
}