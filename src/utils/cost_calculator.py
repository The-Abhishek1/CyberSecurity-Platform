class CostCalculator:
    def estimate_cost(self, token_count: int, model: str) -> float:
        # Simple estimation
        return token_count * 0.00002
    
    def estimate_task_cost(self, task) -> float:
        return 0.01  # Default cost