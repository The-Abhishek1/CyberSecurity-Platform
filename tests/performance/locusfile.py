# tests/performance/locustfile.py

from locust import HttpUser, task, between
import random
import json

class OrchestratorUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """Setup before tests"""
        self.process_ids = []
    
    @task(3)
    def execute_scan(self):
        """Execute a scan"""
        goals = [
            "Scan example.com",
            "Check for vulnerabilities",
            "Port scan target",
            "Security assessment"
        ]
        
        response = self.client.post(
            "/api/v1/execute",
            json={
                "goal": random.choice(goals),
                "target": "example.com",
                "priority": random.choice(["low", "medium", "high"]),
                "mode": "async"
            }
        )
        
        if response.status_code == 202:
            data = response.json()
            self.process_ids.append(data["process_id"])
    
    @task(2)
    def check_status(self):
        """Check status of executions"""
        if self.process_ids:
            process_id = random.choice(self.process_ids)
            self.client.get(f"/api/v1/status/{process_id}")
    
    @task(1)
    def list_executions(self):
        """List executions"""
        self.client.get("/api/v1/list")
    
    @task(1)
    def health_check(self):
        """Health check"""
        self.client.get("/health")