"""HTML format reporter for IPCrawler

Provides HTML output formatting with templates and styling.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from jinja2 import Template

from ..base.reporter import BaseReporter
from src.core.ui.themes.default import COLORS, ICONS


class HTMLReporter(BaseReporter):
    """HTML format reporter with responsive design"""
    
    def __init__(self, output_dir: Optional[Path] = None, theme: str = 'default'):
        """Initialize HTML reporter
        
        Args:
            output_dir: Directory to save reports  
            theme: Theme to use for styling
        """
        super().__init__(output_dir)
        self.theme = theme
        self.template = self._get_html_template()
    
    def generate(self, data: Dict[str, Any], **kwargs) -> Path:
        """Generate HTML report from data
        
        Args:
            data: Data to generate report from
            **kwargs: Additional options (filename, target, title)
            
        Returns:
            Path to generated HTML file
        """
        if not self.validate_data(data):
            raise ValueError("Invalid data provided for HTML report")
        
        # Prepare template data
        template_data = self._prepare_template_data(data, **kwargs)
        
        # Get filename
        filename = kwargs.get('filename')
        if not filename:
            target = kwargs.get('target', 'unknown')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_target = target.replace(':', '_').replace('/', '_')
            filename = f"report_{safe_target}_{timestamp}.html"
        
        if not filename.endswith('.html'):
            filename += '.html'
        
        output_path = self.get_output_path(filename)
        
        # Render template
        html_content = self.template.render(**template_data)
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return output_path
    
    def get_format(self) -> str:
        """Get the report format name"""
        return "html"
    
    def _prepare_template_data(self, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Prepare data for HTML template"""
        return {
            'title': kwargs.get('title', 'IPCrawler Report'),
            'target': kwargs.get('target', 'Unknown'),
            'timestamp': datetime.now(),
            'data': data,
            'metadata': self.metadata,
            'colors': COLORS,
            'icons': ICONS,
            'theme': self.theme
        }
    
    def _get_html_template(self) -> Template:
        """Get HTML template"""
        template_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} - {{ target }}</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Mono', monospace;
            background-color: {{ colors.background }};
            color: {{ colors.foreground }};
            line-height: 1.6;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: #0a0a0a;
            border: 1px solid {{ colors.primary }};
            border-radius: 8px;
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 100%);
            padding: 30px;
            border-bottom: 2px solid {{ colors.primary }};
            text-align: center;
        }
        
        .header h1 {
            color: {{ colors.primary }};
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 0 0 20px {{ colors.primary }};
        }
        
        .header .subtitle {
            color: {{ colors.secondary }};
            font-size: 1.2em;
            margin-bottom: 20px;
        }
        
        .header .meta {
            color: {{ colors.muted }};
            font-size: 0.9em;
        }
        
        .content {
            padding: 30px;
        }
        
        .section {
            margin-bottom: 40px;
            background: #0f0f0f;
            border: 1px solid #333;
            border-radius: 5px;
            overflow: hidden;
        }
        
        .section-header {
            background: #1a1a1a;
            padding: 15px 20px;
            border-bottom: 1px solid #333;
            font-size: 1.3em;
            font-weight: bold;
            color: {{ colors.primary }};
        }
        
        .section-content {
            padding: 20px;
        }
        
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .summary-card {
            background: #1a1a1a;
            border: 1px solid #333;
            border-radius: 5px;
            padding: 20px;
            text-align: center;
        }
        
        .summary-card .value {
            font-size: 2em;
            font-weight: bold;
            color: {{ colors.primary }};
            margin-bottom: 10px;
        }
        
        .summary-card .label {
            color: {{ colors.muted }};
            text-transform: uppercase;
            font-size: 0.8em;
            letter-spacing: 1px;
        }
        
        .data-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        
        .data-table th,
        .data-table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #333;
        }
        
        .data-table th {
            background: #1a1a1a;
            color: {{ colors.primary }};
            font-weight: bold;
            text-transform: uppercase;
            font-size: 0.8em;
            letter-spacing: 1px;
        }
        
        .data-table tr:hover {
            background: #0f0f0f;
        }
        
        .severity-critical { color: #ff4444; }
        .severity-high { color: #ff8800; }
        .severity-medium { color: #ffaa00; }
        .severity-low { color: #00aaff; }
        .severity-info { color: #888888; }
        
        .status-success { color: {{ colors.success }}; }
        .status-error { color: {{ colors.error }}; }
        .status-warning { color: {{ colors.warning }}; }
        .status-info { color: {{ colors.info }}; }
        
        .code {
            background: #0a0a0a;
            border: 1px solid #333;
            border-radius: 3px;
            padding: 2px 6px;
            font-family: inherit;
            color: {{ colors.info }};
        }
        
        .footer {
            background: #1a1a1a;
            padding: 20px;
            text-align: center;
            border-top: 1px solid #333;
            color: {{ colors.muted }};
            font-size: 0.9em;
        }
        
        @media (max-width: 768px) {
            .summary-grid {
                grid-template-columns: 1fr;
            }
            
            .container {
                margin: 10px;
            }
            
            body {
                padding: 10px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{{ icons.search }} {{ title }}</h1>
            <div class="subtitle">Target: {{ target }}</div>
            <div class="meta">
                Generated: {{ timestamp.strftime('%Y-%m-%d %H:%M:%S') }} | 
                IPCrawler v{{ metadata.version }}
            </div>
        </div>
        
        <div class="content">
            <!-- Dynamic content will be inserted here based on data structure -->
            {% if data %}
                <div class="section">
                    <div class="section-header">{{ icons.info }} Report Data</div>
                    <div class="section-content">
                        <pre style="color: {{ colors.muted }}; white-space: pre-wrap;">{{ data | tojson(indent=2) }}</pre>
                    </div>
                </div>
            {% endif %}
        </div>
        
        <div class="footer">
            <p>{{ icons.shield }} Generated by IPCrawler - Advanced Network Discovery & Security Assessment Tool</p>
        </div>
    </div>
</body>
</html>'''
        
        return Template(template_content)