
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)


class ApprovalWorkflow:
    """Manages human-in-the-loop approval workflows"""
    
    def __init__(self):
        self.approval_requests = {}
        self.approval_templates = {}
        logger.info("Approval Workflow initialized")
    
    async def create_approval_request(self, 
                                      request_type: str,
                                      requester: str,
                                      approvers: List[str],
                                      data: Dict[str, Any],
                                      deadline: Optional[datetime] = None,
                                      escalation_policy: Optional[Dict] = None) -> str:
        """Create a new approval request"""
        
        request_id = f"apr_{uuid.uuid4().hex[:12]}"
        
        request = {
            "request_id": request_id,
            "type": request_type,
            "requester": requester,
            "approvers": approvers,
            "data": data,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "deadline": deadline.isoformat() if deadline else None,
            "escalation_policy": escalation_policy or {},
            "decisions": [],
            "current_approver_index": 0
        }
        
        self.approval_requests[request_id] = request
        logger.info(f"Created approval request {request_id} from {requester}")
        
        return request_id
    
    async def get_pending_approvals(self, user_id: str) -> List[Dict]:
        """Get pending approvals for a user"""
        
        pending = []
        
        for request_id, request in self.approval_requests.items():
            if request["status"] != "pending":
                continue
            
            if user_id in request["approvers"]:
                # Check if it's this user's turn (if sequential)
                if request.get("sequential", False):
                    current_index = request["current_approver_index"]
                    if current_index < len(request["approvers"]) and request["approvers"][current_index] == user_id:
                        pending.append(request)
                else:
                    # Parallel approval - anyone can approve
                    pending.append(request)
        
        return pending
    
    async def approve(self, request_id: str, approver: str, comments: str = "") -> bool:
        """Approve a request"""
        
        if request_id not in self.approval_requests:
            logger.error(f"Approval request {request_id} not found")
            return False
        
        request = self.approval_requests[request_id]
        
        if request["status"] != "pending":
            logger.warning(f"Approval request {request_id} is not pending")
            return False
        
        # Record decision
        decision = {
            "approver": approver,
            "decision": "approved",
            "comments": comments,
            "timestamp": datetime.utcnow().isoformat()
        }
        request["decisions"].append(decision)
        
        # Check if this completes the approval
        if await self._is_approval_complete(request):
            request["status"] = "approved"
            request["completed_at"] = datetime.utcnow().isoformat()
            logger.info(f"Approval request {request_id} approved")
        
        return True
    
    async def reject(self, request_id: str, approver: str, reason: str) -> bool:
        """Reject a request"""
        
        if request_id not in self.approval_requests:
            logger.error(f"Approval request {request_id} not found")
            return False
        
        request = self.approval_requests[request_id]
        
        if request["status"] != "pending":
            logger.warning(f"Approval request {request_id} is not pending")
            return False
        
        # Record decision
        decision = {
            "approver": approver,
            "decision": "rejected",
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat()
        }
        request["decisions"].append(decision)
        
        # Rejection immediately completes (with failure)
        request["status"] = "rejected"
        request["completed_at"] = datetime.utcnow().isoformat()
        logger.info(f"Approval request {request_id} rejected by {approver}")
        
        return True
    
    async def _is_approval_complete(self, request: Dict) -> bool:
        """Check if approval is complete"""
        
        if request.get("sequential", False):
            # Sequential approval - need approval from all
            return len(request["decisions"]) >= len(request["approvers"])
        else:
            # Parallel approval - need at least one approval
            return len([d for d in request["decisions"] if d["decision"] == "approved"]) > 0
    
    async def get_request_status(self, request_id: str) -> Optional[Dict]:
        """Get status of an approval request"""
        
        return self.approval_requests.get(request_id)
    
    async def create_approval_template(self, 
                                       template_name: str,
                                       approvers: List[str],
                                       sequential: bool = False,
                                       deadline_hours: Optional[int] = None,
                                       escalation_policy: Optional[Dict] = None) -> str:
        """Create a reusable approval template"""
        
        template_id = f"apt_{uuid.uuid4().hex[:8]}"
        
        template = {
            "template_id": template_id,
            "name": template_name,
            "approvers": approvers,
            "sequential": sequential,
            "deadline_hours": deadline_hours,
            "escalation_policy": escalation_policy or {},
            "created_at": datetime.utcnow().isoformat()
        }
        
        self.approval_templates[template_id] = template
        logger.info(f"Created approval template {template_name}")
        
        return template_id
    
    async def create_from_template(self, 
                                   template_id: str,
                                   requester: str,
                                   data: Dict[str, Any]) -> Optional[str]:
        """Create approval request from template"""
        
        if template_id not in self.approval_templates:
            logger.error(f"Approval template {template_id} not found")
            return None
        
        template = self.approval_templates[template_id]
        
        deadline = None
        if template.get("deadline_hours"):
            from datetime import timedelta
            deadline = datetime.utcnow() + timedelta(hours=template["deadline_hours"])
        
        return await self.create_approval_request(
            request_type=template["name"],
            requester=requester,
            approvers=template["approvers"],
            data=data,
            deadline=deadline,
            escalation_policy=template["escalation_policy"]
        )
    
    async def check_deadlines(self):
        """Check for expired approvals and handle escalations"""
        
        now = datetime.utcnow()
        
        for request_id, request in self.approval_requests.items():
            if request["status"] != "pending":
                continue
            
            if request.get("deadline"):
                deadline = datetime.fromisoformat(request["deadline"])
                if now > deadline:
                    # Deadline passed
                    if request.get("escalation_policy", {}).get("on_deadline") == "auto_approve":
                        request["status"] = "approved"
                        request["completed_at"] = now.isoformat()
                        request["auto_approved"] = True
                        logger.info(f"Approval request {request_id} auto-approved due to deadline")
                    else:
                        request["status"] = "expired"
                        request["completed_at"] = now.isoformat()
                        logger.info(f"Approval request {request_id} expired")