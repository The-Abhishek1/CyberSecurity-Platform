from typing import Dict, Optional
from datetime import datetime, timedelta


class BillingCalculator:
    """
    Enterprise Billing Calculator
    
    Features:
    - Tier-based pricing
    - Usage-based billing
    - Discount application
    - Invoice generation
    """
    
    def __init__(self, usage_aggregator: UsageAggregator):
        self.usage_aggregator = usage_aggregator
        
        # Pricing tiers
        self.tiers = {
            "free": {
                "base_price": 0,
                "included_executions": 100,
                "included_storage_gb": 1,
                "execution_price": 0.01,
                "storage_price": 0.10,
                "api_call_price": 0.001
            },
            "basic": {
                "base_price": 99,
                "included_executions": 1000,
                "included_storage_gb": 10,
                "execution_price": 0.008,
                "storage_price": 0.08,
                "api_call_price": 0.0008
            },
            "professional": {
                "base_price": 499,
                "included_executions": 10000,
                "included_storage_gb": 100,
                "execution_price": 0.005,
                "storage_price": 0.05,
                "api_call_price": 0.0005
            },
            "enterprise": {
                "base_price": 1999,
                "included_executions": 100000,
                "included_storage_gb": 1000,
                "execution_price": 0.003,
                "storage_price": 0.03,
                "api_call_price": 0.0003
            }
        }
        
        logger.info("Billing Calculator initialized")
    
    async def calculate_invoice(
        self,
        tenant_id: str,
        tier: str,
        billing_period: str = "monthly"
    ) -> Dict:
        """Calculate invoice for tenant"""
        
        # Get usage for period
        usage_summary = await self.usage_aggregator.get_usage_summary(tenant_id, billing_period)
        
        # Get tier pricing
        pricing = self.tiers.get(tier.lower(), self.tiers["basic"])
        
        # Calculate charges
        charges = []
        total = pricing["base_price"]
        
        # Calculate overage charges
        executions = usage_summary["resources"].get("executions", {}).get("usage", 0)
        if executions > pricing["included_executions"]:
            overage = executions - pricing["included_executions"]
            execution_charge = overage * pricing["execution_price"]
            charges.append({
                "item": "execution_overage",
                "quantity": overage,
                "rate": pricing["execution_price"],
                "amount": execution_charge
            })
            total += execution_charge
        
        storage = usage_summary["resources"].get("storage_gb", {}).get("usage", 0)
        if storage > pricing["included_storage_gb"]:
            overage = storage - pricing["included_storage_gb"]
            storage_charge = overage * pricing["storage_price"]
            charges.append({
                "item": "storage_overage",
                "quantity": overage,
                "rate": pricing["storage_price"],
                "amount": storage_charge
            })
            total += storage_charge
        
        # Add base charge
        if pricing["base_price"] > 0:
            charges.append({
                "item": "base_subscription",
                "quantity": 1,
                "rate": pricing["base_price"],
                "amount": pricing["base_price"]
            })
        
        invoice = {
            "invoice_id": f"inv_{uuid.uuid4().hex[:12]}",
            "tenant_id": tenant_id,
            "period": billing_period,
            "generated_at": datetime.utcnow().isoformat(),
            "due_date": (datetime.utcnow() + timedelta(days=30)).isoformat(),
            "charges": charges,
            "subtotal": total,
            "tax": total * 0.1,  # 10% tax
            "total": total * 1.1,
            "usage_summary": usage_summary
        }
        
        return invoice
    
    async def apply_discount(
        self,
        tenant_id: str,
        discount_type: str,
        discount_value: float
    ):
        """Apply discount to tenant"""
        # In production, store discount in database
        logger.info(f"Applied {discount_type} discount of {discount_value} to {tenant_id}")