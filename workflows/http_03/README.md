# HTTP Advanced Discovery Workflow (http_03)

Advanced HTTP/HTTPS scanner with multiple discovery techniques that doesn't require wordlists.

## Features

### 1. DNS Enumeration
- Multiple DNS record types (A, AAAA, CNAME, MX, NS, TXT, SOA)
- Zone transfer attempts
- Common subdomain pattern detection (no wordlist required)
- Parallel subdomain verification

### 2. HTTP Service Discovery
- Automatic HTTP/HTTPS detection
- Port scanning for common web services
- Service fingerprinting
- Response analysis

### 3. Path Discovery (No Wordlists)
- HTML parsing for links and resources
- Common application patterns
- Technology-specific paths
- API endpoint discovery
- Configuration file detection

### 4. Vulnerability Detection
- Missing security headers
- Information disclosure
- CORS misconfigurations
- SSL/TLS weaknesses
- Weak cipher suites
- Cross-service analysis

### 5. Technology Detection
- Server fingerprinting
- Framework detection
- CMS identification
- JavaScript framework detection

## Dependencies

### Python Libraries (Optional)
```bash
pip install httpx dnspython
```

If these are not installed, the scanner will automatically fall back to using curl and system tools.

### Fallback Mode
When Python dependencies are not available, the scanner uses:
- `curl` for HTTP requests
- `nslookup` for DNS queries
- System SSL tools for certificate analysis

## Usage

The http_03 workflow is automatically triggered after nmap scanning when HTTP/HTTPS services are detected.

### Detected Ports
The scanner looks for services on these common ports:
- 80, 443 (standard HTTP/HTTPS)
- 8080, 8443 (alternative HTTP/HTTPS)
- 8000, 8888, 3000, 5000, 9000 (common development ports)

### Output

Results are saved as `http_scan_results.json` in the workspace directory with:
- Discovered services
- Vulnerabilities by severity
- DNS records and subdomains
- Discovered paths
- Detected technologies

## Vulnerability Severity Levels

- **Critical**: Immediate security risks (e.g., exposed sensitive files)
- **High**: Serious misconfigurations (e.g., CORS wildcard, weak SSL)
- **Medium**: Missing security headers
- **Low**: Information disclosure

## Example Output

```json
{
  "target": "example.com",
  "services": [
    {
      "port": 443,
      "scheme": "https",
      "url": "https://example.com:443",
      "server": "nginx/1.18.0",
      "technologies": ["nginx", "PHP"],
      "discovered_paths": ["/api/", "/login", "/robots.txt"]
    }
  ],
  "vulnerabilities": [
    {
      "type": "missing-x-frame-options",
      "severity": "medium",
      "description": "Missing Clickjacking protection header"
    }
  ],
  "dns_records": [
    {"type": "A", "value": "93.184.216.34"}
  ],
  "subdomains": ["www.example.com", "mail.example.com"]
}
```