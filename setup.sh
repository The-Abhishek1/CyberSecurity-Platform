#!/bin/bash
# setup.sh - Complete project setup script

set -e

echo "🚀 Enterprise Security Orchestrator - Setup Script"
echo "=================================================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check prerequisites
print_status "📋 Checking prerequisites..."

check_command() {
    if command -v $1 >/dev/null 2>&1; then
        print_success "$1 installed"
        return 0
    else
        print_warning "$1 not found"
        return 1
    fi
}

check_command python3 || { print_error "Python 3.11+ required"; exit 1; }
check_command docker || { print_error "Docker required"; exit 1; }
check_command docker-compose || { print_error "Docker Compose required"; exit 1; }
check_command git || { print_error "Git required"; exit 1; }
check_command curl || { print_warning "curl not found, will install"; }
check_command wget || { print_warning "wget not found, will install"; }

# Check Python version
PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
if (( $(echo "$PY_VERSION < 3.9" | bc -l) )); then
    print_error "Python 3.9+ required, found $PY_VERSION"
    exit 1
fi
print_success "Python $PY_VERSION detected"

# Check Docker version
DOCKER_VERSION=$(docker --version | cut -d ' ' -f3 | cut -d '.' -f1)
if [ "$DOCKER_VERSION" -lt 20 ]; then
    print_warning "Docker version 20+ recommended, found $DOCKER_VERSION"
fi

print_success "All prerequisites satisfied"

# Create project directory
PROJECT_DIR="enterprise-security-orchestrator"
print_status "📁 Creating project structure in $PROJECT_DIR..."

mkdir -p $PROJECT_DIR
cd $PROJECT_DIR

# Initialize git repository
print_status "🔧 Initializing git repository..."
git init > /dev/null 2>&1
print_success "Git repository initialized"

# Create directory structure
print_status "Creating directory structure..."

# Source directories
mkdir -p src/{api,core,scheduler,agents,memory,orchestrator,tools,workers,recovery,domain_agents,observability,security,monitoring,governance,gateway,tenant,integrations,workflow,reporting,ai,predictive,autonomous,recommendation,knowledge_graph}

# Test directories
mkdir -p tests/{unit,integration,performance,security,chaos,e2e}

# Docker files
mkdir -p docker/{api,workers,base,monitoring,init}

# Configuration
mkdir -p config/{development,staging,production}

# Data directories
mkdir -p data/{postgres,redis,rabbitmq,prometheus,grafana,loki}

# Logs
mkdir -p logs/{api,workers,audit,monitoring}

# Scripts
mkdir -p scripts/{deployment,backup,monitoring,testing,chaos}

# Documentation
mkdir -p docs/{architecture,deployment,operations,security,api,runbooks}

print_success "Directory structure created"

# Create virtual environment
print_status "🐍 Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate
print_success "Virtual environment created and activated"

# Create requirements.txt with all dependencies
print_status "📦 Creating requirements.txt..."

cat > requirements.txt << 'EOF'
# Core Framework
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0
python-multipart==0.0.6

# Database
asyncpg==0.29.0
sqlalchemy==2.0.23
alembic==1.12.1
redis==5.0.1
motor==3.3.2
aiosqlite==0.19.0  # For testing

# Message Queue
celery==5.3.4
aio-pika==9.3.0
rabbitmq-admin==1.0.0

# Security
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
cryptography==41.0.7
pyotp==2.9.0
qrcode==7.4.2
python-jose==3.3.0
bcrypt==4.0.1

# ML/AI
numpy==1.24.3
pandas==2.1.3
scikit-learn==1.3.2
tensorflow==2.13.0
xgboost==2.0.2
mlflow==2.8.0
joblib==1.3.2

