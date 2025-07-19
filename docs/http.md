# HTTP Advanced Discovery Workflow (http_03)

Advanced HTTP/HTTPS scanner with comprehensive hostname discovery and virtual host detection that eliminates the need for manual /etc/hosts entries.

## Enhanced Features

### 🔍 **Comprehensive Hostname Testing**
- Tests **ALL hostname combinations** for each port
- Discovers virtual hosts automatically
- **No manual /etc/hosts modifications required**
- Eliminates need for double scanning

### 🌐 **Dynamic Hostname Discovery**
- DNS enumeration with intelligent subdomain patterns
- Hostname extraction from HTTP responses (redirects, links)
- Automatic generation of common subdomain patterns
- Cross-references hostnames across all discovered services

### 🎯 **Unique Service Detection**
- Identifies different services on same port with different hostnames
- Compares content, headers, and response characteristics
- Prevents duplicate entries while capturing all variations

## Core Features

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
- **Virtual host detection across all hostnames**

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

## How It Solves the Double-Scan Problem

**Before (Required Two Scans):**
1. First scan: Discovers basic services via IP
2. Manual /etc/hosts entry addition
3. Second scan: Discovers hostname-specific services

**Now (Single Comprehensive Scan):**
1. Discovers services via IP **AND** all possible hostnames
2. Automatically extracts hostnames from responses
3. Tests all hostname combinations systematically
4. Captures all virtual hosts in one pass

## Example Hostname Discovery

```bash
[DEBUG] HTTP scanner execute - ports: [80, 443], testing 15 hostnames: 
['192.168.1.100', 'example.com', 'www.example.com', 'api.example.com', 
 'admin.example.com', 'portal.example.com', 'secure.example.com', ...]

[DEBUG] Found unique service: https://192.168.1.100:443 (hostname: 192.168.1.100)
[DEBUG] Found unique service: https://192.168.1.100:443 (hostname: portal.example.com)
[DEBUG] Discovered additional hostnames: ['app.example.com', 'secure.example.com']
[DEBUG] Found service via discovered hostname: https://192.168.1.100:443 (hostname: app.example.com)
```

## Dependencies

### Python Libraries (Optional)
```bash
pip install httpx dnspython
```

If these are not installed, the scanner will automatically fall back to using curl and system tools with the same comprehensive hostname testing.

### Fallback Mode
When Python dependencies are not available, the scanner uses:
- `curl` for HTTP requests with proper Host headers
- `nslookup` for DNS queries
- Comprehensive hostname testing via curl
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
- **All discovered services (including virtual hosts)**
- **Hostname used for each service discovery**
- Vulnerabilities by severity
- DNS records and subdomains
- Discovered paths
- Detected technologies
- **List of all tested hostnames**

## Enhanced Output Example

```json
{
  "target": "192.168.1.100",
  "tested_hostnames": [
    "192.168.1.100", "example.com", "www.example.com", 
    "api.example.com", "portal.example.com"
  ],
  "services": [
    {
      "port": 443,
      "scheme": "https",
      "url": "https://192.168.1.100:443",
      "actual_target": "192.168.1.100",
      "server": "nginx/1.18.0",
      "technologies": ["nginx"]
    },
    {
      "port": 443,
      "scheme": "https", 
      "url": "https://192.168.1.100:443",
      "actual_target": "portal.example.com",
      "server": "nginx/1.18.0",
      "technologies": ["nginx", "WordPress"],
      "discovered_paths": ["/wp-admin/", "/api/"]
    }
  ],
  "summary": {
    "total_services": 2,
    "virtual_hosts_detected": true
  }
}
```

## Benefits

✅ **Single scan** discovers all services (no double scanning)  
✅ **No manual /etc/hosts** modifications required  
✅ **Automatic virtual host** detection  
✅ **Comprehensive hostname** testing  
✅ **Dynamic discovery** of new hostnames from responses  
✅ **Fallback mode** works identically when dependencies unavailable  

## Vulnerability Severity Levels

- **Critical**: Immediate security risks (e.g., exposed sensitive files)
- **High**: Serious misconfigurations (e.g., CORS wildcard, weak SSL)
- **Medium**: Missing security headers
- **Low**: Information disclosure