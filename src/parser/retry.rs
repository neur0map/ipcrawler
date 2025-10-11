use anyhow::Result;
use regex::Regex;
use std::time::Duration;
use tokio::time::sleep;
use tracing::{info, warn};

pub struct RetryStrategy {
    max_retries: usize,
    base_delay_ms: u64,
    max_delay_ms: u64,
}

impl RetryStrategy {
    pub fn new(max_retries: usize) -> Self {
        Self {
            max_retries,
            base_delay_ms: 1000,
            max_delay_ms: 60000,
        }
    }

    pub async fn retry_with_backoff<F, Fut, T>(&self, mut operation: F) -> Result<T>
    where
        F: FnMut() -> Fut,
        Fut: std::future::Future<Output = Result<T>>,
    {
        let mut attempt = 0;

        loop {
            match operation().await {
                Ok(result) => return Ok(result),
                Err(e) => {
                    attempt += 1;

                    if attempt > self.max_retries {
                        return Err(e);
                    }

                    // Try to parse rate limit wait time from error
                    let wait_time = self.parse_rate_limit_wait(&e);

                    if let Some(wait_ms) = wait_time {
                        info!(
                            "Rate limit hit, waiting {}s before retry {}/{}",
                            wait_ms / 1000,
                            attempt,
                            self.max_retries
                        );
                        sleep(Duration::from_millis(wait_ms)).await;
                    } else {
                        // Exponential backoff
                        let delay = self.calculate_backoff(attempt);
                        warn!(
                            "Attempt {}/{} failed: {}. Retrying in {}s...",
                            attempt,
                            self.max_retries,
                            e,
                            delay.as_secs()
                        );
                        sleep(delay).await;
                    }
                }
            }
        }
    }

    fn parse_rate_limit_wait(&self, error: &anyhow::Error) -> Option<u64> {
        let error_str = error.to_string();

        // Try to parse "Please try again in 17.148s" or "Please try again in 1.5s"
        let re = Regex::new(r"try again in ([\d.]+)s").ok()?;
        if let Some(caps) = re.captures(&error_str) {
            if let Some(seconds_str) = caps.get(1) {
                if let Ok(seconds) = seconds_str.as_str().parse::<f64>() {
                    // Add a small buffer (200ms) to ensure we wait long enough
                    return Some(((seconds * 1000.0) + 200.0) as u64);
                }
            }
        }

        // Try to parse "try again in 626.999999ms"
        let re_ms = Regex::new(r"try again in ([\d.]+)ms").ok()?;
        if let Some(caps) = re_ms.captures(&error_str) {
            if let Some(ms_str) = caps.get(1) {
                if let Ok(ms) = ms_str.as_str().parse::<f64>() {
                    return Some((ms + 200.0) as u64);
                }
            }
        }

        None
    }

    fn calculate_backoff(&self, attempt: usize) -> Duration {
        let delay_ms = self.base_delay_ms * (2_u64.pow(attempt as u32 - 1));
        let delay_ms = delay_ms.min(self.max_delay_ms);
        Duration::from_millis(delay_ms)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_rate_limit_seconds() {
        let strategy = RetryStrategy::new(3);
        let error = anyhow::anyhow!("Rate limit reached. Please try again in 17.148s");

        let wait_time = strategy.parse_rate_limit_wait(&error);
        assert!(wait_time.is_some());
        let ms = wait_time.unwrap();
        assert!((17148..17500).contains(&ms)); // Should be ~17348 with buffer
    }

    #[test]
    fn test_parse_rate_limit_ms() {
        let strategy = RetryStrategy::new(3);
        let error = anyhow::anyhow!("try again in 626.999999ms");

        let wait_time = strategy.parse_rate_limit_wait(&error);
        assert!(wait_time.is_some());
        let ms = wait_time.unwrap();
        assert!((626..1000).contains(&ms));
    }

    #[test]
    fn test_backoff_calculation() {
        let strategy = RetryStrategy::new(5);

        assert_eq!(strategy.calculate_backoff(1), Duration::from_millis(1000));
        assert_eq!(strategy.calculate_backoff(2), Duration::from_millis(2000));
        assert_eq!(strategy.calculate_backoff(3), Duration::from_millis(4000));
        assert_eq!(strategy.calculate_backoff(4), Duration::from_millis(8000));
    }
}