# Monitoring & Observability
prometheus-client==0.19.0
opentelemetry-api==1.21.0
opentelemetry-sdk==1.21.0
opentelemetry-exporter-otlp==1.21.0
opentelemetry-instrumentation-fastapi==0.42b0
opentelemetry-instrumentation-sqlalchemy==0.42b0
opentelemetry-instrumentation-redis==0.42b0
python-json-logger==2.0.7

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
pytest-xdist==3.5.0
pytest-timeout==2.2.0
pytest-mock==3.12.0
locust==2.19.1
hypothesis==6.92.0
faker==20.1.0
factory-boy==3.3.0
requests-mock==1.11.0

# Development
black==23.11.0
isort==5.12.0
flake8==6.1.0
mypy==1.7.0
pre-commit==3.5.0
bandit==1.7.5
safety==2.3.5

# API & Web
httpx==0.25.1
requests==2.31.0
websockets==12.0
graphene==3.3
graphql-core==3.2.3

# Utils
tenacity==8.2.3
python-dotenv==1.0.0
email-validator==2.1.0
jinja2==3.1.2
pyyaml==6.0.1
click==8.1.7
typer==0.9.0
rich==13.7.0
python-dateutil==2.8.2
pytz==2023.3
EOF

print_success "requirements.txt created"

# Install dependencies
print_status "Installing Python dependencies..."
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt > /dev/null 2>&1
print_success "Dependencies installed"

# Create .env file
print_status "🔐 Creating environment configuration..."

cat > .env << 'EOF'
# Environment
ENVIRONMENT=development
DEBUG=true
SECRET_KEY=$(openssl rand -hex 32)
API_VERSION=v1
API_PORT=8000
API_HOST=0.0.0.0

# Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=orchestrator
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DSN=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DSN=redis://${REDIS_HOST}:${REDIS_PORT}/0

# RabbitMQ
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
RABBITMQ_DSN=amqp://${RABBITMQ_USER}:${RABBITMQ_PASSWORD}@${RABBITMQ_HOST}:${RABBITMQ_PORT}/

# Authentication
JWT_SECRET_KEY=$(openssl rand -hex 32)
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Encryption
FIELD_ENCRYPTION_KEY=$(openssl rand -hex 32)

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
AUDIT_LOG_PATH=./logs/audit/audit.log

# Testing
TEST_DATABASE_URL=sqlite+aiosqlite:///./test.db
TEST_REDIS_URL=redis://localhost:6379/1
EOF

print_success "Environment configuration created"

# Create docker-compose.yml
print_status "🐳 Creating Docker Compose configuration..."

cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: eso-postgres
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: orchestrator
    ports:
      - "5432:5432"
    volumes:
      - ./data/postgres:/var/lib/postgresql/data
      - ./docker/init/postgres:/docker-entrypoint-initdb.d
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - eso-network

  redis:
    image: redis:7-alpine
    container_name: eso-redis
    ports:
      - "6379:6379"
    volumes:
      - ./data/redis:/data
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - eso-network

  rabbitmq:
    image: rabbitmq:3-management-alpine
    container_name: eso-rabbitmq
    environment:
      RABBITMQ_DEFAULT_USER: guest
      RABBITMQ_DEFAULT_PASS: guest
    ports:
      - "5672:5672"
      - "15672:15672"
    volumes:
      - ./data/rabbitmq:/var/lib/rabbitmq
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "ping"]
      interval: 30s
      timeout: 10s
      retries: 5
    networks:
      - eso-network

  prometheus:
    image: prom/prometheus:latest
    container_name: eso-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./docker/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./data/prometheus:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    networks:
      - eso-network

  grafana:
    image: grafana/grafana:latest
    container_name: eso-grafana
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin
      GF_INSTALL_PLUGINS: grafana-piechart-panel
    volumes:
      - ./docker/monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./docker/monitoring/grafana/datasources:/etc/grafana/provisioning/datasources
      - ./data/grafana:/var/lib/grafana
    depends_on:
      - prometheus
    networks:
      - eso-network

  loki:
    image: grafana/loki:latest
    container_name: eso-loki
    ports:
      - "3100:3100"
    volumes:
      - ./docker/monitoring/loki-config.yaml:/etc/loki/local-config.yaml
      - ./data/loki:/loki
    command: -config.file=/etc/loki/local-config.yaml
    networks:
      - eso-network

  api:
    build:
      context: .
      dockerfile: docker/api/Dockerfile
    container_name: eso-api
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=development
      - POSTGRES_DSN=postgresql://postgres:postgres@postgres:5432/orchestrator
      - REDIS_DSN=redis://redis:6379/0
      - RABBITMQ_DSN=amqp://guest:guest@rabbitmq:5672/
    volumes:
      - ./src:/app/src
      - ./logs:/var/log
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy
    networks:
      - eso-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

