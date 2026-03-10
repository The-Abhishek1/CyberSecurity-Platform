from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import jinja2
import pdfkit
import json
import markdown

from src.reporting.templates.compliance_templates import ComplianceTemplates
from src.reporting.scheduler.report_scheduler import ReportScheduler
from src.utils.logging import logger


class ReportFormat(str, Enum):
    PDF = "pdf"
    HTML = "html"
    JSON = "json"
    CSV = "csv"
    MARKDOWN = "markdown"


class ReportEngine:
    """
    Enterprise Report Engine
    
    Features:
    - Multiple output formats
    - Template-based generation
    - Scheduled reports
    - Custom branding
    - Data visualization
    - Export capabilities
    """
    
    def __init__(self, scheduler: ReportScheduler):
        self.scheduler = scheduler
        
        # Template engine
        self.template_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader("src/reporting/templates"),
            autoescape=True
        )
        
        # Compliance templates
        self.compliance_templates = ComplianceTemplates()
        
        # Report cache
        self.report_cache: Dict[str, Dict] = {}
        
        logger.info("Report Engine initialized")
    
    async def generate_report(
        self,
        report_type: str,
        data: Dict,
        format: ReportFormat = ReportFormat.PDF,
        template: Optional[str] = None,
        branding: Optional[Dict] = None
    ) -> Dict:
        """Generate report"""
        
        report_id = f"rpt_{uuid.uuid4().hex[:12]}"
        
        # Get template
        if template:
            template_content = await self._load_template(template)
        else:
            template_content = await self.compliance_templates.get_template(report_type)
        
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
        output = await self._convert_format(rendered, format)
        
        report = {
            "report_id": report_id,
            "type": report_type,
            "format": format.value,
            "generated_at": context["generated_at"],
            "size_bytes": len(output),
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
        
        try:
            template = self.template_env.get_template(template_name)
            return template.source
        except Exception as e:
            logger.error(f"Failed to load template {template_name}: {e}")
            return ""
    
    async def _render_template(self, template_content: str, context: Dict) -> str:
        """Render template with context"""
        
        template = jinja2.Template(template_content)
        return template.render(**context)
    
    async def _convert_format(self, content: str, format: ReportFormat) -> str:
        """Convert rendered content to requested format"""
        
        if format == ReportFormat.HTML:
            return content
            
        elif format == ReportFormat.PDF:
            # Convert HTML to PDF
            options = {
                'page-size': 'Letter',
                'margin-top': '0.75in',
                'margin-right': '0.75in',
                'margin-bottom': '0.75in',
                'margin-left': '0.75in',
                'encoding': "UTF-8",
                'no-outline': None
            }
            
            pdf = pdfkit.from_string(content, False, options=options)
            return pdf.decode('latin1')
            
        elif format == ReportFormat.JSON:
            # Extract data from content (simplified)
            return json.dumps(context.get("data", {}), indent=2)
            
        elif format == ReportFormat.CSV:
            # Convert to CSV (simplified)
            import csv
            import io
            
            output = io.StringIO()
            data = context.get("data", {})
            
            if data and isinstance(data, dict):
                writer = csv.writer(output)
                writer.writerow(data.keys())
                writer.writerow(data.values())
            
            return output.getvalue()
            
        elif format == ReportFormat.MARKDOWN:
            # Convert HTML to Markdown (simplified)
            import html2text
            h = html2text.HTML2Text()
            return h.handle(content)
        
        return content
    
    def _default_branding(self) -> Dict:
        """Get default branding"""
        return {
            "company_name": "Enterprise Security Orchestrator",
            "logo_url": "https://example.com/logo.png",
            "primary_color": "#1a73e8",
            "secondary_color": "#5f6368"
        }
    
    async def schedule_report(
        self,
        report_type: str,
        schedule: str,
        recipients: List[str],
        format: ReportFormat = ReportFormat.PDF,
        params: Optional[Dict] = None
    ) -> str:
        """Schedule recurring report"""
        
        job_id = await self.scheduler.schedule_job(
            job_type="report",
            schedule=schedule,
            func=self.generate_report,
            args=[report_type],
            kwargs={
                "format": format,
                **(params or {})
            },
            recipients=recipients
        )
        
        logger.info(f"Scheduled report {report_type} with schedule {schedule}")
        
        return job_id
    
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


class ExecutiveDashboard:
    """Executive dashboard with key metrics"""
    
    async def generate(
        self,
        tenant_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """Generate executive dashboard"""
        
        return {
            "tenant_id": tenant_id,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "summary": {
                "total_scans": 1250,
                "vulnerabilities_found": 342,
                "critical_findings": 23,
                "average_risk_score": 42.5,
                "compliance_score": 87.5
            },
            "trends": {
                "vulnerabilities_over_time": [
                    {"date": "2024-01-01", "count": 45},
                    {"date": "2024-01-02", "count": 52},
                    {"date": "2024-01-03", "count": 38}
                ],
                "scan_volume": [
                    {"date": "2024-01-01", "count": 120},
                    {"date": "2024-01-02", "count": 145},
                    {"date": "2024-01-03", "count": 132}
                ]
            },
            "top_findings": [
                {
                    "title": "Critical SQL Injection",
                    "severity": "critical",
                    "count": 5,
                    "trend": "+2"
                },
                {
                    "title": "Open Port 22",
                    "severity": "high",
                    "count": 12,
                    "trend": "-3"
                }
            ],
            "compliance_status": {
                "soc2": 92,
                "hipaa": 88,
                "pci_dss": 85,
                "gdpr": 90
            },
            "resource_usage": {
                "api_calls": 45200,
                "execution_minutes": 3240,
                "storage_gb": 125,
                "active_workers": 15
            }
        }


class ComplianceDashboard:
    """Compliance dashboard for audit purposes"""
    
    async def generate(
        self,
        framework: str,
        tenant_id: str,
        report_date: datetime
    ) -> Dict:
        """Generate compliance dashboard"""
        
        return {
            "framework": framework,
            "tenant_id": tenant_id,
            "report_date": report_date.isoformat(),
            "overall_compliance": 87.5,
            "controls": [
                {
                    "id": "CC1.1",
                    "name": "Access Control Policy",
                    "status": "compliant",
                    "last_audit": "2024-01-15",
                    "evidence_count": 12
                },
                {
                    "id": "CC2.2",
                    "name": "Audit Logging",
                    "status": "partial",
                    "last_audit": "2024-01-10",
                    "issues": ["Incomplete log retention"],
                    "remediation": "Extend log retention to 90 days"
                }
            ],
            "audit_trail": [
                {
                    "date": "2024-01-20",
                    "event": "Access control review",
                    "status": "passed",
                    "auditor": "system"
                }
            ],
            "evidence_summary": {
                "total_files": 45,
                "last_upload": "2024-01-21",
                "expiring_soon": 3
            }
        }