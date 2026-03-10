from typing import Dict, List, Optional
import aiohttp
from jira import JIRA


class JiraIntegration:
    """
    Jira Ticketing Integration
    
    Features:
    - Create tickets from findings
    - Update ticket status
    - Sync findings with Jira
    - Custom field mapping
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.jira = None
        self._connect()
    
    def _connect(self):
        """Connect to Jira"""
        self.jira = JIRA(
            server=self.config["url"],
            basic_auth=(
                self.config["username"],
                self.config["api_token"]
            )
        )
    
    async def create_issue(
        self,
        project_key: str,
        summary: str,
        description: str,
        issue_type: str = "Task",
        priority: str = "Medium",
        labels: Optional[List[str]] = None,
        custom_fields: Optional[Dict] = None
    ) -> Dict:
        """Create Jira issue"""
        
        issue_dict = {
            "project": {"key": project_key},
            "summary": summary,
            "description": description,
            "issuetype": {"name": issue_type},
            "priority": {"name": priority}
        }
        
        if labels:
            issue_dict["labels"] = labels
        
        if custom_fields:
            issue_dict.update(custom_fields)
        
        try:
            issue = self.jira.create_issue(fields=issue_dict)
            
            return {
                "id": issue.id,
                "key": issue.key,
                "url": f"{self.config['url']}/browse/{issue.key}"
            }
        except Exception as e:
            logger.error(f"Jira create issue failed: {e}")
            raise
    
    async def create_vulnerability_ticket(
        self,
        finding: Dict,
        project_key: str
    ) -> Dict:
        """Create ticket from vulnerability finding"""
        
        summary = f"[Security] {finding.get('title', 'Vulnerability Found')}"
        
        description = f"""
h2. Vulnerability Details
* Target: {finding.get('target')}
* Severity: {finding.get('severity', 'Unknown')}
* CVSS Score: {finding.get('cvss_score', 'N/A')}
* CVE: {finding.get('cve_id', 'N/A')}

h2. Description
{finding.get('description', 'No description provided')}

h2. Remediation
{finding.get('remediation', 'No remediation steps provided')}

h2. Evidence
{finding.get('evidence', 'No evidence provided')}

h2. Detection Details
* Scanner: {finding.get('scanner')}
* Detected at: {finding.get('detected_at')}
* Scan ID: {finding.get('scan_id')}
        """
        
        # Map severity to Jira priority
        priority_map = {
            "critical": "Highest",
            "high": "High",
            "medium": "Medium",
            "low": "Low",
            "info": "Lowest"
        }
        
        priority = priority_map.get(
            finding.get('severity', 'medium').lower(),
            "Medium"
        )
        
        labels = ["security", "vulnerability"]
        if finding.get("cve_id"):
            labels.append("cve")
        
        return await self.create_issue(
            project_key=project_key,
            summary=summary,
            description=description,
            issue_type="Bug",
            priority=priority,
            labels=labels,
            custom_fields={
                "customfield_10001": finding.get("cvss_score"),  # Example custom field
                "customfield_10002": finding.get("cve_id")
            }
        )
    
    async def update_issue_status(
        self,
        issue_key: str,
        transition_name: str
    ):
        """Update issue status"""
        
        try:
            issue = self.jira.issue(issue_key)
            transitions = self.jira.transitions(issue)
            
            for transition in transitions:
                if transition['name'].lower() == transition_name.lower():
                    self.jira.transition_issue(issue, transition['id'])
                    return True
            
            logger.warning(f"Transition {transition_name} not found for {issue_key}")
            return False
            
        except Exception as e:
            logger.error(f"Jira update issue failed: {e}")
            return False
    
    async def add_comment(self, issue_key: str, comment: str):
        """Add comment to issue"""
        
        try:
            self.jira.add_comment(issue_key, comment)
            return True
        except Exception as e:
            logger.error(f"Jira add comment failed: {e}")
            return False
    
    async def get_issue(self, issue_key: str) -> Optional[Dict]:
        """Get issue details"""
        
        try:
            issue = self.jira.issue(issue_key)
            
            return {
                "key": issue.key,
                "summary": issue.fields.summary,
                "status": issue.fields.status.name,
                "priority": issue.fields.priority.name,
                "assignee": issue.fields.assignee.displayName if issue.fields.assignee else None,
                "created": issue.fields.created,
                "updated": issue.fields.updated
            }
        except Exception as e:
            logger.error(f"Jira get issue failed: {e}")
            return None