use anyhow::{bail, Context, Result};
use colored::Colorize;
use std::process::Command;

const REPO_URL: &str = "https://github.com/neur0map/ipcrawler";
const CRATES_IO_API: &str = "https://crates.io/api/v1/crates/ipcrawler";

pub struct SelfUpdater {
    current_version: String,
    verbose: bool,
}

impl SelfUpdater {
    pub fn new(current_version: &str, verbose: bool) -> Self {
        Self {
            current_version: current_version.to_string(),
            verbose,
        }
    }

    pub async fn check_for_updates(&self) -> Result<Option<String>> {
        println!("{}", "Checking for updates...".cyan());

        // First try to get latest version from crates.io
        match self.get_latest_version_crates().await {
            Ok(latest) => {
                if self.is_newer(&latest, &self.current_version) {
                    println!(
                        "  {} Update available: {} -> {}",
                        "✓".green().bold(),
                        self.current_version.yellow(),
                        latest.green().bold()
                    );
                    Ok(Some(latest))
                } else {
                    println!(
                        "  {} You're on the latest version: {}",
                        "✓".green().bold(),
                        self.current_version.green()
                    );
                    Ok(None)
                }
            }
            Err(e) => {
                if self.verbose {
                    eprintln!("  {} Failed to check crates.io: {}", "⚠".yellow(), e);
                }
                // Fallback to git tags
                match self.get_latest_version_git().await {
                    Ok(latest) => {
                        if self.is_newer(&latest, &self.current_version) {
                            println!(
                                "  {} Update available: {} -> {}",
                                "✓".green().bold(),
                                self.current_version.yellow(),
                                latest.green().bold()
                            );
                            Ok(Some(latest))
                        } else {
                            println!(
                                "  {} You're on the latest version: {}",
                                "✓".green().bold(),
                                self.current_version.green()
                            );
                            Ok(None)
                        }
                    }
                    Err(e2) => {
                        bail!(
                            "Failed to check for updates from both crates.io and git: {} / {}",
                            e,
                            e2
                        );
                    }
                }
            }
        }
    }

    pub async fn update(&self) -> Result<()> {
        // Check if update is available
        let latest_version = match self.check_for_updates().await? {
            Some(version) => version,
            None => {
                println!("\n{}", "Already on the latest version!".green());
                return Ok(());
            }
        };

        println!("\n{}", "Starting self-update...".cyan().bold());

        // Detect cargo installation and channel
        let (cargo_path, channel) = self.detect_cargo()?;
        println!(
            "  {} Detected cargo: {} ({})",
            "✓".green(),
            cargo_path.dimmed(),
            channel.yellow()
        );

        // Determine installation method
        let install_method = self.determine_install_method(&cargo_path)?;

        match install_method {
            InstallMethod::CargoInstall => {
                println!("  {} Installing via cargo install...", "→".cyan());
                self.cargo_install(&cargo_path)?;
            }
            InstallMethod::GitClone => {
                println!("  {} Installing from git repository...", "→".cyan());
                self.git_install(&cargo_path)?;
            }
        }

        println!("\n{}", "✓ Update complete!".green().bold());
        println!("  Updated to version {}", latest_version.green().bold());

        Ok(())
    }

    fn detect_cargo(&self) -> Result<(String, String)> {
        // Try to find cargo
        let cargo_path = if let Ok(output) = Command::new("which").arg("cargo").output() {
            String::from_utf8_lossy(&output.stdout).trim().to_string()
        } else if let Ok(output) = Command::new("where").arg("cargo").output() {
            String::from_utf8_lossy(&output.stdout).trim().to_string()
        } else {
            bail!("Cargo not found. Please install Rust from https://rustup.rs/");
        };

        // Check cargo version to detect channel
        let output = Command::new("cargo")
            .arg("--version")
            .output()
            .context("Failed to get cargo version")?;

        let version_str = String::from_utf8_lossy(&output.stdout);
        let channel = if version_str.contains("nightly") {
            "nightly".to_string()
        } else if version_str.contains("beta") {
            "beta".to_string()
        } else if version_str.contains("stable") || version_str.contains("rustc") {
            "stable".to_string()
        } else {
            "unknown".to_string()
        };

        Ok((cargo_path, channel))
    }

