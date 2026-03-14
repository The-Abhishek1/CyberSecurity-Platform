
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json
import os
import uuid
import logging
from enum import Enum

try:
    import pdfkit
    PDFKIT_AVAILABLE = True
except ImportError:
    PDFKIT_AVAILABLE = False
    logging.warning("pdfkit not installed. PDF generation will be mocked.")

try:
    import markdown
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False

import jinja2

logger = logging.getLogger(__name__)


class ReportFormat(str, Enum):
    PDF = "pdf"
    HTML = "html"
    JSON = "json"
    CSV = "csv"
    MARKDOWN = "markdown"
    TEXT = "text"


class ReportEngine:
    """Enterprise Report Engine"""
    
    def __init__(self, scheduler=None):
        self.scheduler = scheduler
        
        # Template engine
        self.template_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader("src/reporting/templates"),
            autoescape=True
        )
        
        # Report cache
        self.report_cache = {}
        
        logger.info("Report Engine initialized")
    
    async def generate_report(self,
                              report_type: str,
                              data: Dict,
                              format: ReportFormat = ReportFormat.PDF,
                              template: Optional[str] = None,
                              branding: Optional[Dict] = None) -> Dict:
        """Generate report"""
        
        report_id = f"rpt_{uuid.uuid4().hex[:12]}"
        
        # Get template
        if template:
            template_content = await self._load_template(template)
        else:
            template_content = await self._get_default_template(report_type)
        
        # Prepare context
        context = {
            "report_id": report_id,
            "generated_at": datetime.utcnow().isoformat(),
            "data": data,
            "branding": branding or self._default_branding()
        }
        
        # Render template
        rendered = await self._render_template(template_content, context)
        
        # Convert to requested format
        output = await self._convert_format(rendered, format, context)
        
        report = {
            "report_id": report_id,
            "type": report_type,
            "format": format.value,
            "generated_at": context["generated_at"],
            "size_bytes": len(output) if isinstance(output, str) else len(str(output)),
            "content": output,
            "metadata": {
                "template": template,
                "data_sources": list(data.keys())
            }
        }
        
        # Cache report
        self.report_cache[report_id] = report
        
        logger.info(f"Generated report {report_id} in {format.value} format")
        
        return report
    
    async def _load_template(self, template_name: str) -> str:
        """Load template file"""
        
        # Check if file exists
        template_path = os.path.join("src/reporting/templates", template_name)
        if os.path.exists(template_path):
            with open(template_path, 'r') as f:
                return f.read()
        
        # Return default template
        return self._get_default_html_template()
    
    async def _get_default_template(self, report_type: str) -> str:
        """Get default template for report type"""
        
        templates = {
            "executive_summary": self._get_executive_template(),
            "vulnerability_report": self._get_vulnerability_template(),
            "compliance_report": self._get_compliance_template(),
            "audit_report": self._get_audit_template()
        }
        
        return templates.get(report_type, self._get_default_html_template())
    
    def _get_default_html_template(self) -> str:
        return """<!DOCTYPE html>
<html>
<head>
    <title>{{ data.title|default('Report') }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        h1 { color: {{ branding.primary_color }}; }
        .header { border-bottom: 2px solid #ccc; margin-bottom: 20px; }
        .footer { margin-top: 40px; font-size: 0.8em; color: #666; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: {{ branding.secondary_color }}; }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ branding.company_name }}</h1>
        <h2>{{ data.title|default('Report') }}</h2>
        <p>Generated: {{ generated_at }}</p>
    </div>
    
    <div class="content">
        {{ data.content|default('No content provided') }}
    </div>
    
    <div class="footer">
        <p>Report ID: {{ report_id }}</p>
    </div>
</body>
</html>"""
    
    def _get_executive_template(self) -> str:
        return """<!DOCTYPE html>
<html>
<head>
    <title>Executive Summary - {{ generated_at }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        h1 { color: #1a73e8; }
        .summary-box { background: #f5f5f5; padding: 20px; border-radius: 5px; margin: 20px 0; }
        .metric { display: inline-block; width: 200px; margin: 10px; padding: 15px; background: white; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        .metric-value { font-size: 24px; font-weight: bold; color: #1a73e8; }
        .metric-label { font-size: 14px; color: #666; }
    </style>
</head>
<body>
    <h1>Executive Security Summary</h1>
    <p>Generated: {{ generated_at }}</p>
    
    <div class="summary-box">
        <h2>Overall Security Posture</h2>
        <div class="metric">
            <div class="metric-value">{{ data.risk_score|default('N/A') }}</div>
            <div class="metric-label">Risk Score</div>
        </div>
        <div class="metric">
            <div class="metric-value">{{ data.vulnerabilities|default(0) }}</div>
            <div class="metric-label">Vulnerabilities</div>
        </div>
        <div class="metric">
            <div class="metric-value">{{ data.scans_completed|default(0) }}</div>
            <div class="metric-label">Scans Completed</div>
        </div>
    </div>
    
    <h2>Key Findings</h2>
    <table>
        <tr>
            <th>Severity</th>
            <th>Count</th>
            <th>Trend</th>
        </tr>
        {% for severity, count in data.findings_by_severity|default({}).items() %}
        <tr>
            <td>{{ severity }}</td>
            <td>{{ count }}</td>
            <td>{{ data.trends.get(severity, 'stable') }}</td>
        </tr>
        {% endfor %}
    </table>
    
    <h2>Recommendations</h2>
    <ul>
    {% for rec in data.recommendations|default([]) %}
        <li>{{ rec }}</li>
    {% endfor %}
    </ul>
</body>
</html>"""
    
    def _get_vulnerability_template(self) -> str:
        return """<!DOCTYPE html>
<html>
<head>
    <title>Vulnerability Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .critical { color: #d32f2f; }
        .high { color: #f57c00; }
        .medium { color: #fbc02d; }
        .low { color: #388e3c; }
        .vuln-item { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
    </style>
</head>
<body>
    <h1>Vulnerability Report</h1>
    <p>Generated: {{ generated_at }}</p>
    <p>Target: {{ data.target|default('All assets') }}</p>
    
    <h2>Summary</h2>
    <p>Total Vulnerabilities: {{ data.vulnerabilities|length }}</p>
    <p>Critical: {{ data.critical_count|default(0) }}</p>
    <p>High: {{ data.high_count|default(0) }}</p>
    <p>Medium: {{ data.medium_count|default(0) }}</p>
    <p>Low: {{ data.low_count|default(0) }}</p>
    
    <h2>Details</h2>
    {% for vuln in data.vulnerabilities|default([]) %}
    <div class="vuln-item {{ vuln.severity|lower }}">
        <h3 class="{{ vuln.severity|lower }}">{{ vuln.title }}</h3>
        <p><strong>Severity:</strong> {{ vuln.severity }}</p>
        <p><strong>CVSS:</strong> {{ vuln.cvss_score|default('N/A') }}</p>
        <p><strong>Description:</strong> {{ vuln.description }}</p>
        <p><strong>Remediation:</strong> {{ vuln.remediation }}</p>
    </div>
    {% endfor %}
</body>
</html>"""
    
    def _get_compliance_template(self) -> str:
        return """<!DOCTYPE html>
<html>
<head>
    <title>Compliance Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .compliant { color: #4caf50; }
        .non-compliant { color: #f44336; }
        .partial { color: #ff9800; }
        .control { margin: 15px 0; padding: 10px; border-left: 4px solid #ddd; }
    </style>
</head>
<body>
    <h1>Compliance Report: {{ data.framework|default('SOC2') }}</h1>
    <p>Generated: {{ generated_at }}</p>
    
    <h2>Overall Compliance: {{ data.compliance_score|default(0) }}%</h2>
    
    <h2>Controls</h2>
    {% for control in data.controls|default([]) %}
    <div class="control">
        <h3>{{ control.id }}: {{ control.name }}</h3>
        <p class="{{ control.status }}">Status: {{ control.status }}</p>
        {% if control.issues %}
        <p><strong>Issues:</strong> {{ control.issues|join(', ') }}</p>
        {% endif %}
        {% if control.remediation %}
        <p><strong>Remediation:</strong> {{ control.remediation }}</p>
        {% endif %}
    </div>
    {% endfor %}
</body>
</html>"""
    
    def _get_audit_template(self) -> str:
        return """<!DOCTYPE html>
<html>
<head>
    <title>Audit Report</title>
    <style>
        body { font-family: monospace; margin: 40px; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <h1>Audit Trail Report</h1>
    <p>Period: {{ data.period.start }} to {{ data.period.end }}</p>
    <p>Generated: {{ generated_at }}</p>
    
    <h2>Summary</h2>
    <p>Total Events: {{ data.total_events|default(0) }}</p>
    <p>Unique Users: {{ data.unique_users|default(0) }}</p>
    <p>Unique Actions: {{ data.unique_actions|default(0) }}</p>
    
    <h2>Events</h2>
    <table>
        <tr>
            <th>Timestamp</th>
            <th>User</th>
            <th>Action</th>
            <th>Resource</th>
            <th>Result</th>
        </tr>
        {% for event in data.events|default([]) %}
        <tr>
            <td>{{ event.timestamp }}</td>
            <td>{{ event.user_id }}</td>
            <td>{{ event.action }}</td>
            <td>{{ event.resource }}</td>
            <td>{{ event.result }}</td>
        </tr>
        {% endfor %}
    </table>
</body>
</html>"""
    
    async def _render_template(self, template_content: str, context: Dict) -> str:
        """Render template with context"""
        
        template = jinja2.Template(template_content)
        return template.render(**context)
    
    async def _convert_format(self, content: str, format: ReportFormat, context: Dict) -> Any:
        """Convert rendered content to requested format"""
        
        if format == ReportFormat.HTML:
            return content
            
        elif format == ReportFormat.PDF:
            return await self._convert_to_pdf(content)
            
        elif format == ReportFormat.JSON:
            return json.dumps(context.get("data", {}), indent=2, default=str)
            
        elif format == ReportFormat.CSV:
            return await self._convert_to_csv(context.get("data", {}))
            
        elif format == ReportFormat.MARKDOWN:
            return await self._convert_to_markdown(content)
            
        elif format == ReportFormat.TEXT:
            # Strip HTML tags for text version
            import re
            return re.sub('<[^<]+?>', '', content)
        
        return content
    
    async def _convert_to_pdf(self, html_content: str) -> bytes:
        """Convert HTML to PDF"""
        
        if PDFKIT_AVAILABLE:
            try:
                options = {
                    'page-size': 'Letter',
                    'margin-top': '0.75in',
                    'margin-right': '0.75in',
                    'margin-bottom': '0.75in',
                    'margin-left': '0.75in',
                    'encoding': "UTF-8",
                    'no-outline': None
                }
                
                pdf = pdfkit.from_string(html_content, False, options=options)
                return pdf
            except Exception as e:
                logger.error(f"PDF generation error: {e}")
                # Fall back to HTML if PDF fails
                return html_content.encode('utf-8')
        else:
            # Mock PDF generation
            logger.warning("pdfkit not installed. Returning HTML instead of PDF.")
            return html_content.encode('utf-8')
    
    async def _convert_to_csv(self, data: Dict) -> str:
        """Convert data to CSV format"""
        
        import csv
        import io
        
        output = io.StringIO()
        
        if isinstance(data, dict):
            # Flatten nested dict for CSV
            flat_data = self._flatten_dict(data)
            writer = csv.DictWriter(output, fieldnames=flat_data.keys())
            writer.writeheader()
            writer.writerow(flat_data)
        elif isinstance(data, list) and data:
            writer = csv.DictWriter(output, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        
        return output.getvalue()
    
    def _flatten_dict(self, d: Dict, parent_key: str = '', sep: str = '.') -> Dict:
        """Flatten nested dictionary"""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)
    
    async def _convert_to_markdown(self, html_content: str) -> str:
        """Convert HTML to Markdown"""
        
        if MARKDOWN_AVAILABLE:
            try:
                import html2text
                h = html2text.HTML2Text()
                h.ignore_links = False
                return h.handle(html_content)
            except Exception as e:
                logger.error(f"Markdown conversion error: {e}")
        
        # Simple HTML tag stripping as fallback
        import re
        return re.sub('<[^<]+?>', '', html_content)
    
    def _default_branding(self) -> Dict:
        """Get default branding"""
        return {
            "company_name": "Enterprise Security Orchestrator",
            "logo_url": "",
            "primary_color": "#1a73e8",
            "secondary_color": "#f5f5f5"
        }
    
    async def get_report(self, report_id: str) -> Optional[Dict]:
        """Get generated report"""
        return self.report_cache.get(report_id)
    
    async def list_reports(self, report_type: Optional[str] = None) -> List[Dict]:
        """List generated reports"""
        
        reports = list(self.report_cache.values())
        
        if report_type:
            reports = [r for r in reports if r["type"] == report_type]
        
        return sorted(reports, key=lambda x: x["generated_at"], reverse=True)
    
    async def delete_report(self, report_id: str):
        """Delete report"""
        self.report_cache.pop(report_id, None)