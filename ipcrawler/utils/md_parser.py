#!/usr/bin/env python3
"""
Advanced markdown parser for ipcrawler scan results.
"""
import re
import sys
import json
import os
from pathlib import Path

def parse_scan_results(content):
    """Parse scan results from markdown content."""
    # Split content by scan result headers
    sections = re.split(r'^## (\w+) Scan Result', content, flags=re.MULTILINE)
    
    results = []
    # Skip the first element (content before first header)
    for i in range(1, len(sections), 2):
        if i + 1 >= len(sections):
            break
            
        tool_name = sections[i].lower()
        section_content = sections[i + 1]
        
        # Extract metadata
        timestamp_match = re.search(r'\*\*Timestamp:\*\* ([^\n]+)', section_content)
        exit_code_match = re.search(r'\*\*Exit Code:\*\* (\d+)', section_content)
        duration_match = re.search(r'\*\*Duration:\*\* ([^\n]+)', section_content)
        status_match = re.search(r'\*\*Status:\*\* ([^\n]+)', section_content)
        command_match = re.search(r'\*\*Command:\*\* `([^`]+)`', section_content)
        
        # Extract content metadata
        page_title_match = re.search(r'📄 Page Title: ([^\n]+)', section_content)
        description_match = re.search(r'📝 Description: ([^\n]+)', section_content)
        technology_match = re.search(r'⚙️ Technology: ([^\n]+)', section_content)
        content_size_match = re.search(r'📏 Content Size: ([^\n]+)', section_content)
        result_type_match = re.search(r'🚫 Result: ([^\n]+)', section_content)
        
        # Extract content line counts
        html_lines_match = re.search(r'\[Complete HTML content \((\d+) lines\):\]', section_content)
        cert_lines_match = re.search(r'\[Complete certificate details \((\d+) lines\):\]', section_content)
        output_lines_match = re.search(r'\[Complete output content \((\d+) lines\):\]', section_content)
        
        scan_result = {
            'tool': tool_name,
            'timestamp': timestamp_match.group(1).strip() if timestamp_match else '',
            'exit_code': int(exit_code_match.group(1)) if exit_code_match else -1,
            'duration': duration_match.group(1).strip() if duration_match else '',
            'status': status_match.group(1).strip() if status_match else '',
            'command': command_match.group(1) if command_match else '',
            'metadata': {
                'page_title': page_title_match.group(1) if page_title_match else '',
                'description': description_match.group(1) if description_match else '',
                'technology': technology_match.group(1) if technology_match else '',
                'content_size': content_size_match.group(1) if content_size_match else '',
                'result_type': result_type_match.group(1) if result_type_match else ''
            },
            'content_info': {
                'html_lines': int(html_lines_match.group(1)) if html_lines_match else 0,
                'cert_lines': int(cert_lines_match.group(1)) if cert_lines_match else 0,
                'output_lines': int(output_lines_match.group(1)) if output_lines_match else 0
            }
        }
        results.append(scan_result)
    
    # Create summary
    summary = {
        'total_scans': len(results),
        'successful_scans': len([r for r in results if r['exit_code'] == 0]),
        'failed_scans': len([r for r in results if r['exit_code'] != 0]),
        'tools_used': list(set([r['tool'] for r in results])),
        'scans': results
    }
    
    return summary

def main():
    """Main function."""
    if len(sys.argv) > 1:
        # Read from file
        file_path = sys.argv[1]
        if os.path.exists(file_path):
            content = Path(file_path).read_text()
        else:
            print(f"Error: File {file_path} does not exist", file=sys.stderr)
            sys.exit(1)
    else:
        # Read from stdin
        content = sys.stdin.read()
    
    try:
        result = parse_scan_results(content)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error parsing content: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()