use std::time::{SystemTime, UNIX_EPOCH};
use regex::Regex;

pub fn new_run_id(target: &str) -> String {
    let timestamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("Time went backwards")
        .as_secs();
    
    // Sanitize target for use in filesystem paths
    let sanitized = sanitize_target(target);
    
    format!("run_{}_{}", sanitized, timestamp)
}

fn sanitize_target(target: &str) -> String {
    // Replace characters that aren't safe for filenames
    let re = Regex::new(r"[^a-zA-Z0-9\-_\.]").unwrap();
    re.replace_all(target, "_").to_string()
}