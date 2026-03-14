#!/usr/bin/env python3
"""
Master test runner that runs all tests (unit, integration, performance)
"""
import os
import sys
from pathlib import Path

# CRITICAL: Set environment variables BEFORE any other imports
os.environ["ENVIRONMENT"] = "test"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-for-testing-only-32-chars!!"
os.environ["FIELD_ENCRYPTION_KEY"] = "test-encryption-key-32-chars-long!!"
os.environ["POSTGRES_DSN"] = "postgresql://test:test@localhost:5432/test_db"
os.environ["REDIS_DSN"] = "redis://localhost:6379/1"
os.environ["MLFLOW_TRACKING_URI"] = "sqlite:///test_mlflow.db"

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Now safe to import other modules
import asyncio
import importlib
from datetime import datetime
from typing import Dict, List, Tuple

class TestRunner:
    """Master test runner"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.results = {
            "unit": {"passed": 0, "failed": 0, "total": 0, "tests": []},
            "integration": {"passed": 0, "failed": 0, "total": 0, "tests": []},
            "performance": {"passed": 0, "failed": 0, "total": 0, "tests": []}
        }
        self.failed_tests = []
    
    def get_test_modules(self) -> Dict[str, List[Tuple[str, str]]]:
        """Get all test modules by category"""
        return {
            "unit": [
                ("Adaptive Scanner", "tests.unit.autonomous.test_adaptive_scanner"),
                ("Auto Scaler", "tests.unit.autonomous.test_auto_scaler"),
                ("API Gateway", "tests.unit.gateway.test_api_gateway"),
                ("Data Masking", "tests.unit.governance.test_masking"),
                ("Vulnerability Predictor", "tests.unit.predictive.test_vulnerability_predictor"),
                ("Tool Recommender", "tests.unit.recommendation.test_tool_recommender"),
                ("Tenant Manager", "tests.unit.tenant.test_tenant_manager"),
                ("Billing", "tests.unit.tenant.test_billing"),
            ],
            "integration": [
                ("Full Workflow", "tests.integration.test_full_workflow"),
            ],
            "performance": [
                ("Load Scaling", "tests.performance.test_load_scaling"),
            ]
        }
    
    async def run_test_module(self, category: str, name: str, module_path: str) -> bool:
        """Run a single test module"""
        print(f"\n{'='*60}")
        print(f"🧪 Running {category.upper()} TEST: {name}")
        print(f"{'='*60}")
        
        try:
            module = importlib.import_module(module_path)
            
            if hasattr(module, 'manual_test'):
                await module.manual_test()
                self.results[category]["passed"] += 1
                self.results[category]["tests"].append(f"✅ {name}")
                print(f"\n✅ {name} PASSED")
                return True
            else:
                error_msg = f"No manual_test function in {module_path}"
                print(f"❌ {error_msg}")
                self.results[category]["failed"] += 1
                self.results[category]["tests"].append(f"❌ {name} (no manual_test)")
                self.failed_tests.append(f"{category}: {name} - {error_msg}")
                return False
                
        except Exception as e:
            error_msg = f"{e.__class__.__name__}: {e}"
            print(f"❌ Error: {error_msg}")
            import traceback
            traceback.print_exc()
            self.results[category]["failed"] += 1
            self.results[category]["tests"].append(f"❌ {name}")
            self.failed_tests.append(f"{category}: {name} - {error_msg}")
            return False
        finally:
            self.results[category]["total"] += 1
    
    async def run_category(self, category: str):
        """Run all tests in a category"""
        print(f"\n{'='*60}")
        print(f"📦 {category.upper()} TESTS")
        print(f"{'='*60}")
        
        modules = self.get_test_modules().get(category, [])
        for name, module_path in modules:
            await self.run_test_module(category, name, module_path)
    
    def print_summary(self):
        """Print test summary"""
        duration = (datetime.now() - self.start_time).total_seconds()
        
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60)
        
        total_passed = sum(cat["passed"] for cat in self.results.values())
        total_failed = sum(cat["failed"] for cat in self.results.values())
        total_tests = sum(cat["total"] for cat in self.results.values())
        
        for category, results in self.results.items():
            print(f"\n{category.upper()}:")
            print(f"   ✅ Passed: {results['passed']}")
            print(f"   ❌ Failed: {results['failed']}")
            print(f"   📊 Total: {results['total']}")
            if results['tests']:
                print(f"   Recent:")
                for test in results['tests'][-3:]:  # Show last 3
                    print(f"      {test}")
        
        print(f"\n⏱️  Duration: {duration:.2f} seconds")
        print(f"\n📈 OVERALL:")
        print(f"   ✅ Total Passed: {total_passed}")
        print(f"   ❌ Total Failed: {total_failed}")
        print(f"   📊 Total Tests: {total_tests}")
        
        if self.failed_tests:
            print(f"\n❌ Failed Tests ({len(self.failed_tests)}):")
            for test in self.failed_tests[:10]:  # Show first 10
                print(f"   • {test}")
            if len(self.failed_tests) > 10:
                print(f"   • ... and {len(self.failed_tests) - 10} more")
        
        if total_failed == 0:
            print(f"\n🎉 ALL TESTS PASSED!")
            return True
        else:
            print(f"\n⚠️  {total_failed} TEST(S) FAILED")
            return False
    
    async def run_all(self):
        """Run all tests"""
        print("="*60)
        print("🧪 ENTERPRISE TEST SUITE")
        print(f"Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Project Root: {Path(__file__).parent}")
        print("="*60)
        
        await self.run_category("unit")
        await self.run_category("integration")
        await self.run_category("performance")
        
        return self.print_summary()

async def main():
    """Main entry point"""
    runner = TestRunner()
    success = await runner.run_all()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())