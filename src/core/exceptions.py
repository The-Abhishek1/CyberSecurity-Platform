from typing import Optional, Dict, Any, List
from fastapi import HTTPException, status


class EnterpriseBaseException(Exception):
    """Base exception for all enterprise exceptions"""
    
    def __init__(
        self,
        message: str,
        code: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


# ========== Authentication & Authorization Exceptions ==========
class AuthenticationError(EnterpriseBaseException):
    """Authentication failed"""
    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="AUTHENTICATION_ERROR",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details
        )


class AuthorizationError(EnterpriseBaseException):
    """Authorization failed"""
    def __init__(self, message: str = "Insufficient permissions", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="AUTHORIZATION_ERROR",
            status_code=status.HTTP_403_FORBIDDEN,
            details=details
        )


class InvalidTokenError(AuthenticationError):
    """Invalid or expired token"""
    def __init__(self, message: str = "Invalid or expired token", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, details=details)
        self.code = "INVALID_TOKEN"


class MFARequiredError(AuthenticationError):
    """MFA is required but not provided"""
    def __init__(self, message: str = "MFA verification required", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, details=details)
        self.code = "MFA_REQUIRED"
        self.status_code = status.HTTP_401_UNAUTHORIZED


# ========== Rate Limiting Exceptions ==========
class RateLimitExceededError(EnterpriseBaseException):
    """Rate limit exceeded"""
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        limit: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code="RATE_LIMIT_EXCEEDED",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details={
                **(details or {}),
                "retry_after": retry_after,
                "limit": limit
            }
        )


# ========== Validation Exceptions ==========
class ValidationError(EnterpriseBaseException):
    """Request validation failed"""
    def __init__(self, message: str = "Validation failed", errors: Optional[List[Dict[str, Any]]] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details={"errors": errors or []}
        )


class ResourceNotFoundError(EnterpriseBaseException):
    """Resource not found"""
    def __init__(self, message: str = "Resource not found", resource_type: Optional[str] = None):
        super().__init__(
            message=message,
            code="RESOURCE_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"resource_type": resource_type}
        )


# ========== Business Logic Exceptions ==========
class BusinessRuleViolationError(EnterpriseBaseException):
    """Business rule violation"""
    def __init__(self, message: str, rule: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="BUSINESS_RULE_VIOLATION",
            status_code=status.HTTP_400_BAD_REQUEST,
            details={**(details or {}), "rule": rule}
        )


class DuplicateResourceError(EnterpriseBaseException):
    """Resource already exists"""
    def __init__(self, message: str = "Resource already exists", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="DUPLICATE_RESOURCE",
            status_code=status.HTTP_409_CONFLICT,
            details=details
        )


# ========== Integration Exceptions ==========
class ExternalServiceError(EnterpriseBaseException):
    """External service error"""
    def __init__(
        self,
        message: str = "External service error",
        service: str = "unknown",
        status_code: int = status.HTTP_502_BAD_GATEWAY,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code="EXTERNAL_SERVICE_ERROR",
            status_code=status_code,
            details={**(details or {}), "service": service}
        )


class DatabaseError(EnterpriseBaseException):
    """Database operation failed"""
    def __init__(self, message: str = "Database operation failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="DATABASE_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )


# ========== Orchestrator Specific Exceptions ==========
class DAGValidationError(EnterpriseBaseException):
    """DAG validation failed"""
    def __init__(self, message: str, errors: List[str], details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="DAG_VALIDATION_ERROR",
            status_code=status.HTTP_400_BAD_REQUEST,
            details={**(details or {}), "errors": errors}
        )


class AgentExecutionError(EnterpriseBaseException):
    """Agent execution failed"""
    def __init__(self, message: str, agent: str, task: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="AGENT_EXECUTION_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={**(details or {}), "agent": agent, "task": task}
        )


class ToolExecutionError(EnterpriseBaseException):
    """Tool execution failed"""
    def __init__(self, message: str, tool: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="TOOL_EXECUTION_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={**(details or {}), "tool": tool}
        )


class BudgetExceededError(EnterpriseBaseException):
    """Budget or quota exceeded"""
    def __init__(self, message: str = "Budget exceeded", budget_type: str = "cost", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="BUDGET_EXCEEDED",
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            details={**(details or {}), "budget_type": budget_type}
        )


# ========== FastAPI Exception Handler ==========
def enterprise_exception_handler(request, exc: EnterpriseBaseException):
    """Convert enterprise exceptions to FastAPI HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "timestamp": datetime.utcnow().isoformat(),
                "path": request.url.path
            }
        }
    )

class QuotaExceededError(Exception):
    """Raised when quota limits are exceeded"""

    def __init__(self, message: str, quota_type: str | None = None):
        self.message = message
        self.quota_type = quota_type
        super().__init__(message)
        

class WorkerExecutionError(EnterpriseBaseException):
    """Worker execution failed"""

    def __init__(
        self,
        message: str,
        worker_id: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code="WORKER_EXECUTION_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={**(details or {}), "worker_id": worker_id}
        )