#!/usr/bin/env python3

"""
YAML Validation Module for IPCrawler

This module handles validation of parsed.yaml files using Pydantic schemas.
Ensures data consistency and catches structural issues early in the pipeline.
"""

import yaml
import sys
import os
from typing import Dict, Any, Optional
from pydantic import ValidationError

from ipcrawler.models import IPCrawlerReport
from ipcrawler.io import info, warn, error


def load_and_validate_report(path: str, exit_on_failure: bool = True) -> Optional[IPCrawlerReport]:
    """
    Load and validate a parsed.yaml file using Pydantic schema.
    
    Args:
        path: Path to the parsed.yaml file
        exit_on_failure: Whether to exit on validation failure (default True for CLI usage)
        
    Returns:
        IPCrawlerReport: Validated report object, or None if validation fails and exit_on_failure=False
        
    Raises:
        SystemExit: If validation fails and exit_on_failure=True
    """
    if not os.path.exists(path):
        error(f"[❌] Parsed YAML file not found: {path}")
        if exit_on_failure:
            sys.exit(1)
        return None
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        if data is None:
            error(f"[❌] Parsed YAML file is empty: {path}")
            if exit_on_failure:
                sys.exit(1)
            return None
            
    except yaml.YAMLError as e:
        error(f"[❌] Failed to parse YAML file {path}: {e}")
        if exit_on_failure:
            sys.exit(1)
        return None
    except Exception as e:
        error(f"[❌] Failed to read file {path}: {e}")
        if exit_on_failure:
            sys.exit(1)
        return None
    
    try:
        report = IPCrawlerReport(**data)
        info(f"[✅] Validation passed for {path}")
        return report
        
    except ValidationError as e:
        error(f"[❌] Parsed YAML validation failed for {path}:")
        
        # Format validation errors in a user-friendly way
        for error_detail in e.errors():
            field_path = " -> ".join(str(loc) for loc in error_detail['loc'])
            error_msg = error_detail['msg']
            error_type = error_detail['type']
            
            if field_path:
                error(f"  Field '{field_path}': {error_msg} (type: {error_type})")
            else:
                error(f"  {error_msg} (type: {error_type})")
                
            # Show the problematic value if available
            if 'input' in error_detail:
                error(f"    Received: {error_detail['input']}")
        
        if exit_on_failure:
            sys.exit(1)
        return None
    except Exception as e:
        error(f"[❌] Unexpected validation error for {path}: {e}")
        if exit_on_failure:
            sys.exit(1)
        return None


def validate_report_data(data: Dict[str, Any]) -> Optional[IPCrawlerReport]:
    """
    Validate report data dictionary without loading from file.
    
    Args:
        data: Dictionary containing report data
        
    Returns:
        IPCrawlerReport: Validated report object, or None if validation fails
    """
    try:
        return IPCrawlerReport(**data)
    except ValidationError as e:
        warn(f"[⚠️] Report data validation failed: {e}")
        return None
    except Exception as e:
        warn(f"[⚠️] Unexpected validation error: {e}")
        return None


def validate_parsed_yaml_structure(target: str) -> bool:
    """
    Quick validation check for parsed.yaml structure without full Pydantic validation.
    
    Args:
        target: Target name to check
        
    Returns:
        bool: True if basic structure is valid, False otherwise
    """
    yaml_path = f"results/{target}/parsed.yaml"
    
    if not os.path.exists(yaml_path):
        return False
    
    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        # Check for required top-level fields
        required_fields = ['target', 'date', 'ports', 'endpoints', 'errors']
        for field in required_fields:
            if field not in data:
                warn(f"[⚠️] Missing required field '{field}' in {yaml_path}")
                return False
        
        # Basic type checking
        if not isinstance(data['ports'], list):
            warn(f"[⚠️] Field 'ports' must be a list in {yaml_path}")
            return False
            
        if not isinstance(data['endpoints'], list):
            warn(f"[⚠️] Field 'endpoints' must be a list in {yaml_path}")
            return False
            
        if not isinstance(data['errors'], list):
            warn(f"[⚠️] Field 'errors' must be a list in {yaml_path}")
            return False
        
        return True
        
    except yaml.YAMLError as e:
        warn(f"[⚠️] YAML parsing error in {yaml_path}: {e}")
        return False
    except Exception as e:
        warn(f"[⚠️] Error checking structure of {yaml_path}: {e}")
        return False


if __name__ == "__main__":
    # Command-line interface for testing validation
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python validator.py <path_to_parsed.yaml>")
        sys.exit(1)
    
    yaml_path = sys.argv[1]
    report = load_and_validate_report(yaml_path)
    
    print(f"✅ Validation successful!")
    print(f"Target: {report.target}")
    print(f"Date: {report.date}")
    print(f"Ports found: {len(report.ports)}")
    print(f"Endpoints found: {len(report.endpoints)}")
    print(f"Errors: {len(report.errors)}")
    if report.cms:
        print(f"CMS detected: {report.cms.name} ({report.cms.confidence})")
    print(f"Summary: {report.summary.tools_run} tools run, {report.summary.errors} errors")