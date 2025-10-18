use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;
use chrono::{DateTime, Utc, Datelike};
use dirs::home_dir;

use crate::optimization::tokens::{TokenEstimate, CostEstimate};

#[derive(Debug, Default, Clone, Serialize, Deserialize)]
pub struct UsageStats {
    pub tokens_used: usize,
    pub cost: f64,
    pub requests: usize,
    pub last_reset: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CostLimits {
    pub max_cost_per_request: f64,
    pub daily_limit: f64,
    pub monthly_limit: f64,
}

impl Default for CostLimits {
    fn default() -> Self {
        Self {
            max_cost_per_request: 0.01,  // $0.01 per request
            daily_limit: 1.0,            // $1.00 per day
            monthly_limit: 30.0,         // $30.00 per month
        }
    }
}

pub struct CostTracker {
    limits: CostLimits,
    usage_file: PathBuf,
    current_usage: HashMap<String, UsageStats>,
    daily_usage: UsageStats,
    monthly_usage: UsageStats,
}

impl CostTracker {
    pub fn new(max_cost_per_request: f64) -> Result<Self> {
        let mut limits = CostLimits::default();
        limits.max_cost_per_request = max_cost_per_request;
        
        let mut usage_file = home_dir().context("Could not find home directory")?;
        usage_file.push(".ipcrawler");
        usage_file.push("usage.json");

        let mut tracker = Self {
            limits,
            usage_file,
            current_usage: HashMap::new(),
            daily_usage: UsageStats::default(),
            monthly_usage: UsageStats::default(),
        };

        tracker.load_usage()?;
        tracker.cleanup_old_usage()?;
        
        Ok(tracker)
    }

    

    fn load_usage(&mut self) -> Result<()> {
        if !self.usage_file.exists() {
            return Ok(());
        }

        let content = fs::read_to_string(&self.usage_file)
            .context("Failed to read usage file")?;
        
        let data: serde_json::Value = serde_json::from_str(&content)
            .context("Failed to parse usage file")?;

        // Load per-provider usage
        if let Some(providers) = data["providers"].as_object() {
            for (provider, stats) in providers {
                if let Ok(stats) = serde_json::from_value::<UsageStats>(stats.clone()) {
                    self.current_usage.insert(provider.clone(), stats);
                }
            }
        }

        // Load daily usage
        if let Some(daily) = data["daily"].as_object() {
            if let Ok(stats) = serde_json::from_value::<UsageStats>(serde_json::Value::Object(daily.clone())) {
                self.daily_usage = stats;
            }
        }

        // Load monthly usage
        if let Some(monthly) = data["monthly"].as_object() {
            if let Ok(stats) = serde_json::from_value::<UsageStats>(serde_json::Value::Object(monthly.clone())) {
                self.monthly_usage = stats;
            }
        }

        Ok(())
    }

    fn save_usage(&self) -> Result<()> {
        // Ensure directory exists
        if let Some(parent) = self.usage_file.parent() {
            fs::create_dir_all(parent)?;
        }

        let mut data = serde_json::Map::new();
        
        // Save per-provider usage
        let mut providers = serde_json::Map::new();
        for (provider, stats) in &self.current_usage {
            providers.insert(provider.clone(), serde_json::to_value(stats)?);
        }
        data.insert("providers".to_string(), serde_json::Value::Object(providers));
        
        // Save daily usage
        data.insert("daily".to_string(), serde_json::to_value(&self.daily_usage)?);
        
        // Save monthly usage
        data.insert("monthly".to_string(), serde_json::to_value(&self.monthly_usage)?);

        let json_data = serde_json::to_string_pretty(&data)?;
        fs::write(&self.usage_file, json_data)
            .context("Failed to write usage file")?;

        Ok(())
    }

    fn cleanup_old_usage(&mut self) -> Result<()> {
        let now = Utc::now();
        let mut needs_save = false;

        // Reset daily usage if it's from a different day
        if now.date_naive() != self.daily_usage.last_reset.date_naive() {
            self.daily_usage = UsageStats {
                last_reset: now,
                ..Default::default()
            };
            needs_save = true;
        }

        // Reset monthly usage if it's from a different month
        if (now.year(), now.month()) != (self.monthly_usage.last_reset.year(), self.monthly_usage.last_reset.month()) {
            self.monthly_usage = UsageStats {
                last_reset: now,
                ..Default::default()
            };
            needs_save = true;
        }

        if needs_save {
            self.save_usage()?;
        }

        Ok(())
    }

    pub fn should_proceed(&self, estimated_cost: f64, _provider: &str) -> bool {
        // Check per-request limit
        if estimated_cost > self.limits.max_cost_per_request {
            return false;
        }

        // Check daily limit
        if self.daily_usage.cost + estimated_cost > self.limits.daily_limit {
            return false;
        }

        // Check monthly limit
        if self.monthly_usage.cost + estimated_cost > self.limits.monthly_limit {
            return false;
        }

        true
    }

    pub fn track_usage(&mut self, provider: &str, tokens: &TokenEstimate, cost: &CostEstimate) -> Result<()> {
        let now = Utc::now();
        
        // Update provider-specific usage
        let provider_stats = self.current_usage.entry(provider.to_string()).or_insert_with(|| UsageStats {
            last_reset: now,
            ..Default::default()
        });
        
        provider_stats.tokens_used += tokens.total_tokens;
        provider_stats.cost += cost.total_cost;
        provider_stats.requests += 1;

        // Update daily usage
        self.daily_usage.tokens_used += tokens.total_tokens;
        self.daily_usage.cost += cost.total_cost;
        self.daily_usage.requests += 1;

        // Update monthly usage
        self.monthly_usage.tokens_used += tokens.total_tokens;
        self.monthly_usage.cost += cost.total_cost;
        self.monthly_usage.requests += 1;

        self.save_usage()?;
        Ok(())
    }

    
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UsageSummary {
    pub total_tokens: usize,
    pub total_cost: f64,
    pub total_requests: usize,
    pub daily_usage: UsageStats,
    pub monthly_usage: UsageStats,
    pub provider_usage: HashMap<String, UsageStats>,
    pub limits: CostLimits,
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::optimization::tokens::{TokenEstimate, CostEstimate};

    #[test]
    fn test_cost_tracking() -> Result<()> {
        let mut tracker = CostTracker::new(0.01)?;
        
        let tokens = TokenEstimate {
            input_tokens: 100,
            output_tokens: 50,
            total_tokens: 150,
        };
        
        let cost = CostEstimate {
            input_cost: 0.001,
            output_cost: 0.001,
            total_cost: 0.002,
            tokens: tokens.clone(),
        };
        
        tracker.track_usage("test_provider", &tokens, &cost)?;
        
        let usage = tracker.get_provider_usage("test_provider").unwrap();
        assert_eq!(usage.tokens_used, 150);
        assert_eq!(usage.cost, 0.002);
        assert_eq!(usage.requests, 1);
        
        Ok(())
    }

    #[test]
    fn test_cost_limits() -> Result<()> {
        let tracker = CostTracker::new(0.01);
        
        // Should proceed with small cost
        assert!(tracker.should_proceed(0.005, "test"));
        
        // Should not proceed with cost exceeding limit
        assert!(!tracker.should_proceed(0.015, "test"));
        
        Ok(())
    }
}