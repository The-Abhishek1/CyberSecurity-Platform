from typing import Dict, List, Optional, Set
from enum import Enum
import json


class Permission(str, Enum):
    # Execution permissions
    EXECUTE_SCAN = "execute:scan"
    EXECUTE_RECON = "execute:recon"
    EXECUTE_EXPLOIT = "execute:exploit"
    EXECUTE_ANALYSIS = "execute:analysis"
    
    # Read permissions
    READ_EXECUTIONS = "read:executions"
    READ_FINDINGS = "read:findings"
    READ_REPORTS = "read:reports"
    READ_AUDIT = "read:audit"
    
    # Write permissions
    WRITE_CONFIG = "write:config"
    WRITE_POLICIES = "write:policies"
    WRITE_RULES = "write:rules"
    
    # Admin permissions
    ADMIN_USERS = "admin:users"
    ADMIN_TENANTS = "admin:tenants"
    ADMIN_SYSTEM = "admin:system"
    ADMIN_AUDIT = "admin:audit"
    
    # Tool permissions
    USE_NMAP = "use:nmap"
    USE_NUCLEI = "use:nuclei"
    USE_SQLMAP = "use:sqlmap"
    USE_GOBUSTER = "use:gobuster"


class Role(str, Enum):
    ADMIN = "admin"
    SECURITY_ANALYST = "security_analyst"
    SECURITY_ENGINEER = "security_engineer"
    AUDITOR = "auditor"
    VIEWER = "viewer"
    API_USER = "api_user"