networks:
  eso-network:
    driver: bridge
EOF

print_success "Docker Compose configuration created"

# Create Prometheus config
print_status "Creating monitoring configuration..."

mkdir -p docker/monitoring

cat > docker/monitoring/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'api'
    static_configs:
      - targets: ['api:8000']
    metrics_path: /metrics
EOF

cat > docker/monitoring/loki-config.yaml << 'EOF'
auth_enabled: false

server:
  http_listen_port: 3100

ingester:
  lifecycler:
    address: 127.0.0.1
    ring:
      kvstore:
        store: inmemory
      replication_factor: 1
    final_sleep: 0s
  chunk_idle_period: 5m
  chunk_retain_period: 30s

schema_config:
  configs:
    - from: 2020-10-24
      store: boltdb-shipper
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 24h

storage_config:
  boltdb_shipper:
    active_index_directory: /loki/index
    cache_location: /loki/cache
    shared_store: filesystem
  filesystem:
    directory: /loki/chunks

limits_config:
  enforce_metric_name: false
  reject_old_samples: true
  reject_old_samples_max_age: 168h

chunk_store_config:
  max_look_back_period: 0s

table_manager:
  retention_deletes_enabled: true
  retention_period: 336h
EOF

print_success "Monitoring configuration created"

# Create API Dockerfile
print_status "Creating Dockerfile for API..."

mkdir -p docker/api

cat > docker/api/Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY scripts/ ./scripts/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
EOF

print_success "Dockerfile created"

# Create initial test file
print_status "🧪 Creating initial test suite..."

mkdir -p tests/unit/api

cat > tests/unit/api/test_health.py << 'EOF'
import pytest
from fastapi.testclient import TestClient
from src.api.app import app

client = TestClient(app)

