"""Enhanced Reporter for Mini Spider Analysis

Generates comprehensive reports from enhanced analysis results with multiple export formats.
"""

import json
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from jinja2 import Template

from .models import MiniSpiderResult, InterestingFinding, SeverityLevel
from utils.debug import debug_print


class EnhancedReporter:
    """Generate comprehensive reports from enhanced Mini Spider analysis"""
    
    def __init__(self):
        self.report_templates = self._load_report_templates()
    
    def generate_comprehensive_report(self, spider_result: MiniSpiderResult, 
                                    output_dir: Path, 
                                    formats: List[str] = None) -> Dict[str, str]:
        """Generate comprehensive reports in multiple formats"""
        if formats is None:
            formats = ['html', 'json', 'csv', 'txt']
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        generated_files = {}
        
        try:
            # Generate HTML report
            if 'html' in formats:
                html_file = self._generate_html_report(spider_result, output_dir)
                generated_files['html'] = str(html_file)
            
            # Generate JSON report
            if 'json' in formats:
                json_file = self._generate_json_report(spider_result, output_dir)
                generated_files['json'] = str(json_file)
            
            # Generate CSV report
            if 'csv' in formats:
                csv_file = self._generate_csv_report(spider_result, output_dir)
                generated_files['csv'] = str(csv_file)
            
            # Generate text report
            if 'txt' in formats:
                txt_file = self._generate_text_report(spider_result, output_dir)
                generated_files['txt'] = str(txt_file)
            
            debug_print(f"Generated {len(generated_files)} report files in {output_dir}")
            return generated_files
            
        except Exception as e:
            debug_print(f"Report generation failed: {str(e)}", level="ERROR")
            return {}
    
    def _generate_html_report(self, spider_result: MiniSpiderResult, output_dir: Path) -> Path:
        """Generate HTML report with interactive elements"""
        html_file = output_dir / f"mini_spider_report_{spider_result.target.replace(':', '_')}.html"
        
        # Prepare data for template
        report_data = self._prepare_report_data(spider_result)
        
        # Use template to generate HTML
        html_content = self.report_templates['html'].render(**report_data)
        
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return html_file
    
    def _generate_json_report(self, spider_result: MiniSpiderResult, output_dir: Path) -> Path:
        """Generate comprehensive JSON report"""
        json_file = output_dir / f"mini_spider_report_{spider_result.target.replace(':', '_')}.json"
        
        # Create comprehensive report structure
        report_data = {
            'metadata': {
                'target': spider_result.target,
                'scan_timestamp': spider_result.scan_timestamp.isoformat(),
                'execution_time': spider_result.execution_time,
                'workflow_version': spider_result.workflow_version,
                'report_generated': datetime.now().isoformat()
            },
            'summary': {
                'total_urls_discovered': len(spider_result.discovered_urls),
                'interesting_findings': len(spider_result.interesting_findings),
                'categories_found': list(spider_result.categorized_results.keys()),
                'tools_used': list(spider_result.tools_available.keys())
            },
            'findings': {
                'by_severity': self._group_findings_by_severity(spider_result.interesting_findings),
                'by_category': self._group_findings_by_category(spider_result.interesting_findings),
                'detailed_findings': [finding.model_dump() for finding in spider_result.interesting_findings]
            },
            'discovered_urls': {
                'by_category': {
                    category: [url.model_dump() for url in urls]
                    for category, urls in spider_result.categorized_results.items()
                },
                'all_urls': [url.model_dump() for url in spider_result.discovered_urls]
            },
            'statistics': spider_result.statistics.model_dump() if hasattr(spider_result.statistics, 'model_dump') else spider_result.statistics
        }
        
        # Add enhanced analysis if available
        if hasattr(spider_result, 'enhanced_analysis') and spider_result.enhanced_analysis:
            report_data['enhanced_analysis'] = spider_result.enhanced_analysis
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        return json_file
    
    def _generate_csv_report(self, spider_result: MiniSpiderResult, output_dir: Path) -> Path:
        """Generate CSV report for findings analysis"""
        csv_file = output_dir / f"mini_spider_findings_{spider_result.target.replace(':', '_')}.csv"
        
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow([
                'URL', 'Finding Type', 'Severity', 'Reason', 'Source', 
                'Confidence', 'Status Code', 'Content Type', 'Response Time'
            ])
            
            # Write findings
            for finding in spider_result.interesting_findings:
                # Find corresponding URL data
                url_data = next((url for url in spider_result.discovered_urls if url.url == finding.url), None)
                
                writer.writerow([
                    finding.url,
                    finding.finding_type,
                    finding.severity.value if hasattr(finding.severity, 'value') else str(finding.severity),
                    finding.reason,
                    finding.source.value if hasattr(finding.source, 'value') else str(finding.source),
                    finding.confidence,
                    url_data.status_code if url_data else '',
                    url_data.content_type if url_data else '',
                    url_data.response_time if url_data else ''
                ])
        
        return csv_file
    
    def _generate_text_report(self, spider_result: MiniSpiderResult, output_dir: Path) -> Path:
        """Generate human-readable text report"""
        txt_file = output_dir / f"mini_spider_summary_{spider_result.target.replace(':', '_')}.txt"
        
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write(f"MINI SPIDER ENHANCED ANALYSIS REPORT\n")
            f.write("="*80 + "\n\n")
            
            # Basic information
            f.write(f"Target: {spider_result.target}\n")
            f.write(f"Scan Time: {spider_result.scan_timestamp}\n")
            f.write(f"Execution Time: {spider_result.execution_time:.2f} seconds\n")
            f.write(f"URLs Discovered: {len(spider_result.discovered_urls)}\n")
            f.write(f"Interesting Findings: {len(spider_result.interesting_findings)}\n\n")
            
            # Critical findings
            critical_findings = [f for f in spider_result.interesting_findings if f.severity == SeverityLevel.CRITICAL]
            if critical_findings:
                f.write("CRITICAL FINDINGS:\n")
                f.write("-" * 40 + "\n")
                for finding in critical_findings:
                    f.write(f"🚨 {finding.finding_type.upper()}: {finding.url}\n")
                    f.write(f"   Reason: {finding.reason}\n")
                    f.write(f"   Confidence: {finding.confidence:.1%}\n\n")
            
            # High severity findings
            high_findings = [f for f in spider_result.interesting_findings if f.severity == SeverityLevel.HIGH]
            if high_findings:
                f.write("HIGH PRIORITY FINDINGS:\n")
                f.write("-" * 40 + "\n")
                for finding in high_findings:
                    f.write(f"⚠️  {finding.finding_type.upper()}: {finding.url}\n")
                    f.write(f"   Reason: {finding.reason}\n")
                    f.write(f"   Confidence: {finding.confidence:.1%}\n\n")
            
            # Enhanced analysis summary
            if hasattr(spider_result, 'enhanced_analysis') and spider_result.enhanced_analysis:
                enhanced = spider_result.enhanced_analysis
                
                f.write("ENHANCED ANALYSIS SUMMARY:\n")
                f.write("-" * 40 + "\n")
                
                # Security assessment
                if 'security_assessment' in enhanced:
                    security = enhanced['security_assessment']
                    f.write(f"Risk Score: {security.get('risk_score', 0)}/100\n")
                    f.write(f"Overall Exposure: {security.get('exposure_analysis', {}).get('overall_exposure', 'unknown').upper()}\n\n")
                
                # Technology profile
                if 'technology_profile' in enhanced:
                    tech = enhanced['technology_profile']
                    detected_techs = tech.get('detected_technologies', [])
                    if detected_techs:
                        f.write("Detected Technologies:\n")
                        for tech_info in detected_techs[:5]:  # Top 5
                            f.write(f"  - {tech_info['name']} ({tech_info['type']}) - {tech_info['confidence']:.1%} confidence\n")
                        f.write("\n")
                
                # Wordlist recommendations
                if 'wordlist_recommendations' in enhanced:
                    wordlists = enhanced['wordlist_recommendations'].get('priority_wordlists', [])
                    if wordlists:
                        f.write("TOP WORDLIST RECOMMENDATIONS:\n")
                        for i, rec in enumerate(wordlists[:5], 1):
                            f.write(f"  {i}. {rec['wordlist']} ({rec['priority']}) - Score: {rec['score']:.1f}\n")
                        f.write("\n")
            
            # URL categories
            f.write("DISCOVERED URL CATEGORIES:\n")
            f.write("-" * 40 + "\n")
            for category, urls in spider_result.categorized_results.items():
                f.write(f"{category.title()}: {len(urls)} URLs\n")
            f.write("\n")
            
            f.write("="*80 + "\n")
            f.write("Report generated by Enhanced Mini Spider Analyzer\n")
            f.write("="*80 + "\n")
        
        return txt_file
    
    def _prepare_report_data(self, spider_result: MiniSpiderResult) -> Dict[str, Any]:
        """Prepare data for report templates"""
        return {
            'target': spider_result.target,
            'scan_timestamp': spider_result.scan_timestamp,
            'execution_time': spider_result.execution_time,
            'total_urls': len(spider_result.discovered_urls),
            'total_findings': len(spider_result.interesting_findings),
            'critical_findings': [f for f in spider_result.interesting_findings if f.severity == SeverityLevel.CRITICAL],
            'high_findings': [f for f in spider_result.interesting_findings if f.severity == SeverityLevel.HIGH],
            'categorized_results': spider_result.categorized_results,
            'enhanced_analysis': getattr(spider_result, 'enhanced_analysis', {}),
            'report_generated': datetime.now(),
            'findings_by_severity': self._group_findings_by_severity(spider_result.interesting_findings)
        }
    
    def _group_findings_by_severity(self, findings: List[InterestingFinding]) -> Dict[str, List[InterestingFinding]]:
        """Group findings by severity level"""
        grouped = {}
        for finding in findings:
            severity = finding.severity.value if hasattr(finding.severity, 'value') else str(finding.severity)
            if severity not in grouped:
                grouped[severity] = []
            grouped[severity].append(finding)
        return grouped
    
    def _group_findings_by_category(self, findings: List[InterestingFinding]) -> Dict[str, List[InterestingFinding]]:
        """Group findings by finding type"""
        grouped = {}
        for finding in findings:
            if finding.finding_type not in grouped:
                grouped[finding.finding_type] = []
            grouped[finding.finding_type].append(finding)
        return grouped
    
    def _load_report_templates(self) -> Dict[str, Template]:
        """Load report templates"""
        # HTML template
        html_template = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mini Spider Analysis Report - {{ target }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { border-bottom: 3px solid #007acc; padding-bottom: 20px; margin-bottom: 30px; }
        .header h1 { color: #007acc; margin: 0; }
        .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .summary-card { background: #f8f9fa; padding: 15px; border-radius: 5px; border-left: 4px solid #007acc; }
        .summary-card h3 { margin: 0 0 10px 0; color: #333; }
        .summary-card .value { font-size: 24px; font-weight: bold; color: #007acc; }
        .severity-critical { background: #ffe6e6; border-left-color: #dc3545; }
        .severity-critical .value { color: #dc3545; }
        .severity-high { background: #fff3cd; border-left-color: #ffc107; }
        .severity-high .value { color: #856404; }
        .findings { margin-bottom: 30px; }
        .finding { background: #f8f9fa; margin: 10px 0; padding: 15px; border-radius: 5px; border-left: 4px solid #6c757d; }
        .finding.critical { border-left-color: #dc3545; background: #ffe6e6; }
        .finding.high { border-left-color: #ffc107; background: #fff3cd; }
        .finding-url { font-family: monospace; background: #e9ecef; padding: 5px; border-radius: 3px; word-break: break-all; }
        .tech-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; }
        .tech-item { background: #e7f3ff; padding: 10px; border-radius: 5px; }
        .wordlist-item { background: #f0f0f0; padding: 10px; margin: 5px 0; border-radius: 3px; }
        .priority-critical { background: #ffebee; border-left: 3px solid #f44336; }
        .priority-high { background: #fff3e0; border-left: 3px solid #ff9800; }
        .priority-medium { background: #f3e5f5; border-left: 3px solid #9c27b0; }
        .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #dee2e6; color: #6c757d; text-align: center; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🕷️ Mini Spider Analysis Report</h1>
            <p><strong>Target:</strong> {{ target }}</p>
            <p><strong>Scan Date:</strong> {{ scan_timestamp.strftime('%Y-%m-%d %H:%M:%S') }}</p>
            <p><strong>Execution Time:</strong> {{ "%.2f"|format(execution_time) }} seconds</p>
        </div>

        <div class="summary">
            <div class="summary-card">
                <h3>URLs Discovered</h3>
                <div class="value">{{ total_urls }}</div>
            </div>
            <div class="summary-card">
                <h3>Total Findings</h3>
                <div class="value">{{ total_findings }}</div>
            </div>
            <div class="summary-card severity-critical">
                <h3>Critical Findings</h3>
                <div class="value">{{ critical_findings|length }}</div>
            </div>
            <div class="summary-card severity-high">
                <h3>High Priority</h3>
                <div class="value">{{ high_findings|length }}</div>
            </div>
        </div>

        {% if critical_findings %}
        <div class="findings">
            <h2>🚨 Critical Findings</h2>
            {% for finding in critical_findings %}
            <div class="finding critical">
                <h4>{{ finding.finding_type.replace('_', ' ').title() }}</h4>
                <div class="finding-url">{{ finding.url }}</div>
                <p><strong>Reason:</strong> {{ finding.reason }}</p>
                <p><strong>Confidence:</strong> {{ "%.1f%%"|format(finding.confidence * 100) }}</p>
            </div>
            {% endfor %}
        </div>
        {% endif %}

        {% if high_findings %}
        <div class="findings">
            <h2>⚠️ High Priority Findings</h2>
            {% for finding in high_findings %}
            <div class="finding high">
                <h4>{{ finding.finding_type.replace('_', ' ').title() }}</h4>
                <div class="finding-url">{{ finding.url }}</div>
                <p><strong>Reason:</strong> {{ finding.reason }}</p>
                <p><strong>Confidence:</strong> {{ "%.1f%%"|format(finding.confidence * 100) }}</p>
            </div>
            {% endfor %}
        </div>
        {% endif %}

        {% if enhanced_analysis and enhanced_analysis.get('technology_profile') %}
        <div class="findings">
            <h2>🔧 Detected Technologies</h2>
            <div class="tech-grid">
                {% for tech in enhanced_analysis.technology_profile.get('detected_technologies', [])[:6] %}
                <div class="tech-item">
                    <strong>{{ tech.name }}</strong> ({{ tech.type }})<br>
                    Confidence: {{ "%.1f%%"|format(tech.confidence * 100) }}
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}

        {% if enhanced_analysis and enhanced_analysis.get('wordlist_recommendations') %}
        <div class="findings">
            <h2>📋 Recommended Wordlists</h2>
            {% for rec in enhanced_analysis.wordlist_recommendations.get('priority_wordlists', [])[:8] %}
            <div class="wordlist-item priority-{{ rec.priority.lower() }}">
                <strong>{{ rec.wordlist }}</strong> ({{ rec.priority }}) - Score: {{ "%.1f"|format(rec.score) }}<br>
                {% for reason in rec.get('reasons', [])[:2] %}
                <small>• {{ reason }}</small><br>
                {% endfor %}
            </div>
            {% endfor %}
        </div>
        {% endif %}

        <div class="footer">
            <p>Report generated on {{ report_generated.strftime('%Y-%m-%d %H:%M:%S') }} by Enhanced Mini Spider Analyzer</p>
        </div>
    </div>
</body>
</html>'''
        
        return {
            'html': Template(html_template)
        }