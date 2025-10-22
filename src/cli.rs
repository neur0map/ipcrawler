use clap::Parser;
use std::path::PathBuf;

#[derive(Parser, Debug)]
#[command(name = "ipcrawler")]
#[command(about = "Automated penetration testing tool", long_about = None)]
#[command(version)]
pub struct Cli {
    #[arg(short, long, help = "Target: IP, CIDR, or file path")]
    pub target: String,

    #[arg(
        short,
        long,
        help = "Ports: list (22,80), range (1-1000), or mode (fast/top-1000/top-10000/all/common)"
    )]
    pub ports: String,

    #[arg(
        short,
        long,
        help = "Output directory (default: ./ipcrawler-results/{timestamp}/)"
    )]
    pub output: Option<PathBuf>,

    #[arg(
        long,
        help = "Auto-install missing tools without prompting",
        default_value = "false"
    )]
    pub install: bool,

    #[arg(long, help = "Path to tools directory", default_value = "tools")]
    pub tools_dir: PathBuf,

    #[arg(
        short = 'w',
        long,
        help = "Wordlist: name from config (e.g., 'common', 'big') or custom path",
        default_value = "common"
    )]
    pub wordlist: String,
}

use anyhow::{Context, Result};
use ipnetwork::IpNetwork;
use std::fs::File;
use std::io::{BufRead, BufReader};
use std::net::IpAddr;
use std::str::FromStr;

pub fn parse_targets(input: &str) -> Result<Vec<String>> {
    if std::path::Path::new(input).exists() {
        parse_targets_from_file(input)
    } else if let Ok(network) = IpNetwork::from_str(input) {
        Ok(expand_cidr(network))
    } else if let Ok(_ip) = IpAddr::from_str(input) {
        Ok(vec![input.to_string()])
    } else {
        anyhow::bail!("Invalid target format: {}", input)
    }
}

fn parse_targets_from_file(path: &str) -> Result<Vec<String>> {
    let file = File::open(path).with_context(|| format!("Failed to open target file: {}", path))?;

    let reader = BufReader::new(file);
    let mut targets = Vec::new();

    for line in reader.lines() {
        let line = line?;
        let trimmed = line.trim();

        if trimmed.is_empty() || trimmed.starts_with('#') {
            continue;
        }

        if let Ok(network) = IpNetwork::from_str(trimmed) {
            targets.extend(expand_cidr(network));
        } else if let Ok(_ip) = IpAddr::from_str(trimmed) {
            targets.push(trimmed.to_string());
        } else {
            eprintln!("Warning: Skipping invalid target in file: {}", trimmed);
        }
    }

    if targets.is_empty() {
        anyhow::bail!("No valid targets found in file: {}", path);
    }

    Ok(targets)
}

fn expand_cidr(network: IpNetwork) -> Vec<String> {
    network.iter().map(|ip| ip.to_string()).collect()
}

pub fn parse_ports(input: &str) -> Result<Vec<u16>> {
    match input.to_lowercase().as_str() {
        "common" | "fast" => Ok(common_ports()),
        "top-1000" => Ok((1..=1000).collect()),
        "top-10000" => Ok((1..=10000).collect()),
        "all" => Ok((1..=65535).collect()),
        _ => {
            if input.contains('-') {
                parse_port_range(input)
            } else if input.contains(',') {
                parse_port_list(input)
            } else {
                let port = input
                    .parse::<u16>()
                    .with_context(|| format!("Invalid port number: {}", input))?;
                Ok(vec![port])
            }
        }
    }
}

fn parse_port_range(input: &str) -> Result<Vec<u16>> {
    let parts: Vec<&str> = input.split('-').collect();
    if parts.len() != 2 {
        anyhow::bail!("Invalid port range format: {}", input);
    }

    let start = parts[0]
        .trim()
        .parse::<u16>()
        .with_context(|| format!("Invalid start port: {}", parts[0]))?;
    let end = parts[1]
        .trim()
        .parse::<u16>()
        .with_context(|| format!("Invalid end port: {}", parts[1]))?;

    if start > end {
        anyhow::bail!("Start port must be less than or equal to end port");
    }

    Ok((start..=end).collect())
}

fn parse_port_list(input: &str) -> Result<Vec<u16>> {
    input
        .split(',')
        .map(|s| {
            s.trim()
                .parse::<u16>()
                .with_context(|| format!("Invalid port in list: {}", s))
        })
        .collect()
}

fn common_ports() -> Vec<u16> {
    vec![
        21, 22, 23, 25, 53, 80, 110, 143, 443, 445, 3306, 3389, 5432, 8080, 8443,
    ]
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_single_ip() {
        let targets = parse_targets("192.168.1.1").unwrap();
        assert_eq!(targets, vec!["192.168.1.1"]);
    }

    #[test]
    fn test_parse_cidr() {
        let targets = parse_targets("192.168.1.0/30").unwrap();
        assert_eq!(targets.len(), 4);
    }

    #[test]
    fn test_parse_single_port() {
        let ports = parse_ports("80").unwrap();
        assert_eq!(ports, vec![80]);
    }

    #[test]
    fn test_parse_port_list() {
        let ports = parse_ports("80,443,8080").unwrap();
        assert_eq!(ports, vec![80, 443, 8080]);
    }

    #[test]
    fn test_parse_port_range() {
        let ports = parse_ports("80-82").unwrap();
        assert_eq!(ports, vec![80, 81, 82]);
    }

    #[test]
    fn test_parse_common_ports() {
        let ports = parse_ports("common").unwrap();
        assert_eq!(ports.len(), 15);
        assert!(ports.contains(&80));
        assert!(ports.contains(&443));
    }

    #[test]
    fn test_parse_fast_mode() {
        let ports = parse_ports("fast").unwrap();
        assert!(!ports.is_empty());
        assert!(ports.contains(&80));
    }

    #[test]
    fn test_parse_top_1000() {
        let ports = parse_ports("top-1000").unwrap();
        assert_eq!(ports.len(), 1000);
        assert!(ports.contains(&80));
        assert!(ports.contains(&443));
    }

    #[test]
    fn test_parse_all_ports() {
        let ports = parse_ports("all").unwrap();
        assert_eq!(ports.len(), 65535);
        assert!(ports.contains(&1));
        assert!(ports.contains(&65535));
    }
}