def test_health_check():
    """Test the health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_readiness_check():
    """Test the readiness check endpoint"""
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"

def test_metrics_endpoint():
    """Test the metrics endpoint"""
    response = client.get("/metrics")
    assert response.status_code == 200
EOF

print_success "Initial test created"

# Create simple API app to test
print_status "Creating minimal API application..."

mkdir -p src/api

cat > src/api/app.py << 'EOF'
from fastapi import FastAPI, Response
from prometheus_client import generate_latest, REGISTRY
import time
import uuid

app = FastAPI(title="Enterprise Security Orchestrator", version="1.0.0")

@app.get("/")
async def root():
    return {
        "service": "Enterprise Security Orchestrator",
        "version": "1.0.0",
        "status": "operational"
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": time.time()}

@app.get("/ready")
async |ready():
    return {"status": "ready", "timestamp": time.time()}

@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(REGISTRY), media_type="text/plain")

@app.get("/api/v1/execute")
async def execute():
    process_id = f"proc_{uuid.uuid4().hex[:12]}"
    return {
        "process_id": process_id,
        "status": "pending",
        "message": "Execution started"
    }
EOF

print_success "Minimal API application created"

# Create pytest configuration
cat > pytest.ini << 'EOF'
[pytest]
asyncio_mode = auto
pythonpath = src
testpaths = tests
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow tests
    performance: Performance tests
EOF

# Create README
print_status "📚 Creating README..."

cat > README.md << 'EOF'
# Enterprise Security Orchestrator

A comprehensive security orchestration platform with AI/ML capabilities.

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Docker & Docker Compose
- Git

### Installation

1. Clone and setup:

git clone <repository>
cd enterprise-security-orchestrator
chmod +x setup.sh
./setup.sh

2. Start services:

docker-compose up -d

3. Run tests:

pytest tests/ -v

4. Access the API:

curl http://localhost:8000

🏗️ Architecture
The platform consists of 7 integrated layers:

API Layer - FastAPI with enterprise features

Scheduler & Planning - DAG-based execution planning

Orchestration - Agent-based task execution

Observability - Monitoring, tracing, logging

Security & Compliance - RBAC, audit, compliance

AI/ML Enhancement - Predictive analytics

Production Readiness - High availability, DR

🧪 Testing
Run different test categories:

# Unit tests
pytest tests/unit -v

# Integration tests
pytest tests/integration -v

# Performance tests
locust -f tests/performance/locustfile.py

# Security tests
bandit -r src/
safety check

📊 Monitoring
Access monitoring tools:

API: http://localhost:8000

Prometheus: http://localhost:9090

Grafana: http://localhost:3000 (admin/admin)

RabbitMQ: http://localhost:15672 (guest/guest)

🔧 Configuration
Environment variables are stored in .env. For production, use:

ENVIRONMENT=production
DEBUG=false
# Add production settings...

📚 Documentation
Full documentation available in /docs:

Architecture

API Reference

Deployment Guide

Operations Guide

✅ First-Time Setup Checklist
Run ./setup.sh

Start Docker services: docker-compose up -d

Run tests: pytest tests/ -v

Access API: curl http://localhost:8000

Check monitoring: http://localhost:3000

Create first user: python scripts/create_user.py

Generate API key: python scripts/generate_api_key.py

Run example scan: python examples/basic_scan.py

🆘 Troubleshooting
Common issues and solutions in docs/runbooks.
EOF

print_success "README created"

Create helper scripts
print_status "Creating helper scripts..."

mkdir -p scripts

Create script to start everything
cat > scripts/start.sh << 'EOF'
#!/bin/bash
echo "🚀 Starting Enterprise Security Orchestrator..."

Start Docker services
docker-compose up -d

Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 10

Activate virtual environment
source venv/bin/activate

Run database migrations
alembic upgrade head

Start API in background
uvicorn src.api.app:app --reload --port 8000 &

echo "✅ All services started"
echo "📊 API: http://localhost:8000"
echo "📈 Prometheus: http://localhost:9090"
echo "📉 Grafana: http://localhost:3000"
EOF
chmod +x scripts/start.sh

Create script to run all tests
cat > scripts/test.sh << 'EOF'
#!/bin/bash
echo "🧪 Running all tests..."

source venv/bin/activate

Unit tests
echo "Running unit tests..."
pytest tests/unit -v --cov=src --cov-report=html

Integration tests
echo "Running integration tests..."
pytest tests/integration -v

Security tests
echo "Running security tests..."
bandit -r src -f html -o reports/security.html
safety check --full-report

Performance tests (if requested)
if [ "$1" == "--performance" ]; then
echo "Running performance tests..."
locust -f tests/performance/locustfile.py --headless -u 100 -r 10 --run-time 1m --host=http://localhost:8000
fi

echo "✅ Tests completed. Reports available in ./reports/"
EOF
chmod +x scripts/test.sh

Create script to generate test data
cat > scripts/generate_test_data.py << 'EOF'
#!/usr/bin/env python3
"""Generate test data for the orchestrator"""

import asyncio
import random
import uuid
from datetime import datetime, timedelta

async def generate_users(count=10):
"""Generate test users"""
users = []
for i in range(count):
users.append({
"id": f"user_{uuid.uuid4().hex[:8]}",
"email": f"user{i}@example.com",
"tenant_id": f"tenant_{random.choice(['a','b','c'])}",
"created_at": datetime.utcnow().isoformat()
})
return users

async def generate_executions(count=100):
"""Generate test executions"""
executions = []
statuses = ["completed", "failed", "running", "pending"]

for i in range(count):
created_at = datetime.utcnow() - timedelta(days=random.randint(0, 30))
executions.append({
"id": f"exec_{uuid.uuid4().hex[:12]}",
"goal": f"Scan target{i}.com",
"status": random.choice(statuses),
"created_at": created_at.isoformat(),
"completed_at": (created_at + timedelta(minutes=random.randint(1, 60))).isoformat() if random.random() > 0.3 else None,
"tasks": random.randint(1, 20),
"cost": round(random.uniform(0.01, 5.0), 4)
})
return executions

async def main():
print("Generating test data...")

users = await generate_users(10)
executions = await generate_executions(100)

print(f"Generated {len(users)} users")
print(f"Generated {len(executions)} executions")

Save to file
import json
with open("tests/test_data.json", "w") as f:
json.dump({
"users": users,
"executions": executions
}, f, indent=2)

print("Test data saved to tests/test_data.json")

if name == "main":
asyncio.run(main())
EOF
chmod +x scripts/generate_test_data.py

Create example usage script
cat > examples/basic_scan.py << 'EOF'
#!/usr/bin/env python3
"""Example: Basic security scan using the orchestrator"""

import asyncio
import httpx
import json

async def execute_scan(goal: str, target: str):
"""Execute a security scan"""

async with httpx.AsyncClient() as client:

Submit scan request
response = await client.post(
"http://localhost:8000/api/v1/execute",
json={
"goal": goal,
"target": target,
"priority": "high",
"mode": "sync"
}
)

if response.status_code != 202:
print(f"Error: {response.text}")
return

result = response.json()
process_id = result["process_id"]
print(f"Scan started with process ID: {process_id}")

Poll for status
while True:
status_response = await client.get(
f"http://localhost:8000/api/v1/status/{process_id}"
)

if status_response.status_code != 200:
break

status = status_response.json()
print(f"Status: {status['status']} - Progress: {status.get('progress', 0)}%")

if status['status'] in ['completed', 'failed', 'cancelled']:
break

await asyncio.sleep(2)

Get final results
if status['status'] == 'completed':
print("\n✅ Scan completed successfully!")
print(json.dumps(status.get('results', {}), indent=2))
else:
print(f"\n❌ Scan failed: {status.get('error', 'Unknown error')}")

async def main():
await execute_scan(
goal="Scan example.com for open ports and vulnerabilities",
target="example.com"
)

if name == "main":
asyncio.run(main())
EOF

Create .gitignore
cat > .gitignore << 'EOF'

Python
pycache/
*.py[cod]
*.so
.Python
venv/
env/
ENV/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

Virtual Environment
venv/
env/
ENV/

IDE
.vscode/
.idea/
*.swp
*.swo
*~

Project specific
logs/
data/
*.db
*.sqlite3
.coverage
htmlcov/
.pytest_cache/
.mypy_cache/
.ruff_cache/
reports/

Environment
.env
.env.local
.env.*.local

Docker
*.pid
*.sock

Test reports
test-results/
performance-results/
EOF

Create initial database migration
mkdir -p alembic
cat > alembic.ini << 'EOF'
[alembic]
script_location = alembic
prepend_sys_path = .
version_path_separator =
sqlalchemy.url = postgresql://postgres:postgres@localhost:5432/orchestrator

[post_write_hooks]
hooks = black
black.type = console_scripts
black.entrypoint = black
black.options = -l 88

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
EOF

Create initial migration
mkdir -p alembic/versions
cat > alembic/versions/001_initial.py << 'EOF'
"""initial migration

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
op.create_table(
'users',
sa.Column('id', sa.String(36), primary_key=True),
sa.Column('email', sa.String(255), nullable=False, unique=True),
sa.Column('hashed_password', sa.String(255), nullable=False),
sa.Column('full_name', sa.String(255)),
sa.Column('tenant_id', sa.String(36), nullable=False),
sa.Column('is_active', sa.Boolean(), default=True),
sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
sa.Column('updated_at', sa.DateTime(), onupdate=sa.func.now())
)

