#!/usr/bin/env python3

import os
import re
import yaml
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


def parse_nmap_ports(nmap_log_path: str) -> List[Dict[str, Any]]:
    """Parse nmap.log for port information."""
    ports = []
    
    if not os.path.exists(nmap_log_path):
        return ports
    
    try:
        with open(nmap_log_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Look for port lines in nmap output
        # Format: "80/tcp  open  http     syn-ack nginx"
        port_pattern = r'^(\d+)/tcp\s+(\w+)\s+(\S+)(?:\s+\S+)?\s*(.*?)$'
        
        for line in content.split('\n'):
            line = line.strip()
            match = re.match(port_pattern, line)
            if match:
                port_num = int(match.group(1))
                state = match.group(2)
                service = match.group(3)
                version_info = match.group(4).strip() if match.group(4) else ""
                
                # Only include open ports
                if state == "open":
                    ports.append({
                        "port": port_num,
                        "service": service,
                        "version": version_info
                    })
    
    except Exception as e:
        logger.warning(f"Error parsing nmap log {nmap_log_path}: {e}")
    
    return ports


def parse_directory_busting_logs(scans_dir: str) -> List[Dict[str, Any]]:
    """Parse directory busting logs (feroxbuster, gobuster, etc.) for endpoints."""
    endpoints = []
    seen_paths = set()
    
    # Common directory busting log file patterns
    bust_patterns = ["feroxbuster.log", "gobuster.log", "dirb.log", "dirsearch.log"]
    
    for pattern in bust_patterns:
        log_path = os.path.join(scans_dir, pattern)
        if os.path.exists(log_path):
            try:
                with open(log_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Common patterns for directory busting output
                # feroxbuster: "200 GET 1234l   5678w   9012c http://example.com/path"
                # gobuster: "/.git (Status: 200) [Size: 1234]"
                
                # Try feroxbuster pattern first
                ferox_pattern = r'(\d+)\s+\w+\s+\d+l\s+\d+w\s+(\d+)c\s+\S+://[^/]+(/\S*)'
                for line in content.split('\n'):
                    match = re.search(ferox_pattern, line)
                    if match:
                        status = int(match.group(1))
                        size = int(match.group(2))
                        path = match.group(3)
                        
                        if path not in seen_paths:
                            seen_paths.add(path)
                            endpoints.append({
                                "path": path,
                                "status": status,
                                "size": size
                            })
                
                # Try gobuster pattern
                gobuster_pattern = r'(\S+)\s+\(Status:\s+(\d+)\)\s+\[Size:\s+(\d+)\]'
                for line in content.split('\n'):
                    match = re.search(gobuster_pattern, line)
                    if match:
                        path = match.group(1)
                        status = int(match.group(2))
                        size = int(match.group(3))
                        
                        if path not in seen_paths:
                            seen_paths.add(path)
                            endpoints.append({
                                "path": path,
                                "status": status,
                                "size": size
                            })
                            
            except Exception as e:
                logger.warning(f"Error parsing directory busting log {log_path}: {e}")
    
    return endpoints


def parse_cms_detection(scans_dir: str) -> Optional[Dict[str, Any]]:
    """Parse whatweb.log and similar for CMS detection."""
    cms_logs = ["whatweb.log", "wappalyzer.log", "cms.log"]
    
    for log_name in cms_logs:
        log_path = os.path.join(scans_dir, log_name)
        if os.path.exists(log_path):
            try:
                with open(log_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Look for CMS patterns
                # WordPress[4.9.8], Drupal[8.5.3], etc.
                cms_pattern = r'(WordPress|Drupal|Joomla|Magento|Shopify|Wix|Squarespace)\[([^\]]+)\]'
                match = re.search(cms_pattern, content, re.IGNORECASE)
                
                if match:
                    return {
                        "name": match.group(1),
                        "confidence": match.group(2)
                    }
                
                # Look for general CMS indicators without version
                simple_pattern = r'\b(WordPress|Drupal|Joomla|Magento|Shopify|Wix|Squarespace)\b'
                match = re.search(simple_pattern, content, re.IGNORECASE)
                
                if match:
                    return {
                        "name": match.group(1),
                        "confidence": "detected"
                    }
                    
            except Exception as e:
                logger.warning(f"Error parsing CMS log {log_path}: {e}")
    
    return None


def parse_errors_log(errors_log_path: str) -> List[Dict[str, Any]]:
    """Parse the YAML-formatted errors.log."""
    if not os.path.exists(errors_log_path):
        return []
    
    try:
        with open(errors_log_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        if not content:
            return []
        
        # Load YAML content
        errors = yaml.safe_load(content)
        
        # Ensure it's a list
        if isinstance(errors, list):
            return errors
        elif errors is not None:
            return [errors]
        else:
            return []
            
    except Exception as e:
        logger.warning(f"Error parsing errors log {errors_log_path}: {e}")
        return []


def build_parsed_yaml(target: str) -> None:
    """
    Read all log files in results/{target}/scans/ and consolidate 
    key data into a clean results/{target}/parsed.yaml.
    """
    # Determine paths
    target_dir = f"results/{target}"
    scans_dir = os.path.join(target_dir, "scans")
    output_path = os.path.join(target_dir, "parsed.yaml")
    
    # Ensure scans directory exists
    if not os.path.exists(scans_dir):
        logger.warning(f"Scans directory not found: {scans_dir}")
        return
    
    # Parse each section
    nmap_log_path = os.path.join(scans_dir, "nmap.log")
    errors_log_path = os.path.join(scans_dir, "errors.log")
    
    ports = parse_nmap_ports(nmap_log_path)
    endpoints = parse_directory_busting_logs(scans_dir)
    cms = parse_cms_detection(scans_dir)
    errors = parse_errors_log(errors_log_path)
    
    # Build the parsed data structure
    parsed_data = {
        "target": target,
        "date": date.today().strftime("%Y-%m-%d"),
        "ports": ports,
        "endpoints": endpoints,
        "cms": cms,
        "errors": errors
    }
    
    # Ensure target directory exists
    os.makedirs(target_dir, exist_ok=True)
    
    # Write to parsed.yaml using pyyaml.safe_dump()
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(parsed_data, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"Parsed data written to {output_path}")
        
    except Exception as e:
        logger.error(f"Error writing parsed.yaml to {output_path}: {e}")
        raise


if __name__ == "__main__":
    # For testing
    import sys
    if len(sys.argv) > 1:
        target = sys.argv[1]
        build_parsed_yaml(target)
    else:
        print("Usage: python parse_logs.py <target>")