class RBACManager:
    """
    Role-Based Access Control Manager
    
    Features:
    - Role definitions
    - Permission assignments
    - Role hierarchy
    - Permission inheritance
    """
    
    def __init__(self):
        # Role definitions with permissions
        self.roles = {
            Role.ADMIN: {
                "permissions": [p for p in Permission],
                "inherits": []
            },
            Role.SECURITY_ANALYST: {
                "permissions": [
                    Permission.EXECUTE_SCAN,
                    Permission.READ_EXECUTIONS,
                    Permission.READ_FINDINGS,
                    Permission.READ_REPORTS,
                    Permission.USE_NMAP,
                    Permission.USE_NUCLEI
                ],
                "inherits": [Role.VIEWER]
            },
            Role.SECURITY_ENGINEER: {
                "permissions": [
                    Permission.EXECUTE_SCAN,
                    Permission.EXECUTE_RECON,
                    Permission.EXECUTE_EXPLOIT,
                    Permission.EXECUTE_ANALYSIS,
                    Permission.READ_EXECUTIONS,
                    Permission.READ_FINDINGS,
                    Permission.READ_REPORTS,
                    Permission.WRITE_CONFIG,
                    Permission.WRITE_RULES,
                    Permission.USE_NMAP,
                    Permission.USE_NUCLEI,
                    Permission.USE_SQLMAP,
                    Permission.USE_GOBUSTER
                ],
                "inherits": [Role.SECURITY_ANALYST]
            },
            Role.AUDITOR: {
                "permissions": [
                    Permission.READ_EXECUTIONS,
                    Permission.READ_FINDINGS,
                    Permission.READ_REPORTS,
                    Permission.READ_AUDIT
                ],
                "inherits": [Role.VIEWER]
            },
            Role.VIEWER: {
                "permissions": [
                    Permission.READ_EXECUTIONS,
                    Permission.READ_FINDINGS,
                    Permission.READ_REPORTS
                ],
                "inherits": []
            },
            Role.API_USER: {
                "permissions": [
                    Permission.EXECUTE_SCAN,
                    Permission.READ_EXECUTIONS
                ],
                "inherits": []
            }
        }
        
        # User role assignments
        self.user_roles: Dict[str, Set[Role]] = {}
        
        # Tenant-specific role assignments
        self.tenant_user_roles: Dict[str, Dict[str, Set[Role]]] = {}
    
    async def assign_role(
        self,
        user_id: str,
        role: Role,
        tenant_id: Optional[str] = None
    ):
        """Assign role to user"""
        
        if tenant_id:
            # Tenant-specific assignment
            if tenant_id not in self.tenant_user_roles:
                self.tenant_user_roles[tenant_id] = {}
            
            if user_id not in self.tenant_user_roles[tenant_id]:
                self.tenant_user_roles[tenant_id][user_id] = set()
            
            self.tenant_user_roles[tenant_id][user_id].add(role)
        else:
            # Global assignment
            if user_id not in self.user_roles:
                self.user_roles[user_id] = set()
            
            self.user_roles[user_id].add(role)
    
    async def remove_role(
        self,
        user_id: str,
        role: Role,
        tenant_id: Optional[str] = None
    ):
        """Remove role from user"""
        
        if tenant_id:
            if tenant_id in self.tenant_user_roles and user_id in self.tenant_user_roles[tenant_id]:
                self.tenant_user_roles[tenant_id][user_id].discard(role)
        else:
            if user_id in self.user_roles:
                self.user_roles[user_id].discard(role)
    
    async def get_user_permissions(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> Set[Permission]:
        """Get all permissions for user"""
        
        permissions = set()
        
        # Get global roles
        if user_id in self.user_roles:
            for role in self.user_roles[user_id]:
                permissions.update(await self._get_role_permissions(role))
        
        # Get tenant-specific roles
        if tenant_id and tenant_id in self.tenant_user_roles:
            if user_id in self.tenant_user_roles[tenant_id]:
                for role in self.tenant_user_roles[tenant_id][user_id]:
                    permissions.update(await self._get_role_permissions(role))
        
        return permissions
    
    async def _get_role_permissions(self, role: Role) -> Set[Permission]:
        """Get all permissions for a role (including inherited)"""
        
        if role not in self.roles:
            return set()
        
        role_config = self.roles[role]
        permissions = set(role_config["permissions"])
        
        # Add inherited permissions
        for inherited_role in role_config["inherits"]:
            permissions.update(await self._get_role_permissions(inherited_role))
        
        return permissions
    
    async def has_permission(
        self,
        user_id: str,
        permission: Permission,
        tenant_id: Optional[str] = None
    ) -> bool:
        """Check if user has specific permission"""
        
        user_permissions = await self.get_user_permissions(user_id, tenant_id)
        return permission in user_permissions
    
    async def has_any_permission(
        self,
        user_id: str,
        permissions: List[Permission],
        tenant_id: Optional[str] = None
    ) -> bool:
        """Check if user has any of the permissions"""
        
        user_permissions = await self.get_user_permissions(user_id, tenant_id)
        return any(p in user_permissions for p in permissions)
    
    async def has_all_permissions(
        self,
        user_id: str,
        permissions: List[Permission],
        tenant_id: Optional[str] = None
    ) -> bool:
        """Check if user has all permissions"""
        
        user_permissions = await self.get_user_permissions(user_id, tenant_id)
        return all(p in user_permissions for p in permissions)
    
    async def get_user_roles(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> Set[Role]:
        """Get roles assigned to user"""
        
        roles = self.user_roles.get(user_id, set()).copy()
        
        if tenant_id and tenant_id in self.tenant_user_roles:
            if user_id in self.tenant_user_roles[tenant_id]:
                roles.update(self.tenant_user_roles[tenant_id][user_id])
        
        return roles
    
    async def get_users_with_role(
        self,
        role: Role,
        tenant_id: Optional[str] = None
    ) -> List[str]:
        """Get all users with specific role"""
        
        users = []
        
        if tenant_id:
            if tenant_id in self.tenant_user_roles:
                for user_id, roles in self.tenant_user_roles[tenant_id].items():
                    if role in roles:
                        users.append(user_id)
        else:
            for user_id, roles in self.user_roles.items():
                if role in roles:
                    users.append(user_id)
        
        return users