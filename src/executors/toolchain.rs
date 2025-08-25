use anyhow::{bail, Result};
use which::which;

const REQUIRED_TOOLS: &[&str] = &["nslookup", "dig"];

pub fn verify_or_bail() -> Result<()> {
    let mut missing = Vec::new();

    for tool in REQUIRED_TOOLS {
        match which(tool) {
            Ok(path) => {
                tracing::debug!("Found {}: {:?}", tool, path);
            }
            Err(_) => {
                missing.push(*tool);
            }
        }
    }

    if !missing.is_empty() {
        bail!(
            "Missing required tools: {}. Install them manually and run 'make verify'",
            missing.join(", ")
        );
    }

    tracing::info!("All required tools found");
    Ok(())
}
