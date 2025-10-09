use anyhow::{Context, Result};

#[derive(Debug, Clone)]
pub struct PortSpec {
    raw: String,
}

impl PortSpec {
    pub fn parse(spec: &str) -> Result<Self> {
        let spec = spec.trim();

        if spec.is_empty() {
            anyhow::bail!("Port specification cannot be empty");
        }

        // Validate the port specification
        for part in spec.split(',') {
            let part = part.trim();

            if part.contains('-') {
                // Range format: 80-443
                let range_parts: Vec<&str> = part.split('-').collect();
                if range_parts.len() != 2 {
                    anyhow::bail!(
                        "Invalid port range format: '{}'. Expected format: 'start-end'",
                        part
                    );
                }

                let start = range_parts[0].trim().parse::<u16>().with_context(|| {
                    format!(
                        "Invalid start port in range '{}': '{}'",
                        part, range_parts[0]
                    )
                })?;
                let end = range_parts[1].trim().parse::<u16>().with_context(|| {
                    format!("Invalid end port in range '{}': '{}'", part, range_parts[1])
                })?;

                if start > end {
                    anyhow::bail!(
                        "Invalid port range '{}': start port {} is greater than end port {}",
                        part,
                        start,
                        end
                    );
                }

                if start == 0 {
                    anyhow::bail!("Port 0 is not valid");
                }
            } else {
                // Single port: 80
                let port = part
                    .parse::<u16>()
                    .with_context(|| format!("Invalid port number: '{}'", part))?;

                if port == 0 {
                    anyhow::bail!("Port 0 is not valid");
                }
            }
        }

        Ok(Self {
            raw: spec.to_string(),
        })
    }

    /// Returns the port specification in its original format
    pub fn as_str(&self) -> &str {
        &self.raw
    }

    /// Returns the port specification formatted for nmap
    /// (same as original format)
    pub fn for_nmap(&self) -> String {
        self.raw.clone()
    }

    /// Returns the port specification formatted for naabu
    /// (same as original format)
    pub fn for_naabu(&self) -> String {
        self.raw.clone()
    }

    /// Returns the port specification formatted for rustscan
    /// (same as original format)
    pub fn for_rustscan(&self) -> String {
        self.raw.clone()
    }

    /// Expands ranges into individual ports (for tools that need it)
    pub fn expand(&self) -> Result<Vec<u16>> {
        let mut ports = Vec::new();

        for part in self.raw.split(',') {
            let part = part.trim();

            if part.contains('-') {
                let range_parts: Vec<&str> = part.split('-').collect();
                let start = range_parts[0].trim().parse::<u16>()?;
                let end = range_parts[1].trim().parse::<u16>()?;

                for port in start..=end {
                    if !ports.contains(&port) {
                        ports.push(port);
                    }
                }
            } else {
                let port = part.parse::<u16>()?;
                if !ports.contains(&port) {
                    ports.push(port);
                }
            }
        }

        ports.sort();
        Ok(ports)
    }

    /// Returns the number of unique ports in the specification
    pub fn count(&self) -> Result<usize> {
        Ok(self.expand()?.len())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_single_port() {
        let spec = PortSpec::parse("80").unwrap();
        assert_eq!(spec.as_str(), "80");
    }

    #[test]
    fn test_parse_multiple_ports() {
        let spec = PortSpec::parse("22,80,443").unwrap();
        assert_eq!(spec.as_str(), "22,80,443");
    }

    #[test]
    fn test_parse_range() {
        let spec = PortSpec::parse("1-1000").unwrap();
        assert_eq!(spec.as_str(), "1-1000");
    }

    #[test]
    fn test_parse_mixed() {
        let spec = PortSpec::parse("22,80,1000-2000,3000").unwrap();
        assert_eq!(spec.as_str(), "22,80,1000-2000,3000");
    }

    #[test]
    fn test_parse_with_spaces() {
        let spec = PortSpec::parse(" 22 , 80 , 100-200 ").unwrap();
        assert_eq!(spec.as_str(), "22 , 80 , 100-200");
    }

    #[test]
    fn test_invalid_empty() {
        assert!(PortSpec::parse("").is_err());
    }

    #[test]
    fn test_invalid_port_zero() {
        assert!(PortSpec::parse("0").is_err());
    }

    #[test]
    fn test_invalid_range_reversed() {
        assert!(PortSpec::parse("100-50").is_err());
    }

    #[test]
    fn test_invalid_port_number() {
        assert!(PortSpec::parse("abc").is_err());
    }

    #[test]
    fn test_expand_single() {
        let spec = PortSpec::parse("80").unwrap();
        let ports = spec.expand().unwrap();
        assert_eq!(ports, vec![80]);
    }

    #[test]
    fn test_expand_multiple() {
        let spec = PortSpec::parse("22,80,443").unwrap();
        let ports = spec.expand().unwrap();
        assert_eq!(ports, vec![22, 80, 443]);
    }

    #[test]
    fn test_expand_range() {
        let spec = PortSpec::parse("78-82").unwrap();
        let ports = spec.expand().unwrap();
        assert_eq!(ports, vec![78, 79, 80, 81, 82]);
    }

    #[test]
    fn test_expand_mixed() {
        let spec = PortSpec::parse("22,80-82,443").unwrap();
        let ports = spec.expand().unwrap();
        assert_eq!(ports, vec![22, 80, 81, 82, 443]);
    }

    #[test]
    fn test_count() {
        let spec = PortSpec::parse("22,80-82,443").unwrap();
        assert_eq!(spec.count().unwrap(), 5);
    }
}