op.create_table(
'executions',
sa.Column('id', sa.String(36), primary_key=True),
sa.Column('process_id', sa.String(36), nullable=False, unique=True),
sa.Column('goal', sa.Text(), nullable=False),
sa.Column('target', sa.String(255)),
sa.Column('status', sa.String(50), nullable=False),
sa.Column('user_id', sa.String(36)),
sa.Column('tenant_id', sa.String(36), nullable=False),
sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
sa.Column('completed_at', sa.DateTime()),
sa.Column('results', sa.JSON())
)

def downgrade():
op.drop_table('executions')
op.drop_table('users')
EOF

print_success "Helper scripts created"

Make all scripts executable
find scripts -name "*.sh" -exec chmod +x {} ;

Initialize git and create first commit
print_status "📦 Creating initial git commit..."
git add .
git commit -m "Initial commit: Enterprise Security Orchestrator" > /dev/null 2>&1
print_success "Git repository initialized and committed"

Final summary
echo ""
echo "🎉 ${GREEN}Setup Complete!${NC}"
echo "=================================================="
echo ""
echo "Next steps:"
echo "1. ${YELLOW}Start the services:${NC}"
echo " cd enterprise-security-orchestrator"
echo " docker-compose up -d"
echo ""
echo "2. ${YELLOW}Activate virtual environment:${NC}"
echo " source venv/bin/activate"
echo ""
echo "3. ${YELLOW}Run database migrations:${NC}"
echo " alembic upgrade head"
echo ""
echo "4. ${YELLOW}Run the tests:${NC}"
echo " pytest tests/ -v"
echo ""
echo "5. ${YELLOW}Start the API:${NC}"
echo " uvicorn src.api.app:app --reload"
echo ""
echo "6. ${YELLOW}Access the services:${NC}"
echo " - API: http://localhost:8000"
echo " - API Docs: http://localhost:8000/docs"
echo " - Prometheus: http://localhost:9090"
echo " - Grafana: http://localhost:3000 (admin/admin)"
echo " - RabbitMQ: http://localhost:15672 (guest/guest)"
echo ""
echo "7. ${YELLOW}Run example scan:${NC}"
echo " python examples/basic_scan.py"
echo ""
echo "📚 Documentation available in ./docs/"
echo ""
echo "Happy testing! 🚀"