    fn determine_install_method(&self, _cargo_path: &str) -> Result<InstallMethod> {
        // Check if we're in development (git repo exists)
        if std::path::Path::new(".git").exists() && std::path::Path::new("Cargo.toml").exists() {
            Ok(InstallMethod::GitClone)
        } else {
            Ok(InstallMethod::CargoInstall)
        }
    }

    fn cargo_install(&self, cargo_path: &str) -> Result<()> {
        let mut cmd = Command::new(cargo_path);
        cmd.args(["install", "--force", "ipcrawler"]);

        if self.verbose {
            println!("  Running: cargo install --force ipcrawler");
        }

        let status = cmd.status().context("Failed to run cargo install")?;

        if !status.success() {
            bail!("cargo install failed with exit code: {:?}", status.code());
        }

        Ok(())
    }

    fn git_install(&self, cargo_path: &str) -> Result<()> {
        println!("  {} Pulling latest changes...", "→".cyan());

        let status = Command::new("git")
            .args(["pull", "origin", "main"])
            .status()
            .context("Failed to run git pull")?;

        if !status.success() {
            bail!("git pull failed");
        }

        println!("  {} Building with cargo...", "→".cyan());

        let mut cmd = Command::new(cargo_path);
        cmd.args(["build", "--release"]);

        if self.verbose {
            cmd.arg("--verbose");
        }

        let status = cmd.status().context("Failed to run cargo build")?;

        if !status.success() {
            bail!("cargo build failed");
        }

        println!(
            "  {} Binary updated at: ./target/release/ipcrawler",
            "✓".green()
        );
        println!(
            "  {} Run 'cargo install --path .' to install globally",
            "💡".yellow()
        );

        Ok(())
    }

    async fn get_latest_version_crates(&self) -> Result<String> {
        let client = reqwest::Client::builder()
            .user_agent("ipcrawler-updater")
            .build()?;

        let response = client
            .get(CRATES_IO_API)
            .send()
            .await
            .context("Failed to fetch from crates.io")?;

        if !response.status().is_success() {
            bail!("crates.io returned status: {}", response.status());
        }

        let json: serde_json::Value = response.json().await?;

        let version = json["crate"]["max_version"]
            .as_str()
            .context("Failed to parse version from crates.io response")?
            .to_string();

        Ok(version)
    }

    async fn get_latest_version_git(&self) -> Result<String> {
        // Try to get latest git tag
        let output = Command::new("git")
            .args(["ls-remote", "--tags", REPO_URL])
            .output()
            .context("Failed to run git ls-remote")?;

        if !output.status.success() {
            bail!("git ls-remote failed");
        }

        let tags = String::from_utf8_lossy(&output.stdout);
        let mut versions: Vec<String> = tags
            .lines()
            .filter_map(|line| {
                let parts: Vec<&str> = line.split('/').collect();
                parts.last().map(|s| s.trim().to_string())
            })
            .filter(|v| v.starts_with('v') || v.chars().next().is_some_and(|c| c.is_ascii_digit()))
            .map(|v| v.trim_start_matches('v').to_string())
            .collect();

        versions.sort_by(|a, b| self.compare_versions(b, a));

        versions
            .first()
            .cloned()
            .context("No versions found in git tags")
    }

    fn is_newer(&self, version1: &str, version2: &str) -> bool {
        let v1 = self.parse_version(version1);
        let v2 = self.parse_version(version2);

        match (v1, v2) {
            (Some(v1_parts), Some(v2_parts)) => {
                for i in 0..3 {
                    if v1_parts[i] > v2_parts[i] {
                        return true;
                    } else if v1_parts[i] < v2_parts[i] {
                        return false;
                    }
                }
                false
            }
            _ => false,
        }
    }

    fn compare_versions(&self, a: &str, b: &str) -> std::cmp::Ordering {
        if self.is_newer(a, b) {
            std::cmp::Ordering::Greater
        } else if self.is_newer(b, a) {
            std::cmp::Ordering::Less
        } else {
            std::cmp::Ordering::Equal
        }
    }

    fn parse_version(&self, version: &str) -> Option<[u32; 3]> {
        let parts: Vec<&str> = version.trim_start_matches('v').split('.').collect();
        if parts.len() != 3 {
            return None;
        }

        Some([
            parts[0].parse().ok()?,
            parts[1].parse().ok()?,
            parts[2].parse().ok()?,
        ])
    }
}

enum InstallMethod {
    CargoInstall,
    GitClone,
}
