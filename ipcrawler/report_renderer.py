#!/usr/bin/env python3

"""
Jinja2-based Report Renderer for IPCrawler

This module provides Jinja2 template-based rendering for generating
clean, Glow-compatible Markdown reports from validated IPCrawlerReport objects.
"""

import os
from pathlib import Path
from typing import Optional
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from ipcrawler.models import IPCrawlerReport
from ipcrawler.io import info, warn, error


def render_markdown_report(report: IPCrawlerReport, output_dir: Optional[str] = None) -> bool:
    """
    Render a Markdown report using Jinja2 template from validated IPCrawlerReport object.
    
    Args:
        report: Validated IPCrawlerReport object from Pydantic
        output_dir: Optional output directory. If None, uses results/{target}/
        
    Returns:
        bool: True if report was successfully generated, False otherwise
    """
    try:
        # Determine output directory
        if output_dir is None:
            output_dir = f"results/{report.target}"
        
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        
        # Set up Jinja2 environment
        template_dir = Path(__file__).parent / "templates"
        env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=False,  # Markdown doesn't need HTML escaping
            trim_blocks=False,
            lstrip_blocks=False
        )
        
        # Load and render template
        try:
            template = env.get_template("markdown_report.j2")
        except TemplateNotFound:
            error(f"Template 'markdown_report.j2' not found in {template_dir}")
            return False
        
        # Render the report
        output = template.render(report=report)
        
        # Write to file
        output_path = out_dir / "report.md"
        output_path.write_text(output, encoding="utf-8")
        
        info(f"📋 Markdown report generated: {output_path}")
        return True
        
    except Exception as e:
        error(f"Failed to render markdown report for {report.target}: {e}")
        return False


def render_markdown_from_yaml(target: str, yaml_path: Optional[str] = None) -> bool:
    """
    Convenience function to render markdown report from parsed.yaml file.
    
    Args:
        target: Target name/address
        yaml_path: Optional path to parsed.yaml. If None, uses results/{target}/parsed.yaml
        
    Returns:
        bool: True if report was successfully generated, False otherwise
    """
    from ipcrawler.validator import load_and_validate_report
    
    try:
        # Determine YAML path
        if yaml_path is None:
            yaml_path = f"results/{target}/parsed.yaml"
        
        # Load and validate the report
        report = load_and_validate_report(yaml_path, exit_on_failure=False)
        
        if not report:
            warn(f"Failed to load or validate {yaml_path}")
            return False
        
        # Render the markdown report
        return render_markdown_report(report)
        
    except Exception as e:
        error(f"Failed to render markdown from YAML for {target}: {e}")
        return False


if __name__ == "__main__":
    # Command-line interface for testing
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python report_renderer.py <target>")
        print("Example: python report_renderer.py test-comprehensive")
        sys.exit(1)
    
    target = sys.argv[1]
    
    if render_markdown_from_yaml(target):
        print(f"✅ Markdown report generated for {target}")
        print(f"📄 View with: glow results/{target}/report.md")
    else:
        print(f"❌ Failed to generate markdown report for {target}")
        sys.exit(1)