text

## 2. Testing Strategy

Now let's create comprehensive tests for each layer:

### Unit Tests (tests/unit/test_scheduler.py)

```python
# tests/unit/test_scheduler.py

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from src.scheduler.hybrid_scheduler import HybridScheduler
from src.models.dag import DAG, TaskNode, TaskStatus, TaskType, AgentCapability

@pytest.fixture
def sample_dag():
    """Create a sample DAG for testing"""
    dag = DAG(
        goal="Test scan",
        target="example.com"
    )
    
    # Add tasks
    task1 = TaskNode(
        name="Port Scan",
        task_type=TaskType.SCAN,
        required_capabilities=[AgentCapability.PORT_SCAN],
        estimated_duration_seconds=60
    )
    dag.add_node(task1)
    
    task2 = TaskNode(
        name="Vulnerability Scan",
        task_type=TaskType.SCAN,
        required_capabilities=[AgentCapability.VULN_SCAN],
        estimated_duration_seconds=120,
        dependencies=[task1.task_id]
    )
    dag.add_node(task2)
    
    return dag

@pytest.mark.asyncio
async def test_dag_creation():
    """Test DAG creation and structure"""
    dag = DAG(goal="Test DAG", target="test.com")
    
    assert dag.goal == "Test DAG"
    assert dag.target == "test.com"
    assert dag.total_tasks == 0
    
    # Add a task
    task = TaskNode(
        name="Test Task",
        task_type=TaskType.SCAN,
        required_capabilities=[AgentCapability.PORT_SCAN]
    )
    dag.add_node(task)
    
    assert dag.total_tasks == 1
    assert task.task_id in dag.nodes

@pytest.mark.asyncio
async def test_dag_dependencies(sample_dag):
    """Test DAG dependency management"""
    dag = sample_dag
    
    # Check dependencies
    task2 = dag.nodes[list(dag.nodes.keys())[1]]
    assert len(task2.dependencies) == 1
    
    # Get execution order
    order = dag.get_execution_order()
    assert len(order) == 2  # Two levels
    assert len(order[0]) == 1  # First level: port scan
    assert len(order[1]) == 1  # Second level: vuln scan


@pytest.mark.asyncio
async def test_dag_cycle_detection(sample_dag):
    """Test cycle detection in DAG"""
    dag = sample_dag
    
    # Try to create a cycle
    task_ids = list(dag.nodes.keys())
    with pytest.raises(ValueError, match="would create a cycle"):
        dag.add_edge(task_ids[1], task_ids[0])

@pytest.mark.asyncio
async def test_task_status_transitions():
    """Test task status transitions"""
    task = TaskNode(
        name="Test",
        task_type=TaskType.SCAN,
        required_capabilities=[AgentCapability.PORT_SCAN]
    )
    
    assert task.status == TaskStatus.PENDING
    
    task.status = TaskStatus.RUNNING
    assert task.status == TaskStatus.RUNNING
    
    task.status = TaskStatus.COMPLETED
    assert task.status == TaskStatus.COMPLETED

@pytest.mark.asyncio
@patch('src.scheduler.hybrid_scheduler.PlannerAgent')
@patch('src.scheduler.hybrid_scheduler.VerifierAgent')
@patch('src.scheduler.hybrid_scheduler.MemoryService')
async def test_scheduler_initialization(mock_memory, mock_verifier, mock_planner):
    """Test scheduler initialization"""
    scheduler = HybridScheduler(
        memory_service=mock_memory,
        planner_agent=mock_planner,
        verifier_agent=mock_verifier
    )
    
    assert scheduler is not None
    assert hasattr(scheduler, 'active_executions')

@pytest.mark.asyncio
@patch('src.scheduler.hybrid_scheduler.HybridScheduler._execute_planning_phase')
async def test_schedule_execution(mock_execute, sample_dag):
    """Test scheduling an execution"""
    # Mock dependencies
    mock_memory = AsyncMock()
    mock_planner = AsyncMock()
    mock_verifier = AsyncMock()
    mock_execute.return_value = None
    
    scheduler = HybridScheduler(
        memory_service=mock_memory,
        planner_agent=mock_planner,
        verifier_agent=mock_verifier
    )
    
    result = await scheduler.schedule_execution(
        goal="Test scan",
        user_id="test_user",
        tenant_id="test_tenant"
    )
    
    assert "process_id" in result
    assert result["status"] == "pending"
    assert result["process_id"].startswith("proc_")

@pytest.mark.asyncio
async def test_concurrent_task_execution():
    """Test concurrent task execution"""
    import asyncio
    
    async def mock_task(delay):
        await asyncio.sleep(delay)
        return f"Task completed after {delay}s"
    
    # Run tasks concurrently
    tasks = [
        mock_task(0.1),
        mock_task(0.2),
        mock_task(0.3)
    ]
    
    start = datetime.utcnow()
    results = await asyncio.gather(*tasks)
    duration = (datetime.utcnow() - start).total_seconds()
    
    assert len(results) == 3
    assert duration < 0.4  # Should be near max of individual tasks, not sum

@pytest.mark.asyncio
async def test_error_handling():
    """Test error handling in async tasks"""
    
    async def failing_task():
        await asyncio.sleep(0.1)
        raise ValueError("Task failed")
    
    async def successful_task():
        await asyncio.sleep(0.1)
        return "Success"
    
    # Run mixed tasks and handle failures
    tasks = [
        successful_task(),
        failing_task(),
        successful_task()
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    assert isinstance(results[1], Exception)
    assert str(results[1]) == "Task failed"
    assert results[0] == "Success"
    assert results[2] == "Success"