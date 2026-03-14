
import sys
sys.path.append('.')
from src.app import app

print("📋 Registered Routes:")
print("=" * 60)

for route in app.routes:
    methods = ",".join(route.methods) if hasattr(route, 'methods') else 'ANY'
    path = getattr(route, 'path', str(route))
    name = getattr(route, 'name', '')
    print(f"{methods:10} {path:30} {name}")
