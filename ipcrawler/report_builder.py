#!/usr/bin/env python3

"""
Markdown Report Builder for IPCrawler

This module generates clean, glow-compatible Markdown reports from validated
IPCrawlerReport objects. Produces terminal-friendly output for easy viewing.
"""

import os
from typing import List, Optional
from datetime import datetime

from ipcrawler.models import IPCrawlerReport, Port, Endpoint, ErrorEntry


def build_markdown(report: IPCrawlerReport, output_path: str) -> None:
    """
    Generate a structured, Glow-friendly Markdown report from a validated IPCrawlerReport object.
    
    Args:
        report: Validated IPCrawlerReport object from Pydantic
        output_path: Path where to write the report.md file
    """
    # Build the markdown content
    markdown_content = _generate_markdown_content(report)
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Write the markdown file
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
    except Exception as e:
        raise RuntimeError(f"Failed to write markdown report to {output_path}: {e}")


def _generate_markdown_content(report: IPCrawlerReport) -> str:
    """Generate the complete markdown content for the report."""
    content_parts = []
    
    # Header and summary
    content_parts.append(_generate_header(report))
    content_parts.append(_generate_summary(report))
    
    # Main sections
    content_parts.append(_generate_ports_section(report.ports))
    content_parts.append(_generate_endpoints_section(report.endpoints))
    content_parts.append(_generate_cms_section(report.cms))
    content_parts.append(_generate_errors_section(report.errors))
    
    # Join all parts with double newlines for proper spacing
    return "\n\n".join(filter(None, content_parts)) + "\n"


def _generate_header(report: IPCrawlerReport) -> str:
    """Generate the report header with title and basic info."""
    return f"# 🎯 IPCrawler Report for {report.target}"


def _generate_summary(report: IPCrawlerReport) -> str:
    """Generate the summary section with key statistics."""
    summary_lines = [
        f"📅 **Date:** {report.date}",
        f"🔧 **Tools Run:** {report.summary.tools_run}",
        f"🔓 **Open Ports:** {report.summary.ports_open}",
        f"🧭 **Endpoints Found:** {report.summary.endpoints_found}",
        f"⚠️ **Errors:** {report.summary.errors}"
    ]
    
    if report.summary.cms_detected:
        summary_lines.append(f"🧠 **CMS Detected:** {report.summary.cms_detected}")
    else:
        summary_lines.append("🧠 **CMS Detected:** None")
    
    summary_content = "\n".join(summary_lines)
    return f"{summary_content}\n\n---"


def _generate_ports_section(ports: List[Port]) -> str:
    """Generate the open ports section with a table."""
    if not ports:
        return "## 🔓 Open Ports\n\n*No open ports discovered.*"
    
    # Build the table
    table_lines = [
        "## 🔓 Open Ports",
        "",
        "| Port | Service | Version |",
        "|------|---------|---------|"
    ]
    
    for port in ports:
        version = port.version if port.version else "*Not detected*"
        table_lines.append(f"| {port.port} | {port.service} | {version} |")
    
    return "\n".join(table_lines)


def _generate_endpoints_section(endpoints: List[Endpoint]) -> str:
    """Generate the discovered endpoints section with a list."""
    if not endpoints:
        return "## 🧭 Discovered Endpoints\n\n*No endpoints discovered.*"
    
    content_lines = ["## 🧭 Discovered Endpoints", ""]
    
    # Group endpoints by status code for better organization
    status_groups = {}
    for endpoint in endpoints:
        status = endpoint.status
        if status not in status_groups:
            status_groups[status] = []
        status_groups[status].append(endpoint)
    
    # Sort status codes (2xx, 3xx, 4xx, 5xx)
    for status in sorted(status_groups.keys()):
        endpoints_list = status_groups[status]
        
        # Add status group header if there are multiple status codes
        if len(status_groups) > 1:
            status_emoji = _get_status_emoji(status)
            content_lines.append(f"### {status_emoji} {status} Responses")
            content_lines.append("")
        
        for endpoint in endpoints_list:
            size_info = f" *({endpoint.size} bytes)*" if endpoint.size > 0 else ""
            notes_info = f" — *{endpoint.notes}*" if endpoint.notes else ""
            content_lines.append(f"- `{endpoint.path}`{size_info}{notes_info}")
        
        if len(status_groups) > 1:
            content_lines.append("")
    
    return "\n".join(content_lines).rstrip()


def _generate_cms_section(cms) -> Optional[str]:
    """Generate the CMS detection section."""
    if not cms:
        return None
    
    return f"## 🧠 Content Management System\n\n**{cms.name}** — *Confidence: {cms.confidence}*"


def _generate_errors_section(errors: List[ErrorEntry]) -> str:
    """Generate the errors section grouped by severity."""
    if not errors:
        return "## 🚨 Errors\n\n*No errors encountered during scanning.*"
    
    content_lines = ["## 🚨 Errors", ""]
    
    # Group errors by severity
    severity_groups = {"high": [], "medium": [], "low": []}
    for error in errors:
        if error.severity in severity_groups:
            severity_groups[error.severity].append(error)
    
    # Generate sections for each severity level that has errors
    for severity in ["high", "medium", "low"]:
        error_list = severity_groups[severity]
        if not error_list:
            continue
        
        severity_emoji = _get_severity_emoji(severity)
        content_lines.append(f"### {severity_emoji} {severity.title()} Severity")
        content_lines.append("")
        
        for error in error_list:
            # Format the error message
            error_line = f"- **{error.plugin}:** {error.message}"
            
            # Add additional context if available
            if error.exit_code is not None and error.exit_code != 0:
                error_line += f" *(Exit code: {error.exit_code})*"
            
            content_lines.append(error_line)
        
        content_lines.append("")
    
    return "\n".join(content_lines).rstrip()


def _get_status_emoji(status_code: int) -> str:
    """Get appropriate emoji for HTTP status code."""
    if 200 <= status_code < 300:
        return "✅"
    elif 300 <= status_code < 400:
        return "🔄"
    elif 400 <= status_code < 500:
        return "⚠️"
    elif 500 <= status_code < 600:
        return "❌"
    else:
        return "❓"


def _get_severity_emoji(severity: str) -> str:
    """Get appropriate emoji for error severity."""
    severity_emojis = {
        "high": "🔴",
        "medium": "🟡", 
        "low": "🟢"
    }
    return severity_emojis.get(severity, "❓")


def build_report_for_target(target: str) -> bool:
    """
    Convenience function to build a markdown report for a target.
    
    Args:
        target: Target name/address
        
    Returns:
        bool: True if report was successfully generated, False otherwise
    """
    from ipcrawler.validator import load_and_validate_report
    
    try:
        # Load and validate the parsed YAML
        parsed_yaml_path = f"results/{target}/parsed.yaml"
        report = load_and_validate_report(parsed_yaml_path, exit_on_failure=False)
        
        if not report:
            return False
        
        # Generate the markdown report
        output_path = f"results/{target}/report.md"
        build_markdown(report, output_path)
        
        return True
        
    except Exception:
        return False


if __name__ == "__main__":
    # Command-line interface for testing
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python report_builder.py <target>")
        print("Example: python report_builder.py test-comprehensive")
        sys.exit(1)
    
    target = sys.argv[1]
    
    if build_report_for_target(target):
        print(f"✅ Markdown report generated for {target}")
        print(f"📄 View with: glow results/{target}/report.md")
    else:
        print(f"❌ Failed to generate report for {target}")
        sys.exit(1)