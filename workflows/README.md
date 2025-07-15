# IPCrawler Workflows

## Workflow Execution Order

Workflows are executed in sequential order based on their naming convention: `tool_XX` where XX determines the execution order.

### Current Workflow Order:

1. **nmap_fast_01** - Fast port discovery
   - Quickly identifies open ports (SYN scan if privileged, TCP connect if not)
   - Execution time: ~10-60 seconds
   - Output: List of open port numbers

2. **nmap_02** - Detailed vulnerability scanning  
   - Performs service detection and vulnerability scanning
   - Uses discovered ports from _01 or scans all ports if discovery is disabled
   - Execution time: Variable based on number of ports
   - Output: Detailed host, service, and vulnerability information

3. **http_03** - Advanced HTTP/HTTPS discovery
   - Automatically triggered when HTTP/HTTPS services are detected
   - Performs DNS enumeration, path discovery, header analysis, and vulnerability detection
   - No wordlists required - uses intelligent discovery techniques
   - Execution time: Typically 10-30 seconds
   - Output: HTTP-specific vulnerabilities and discovered paths/subdomains

## Adding New Workflows

To add a new workflow:

1. Create a new directory: `/workflows/tool_XX/`
2. The XX number determines execution order (e.g., _04 would run after _03)
3. Implement scanner inheriting from `BaseWorkflow`
4. Import and integrate in `ipcrawler.py`

## Workflow Dependencies

- Each workflow can use results from previous workflows
- The _03 workflow uses port information from _02 to identify HTTP services
- Results are passed through the scanning pipeline automatically