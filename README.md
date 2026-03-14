🏢 Enterprise Security Orchestrator (AXR)
<div align="center">
https://img.shields.io/badge/version-1.0.0-blue
https://img.shields.io/badge/python-3.11-green
https://img.shields.io/badge/FastAPI-0.104.0-teal
https://img.shields.io/badge/docker-24.0-blue
https://img.shields.io/badge/license-Proprietary-red

Enterprise-grade security orchestration platform combining LLM-based planning with isolated containerized tool execution

Features • Architecture • Quick Start • Documentation • Contributing

</div>
📋 Table of Contents
Overview

Features

Architecture

Technology Stack

Prerequisites

Quick Start

Configuration

API Reference

Docker Setup

Kubernetes Deployment

Security

Monitoring & Observability

Testing

Troubleshooting

Contributing

License

🎯 Overview
AXR (Advanced eXecution & Response) is an enterprise security orchestration platform that automates security workflows through intelligent agents. It combines the power of Large Language Models (LLMs) for planning with isolated containerized tool execution, providing a scalable, secure, and intelligent security automation solution.

graph TD
    A[User Request] --> B[API Gateway]
    B --> C[Scheduler]
    C --> D[Planner Agent]
    D --> E[Verifier Agent]
    E --> F[Agent Orchestrator]
    F --> G[Domain Agents]
    G --> H[Tool Router]
    H --> I[Worker Pool]
    I --> J[Docker Containers]
    J --> K[Security Tools]
    K --> L[Results]
    L --> A

✨ Features
🤖 Intelligent Agents
Planner Agent: Uses LLM (local/cloud) to decompose security goals into executable DAGs

Verifier Agent: Validates DAG structure, resource availability, and security policies

Scanner Agent: Performs port scanning, vulnerability scanning, and service detection

Recon Agent: Handles network reconnaissance, DNS enumeration, and host discovery

🔧 Dynamic Tool Management
Auto-discovery of tools from Docker images and YAML configurations

Dynamic worker pools with auto-scaling based on load

Tool versioning and fallback strategies

Isolated execution in Docker containers

🛡️ Enterprise Security
Multi-tenancy with complete isolation (data, compute, network)

RBAC/ABAC authorization

Audit logging of all actions

Secret management and encryption

Compliance tracking (SOC2, GDPR, HIPAA, PCI-DSS)

📊 Observability
OpenTelemetry integration for distributed tracing

Prometheus metrics

Grafana dashboards

Loki log aggregation

Jaeger tracing

🔄 Recovery & Resilience
Circuit breaker pattern

Retry with exponential backoff

Fallback strategies

Self-healing worker pools

Escalation management

🧠 AI/ML Capabilities
Vulnerability prediction

Risk scoring

Resource prediction

Tool recommendation

Parameter optimization

Anomaly detection

🏗 Architecture
Container Architecture
text
┌─────────────────────────────────────────────────┐
│              API CONTAINER (Light)              │
│  • FastAPI                                      │
│  • Planner Agent (LLM client only)              │
│  • Scheduler                                    │
│  • Tool Router                                  │
│  Size: ~200-300MB                               │
└─────────────────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│ ML Worker     │  │ LLM Worker    │  │ Security      │
│ Container     │  │ Container     │  │ Worker        │
│               │  │               │  │ Containers    │
│ • TensorFlow  │  │ • Local LLM   │  │ • nmap        │
│ • XGBoost     │  │ • LangChain   │  │ • nuclei      │
│ • scikit-learn│  │ • Transformers│  │ • sqlmap      │
│ • MLflow      │  │               │  │ • gobuster    │
│ Size: ~3-4GB  │  │ Size: ~4-8GB  │  │ Size: ~200MB  │
└───────────────┘  └───────────────┘  └───────────────┘
Security Layers
text
┌─────────────────────────────────────────────────────────────┐
│                    LAYER 1: NETWORK ISOLATION               │
│  • Each service in separate network segment                 │
│  • API can only talk to workers, not directly to internet   │
│  • Workers have NO internet access (air-gapped)             │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                    LAYER 2: CONTAINER SECURITY              │
│  • All containers run as NON-ROOT users                     │
│  • Read-only root filesystem                                │
│  • Dropped all Linux capabilities                           │
│  • Seccomp profiles to block syscalls                       │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                    LAYER 3: IMAGE SECURITY                  │
│  • Distroless images (no shell, no package manager)         │
│  • Regular vulnerability scanning (Trivy, Grype)            │
│  • Signed images with Cosign                                 │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                    LAYER 4: RUNTIME SECURITY                │
│  • Falco for runtime threat detection                       │
│  • Audit logging of all actions                             │
│  • Activity monitoring and alerting                         │
└─────────────────────────────────────────────────────────────┘
🛠 Technology Stack
Core
Python 3.11+ - Primary language

FastAPI - Web framework

Pydantic - Data validation

Uvicorn - ASGI server

AI/ML
LangChain - LLM orchestration

Transformers - Hugging Face models

TensorFlow/PyTorch - Deep learning

scikit-learn - Classical ML

XGBoost - Gradient boosting

MLflow - Model registry

Infrastructure
Docker - Containerization

Kubernetes - Orchestration (optional)

Redis - Caching & rate limiting

PostgreSQL - Primary database

RabbitMQ - Message queue

Monitoring
OpenTelemetry - Distributed tracing

Prometheus - Metrics collection

Grafana - Visualization

Loki - Log aggregation

Jaeger - Tracing

Security
Falco - Runtime security

Trivy - Vulnerability scanning

Cosign - Image signing

OAuth2/JWT - Authentication

📋 Prerequisites
System Requirements
OS: Linux (Ubuntu 20.04+ recommended), macOS, or WSL2

CPU: 4+ cores

RAM: 8GB minimum, 16GB recommended

Disk: 20GB free space

Docker: 24.0+

Python: 3.11+

Required Software
bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Python 3.11
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev

# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Install Ollama (for local LLM)
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull qwen2.5:3b
🚀 Quick Start
1. Clone Repository
bash
git clone https://github.com/yourusername/axr.git
cd axr
2. Set Up Virtual Environment
bash
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
3. Install Dependencies
bash
# Install Poetry if not already installed
pip install poetry

# Install all dependencies
poetry install

# Install development dependencies (optional)
poetry install --with dev
4. Configure Environment
bash
cp .env.example .env
# Edit .env with your configuration
nano .env
5. Build Docker Images
bash
# Build base worker image
docker build -t eso-worker-base:latest -f docker/workers/base/Dockerfile .

# Build security tool images
./scripts/build-workers.sh
6. Initialize Database
bash
# Run database migrations
alembic upgrade head
7. Start the API
bash
# Development mode with auto-reload
uvicorn src.api.app:app --reload

# Production mode
uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --workers 4
8. Test the API
bash
# Health check
curl http://localhost:8000/api/v1/health

# Run a scan
curl -X POST http://localhost:8000/api/v1/hybrid/execute \
  -H "Content-Type: application/json" \
  -d '{"goal": "Scan example.com for open ports"}'

# Check status
curl http://localhost:8000/api/v1/hybrid/status/PROCESS_ID
⚙️ Configuration
Environment Variables
Variable	Description	Default
ENVIRONMENT	Runtime environment	development
API_VERSION	API version	v1
API_PREFIX	API URL prefix	/api
API_PORT	API port	8000
API_HOST	API host	0.0.0.0
WORKERS	Number of worker processes	4
JWT_SECRET_KEY	JWT signing key	Required
POSTGRES_DSN	PostgreSQL connection string	Required
REDIS_DSN	Redis connection string	Required
LLM_PROVIDER	LLM provider (local/openai/anthropic)	local
OPENAI_API_KEY	OpenAI API key	Optional
ANTHROPIC_API_KEY	Anthropic API key	Optional
LOCAL_LLM_URL	Local LLM URL	http://localhost:11434
LOCAL_LLM_MODEL	Local LLM model	qwen2.5:3b
Configuration Files
.env - Main environment configuration

alembic.ini - Database migration configuration

pyproject.toml - Python dependencies

pytest.ini - Test configuration

📚 API Reference
Endpoints
Hybrid Execution
Method	Endpoint	Description
POST	/api/v1/hybrid/execute	Execute a security goal
GET	/api/v1/hybrid/status/{process_id}	Get execution status
GET	/api/v1/hybrid/list	List all executions
POST	/api/v1/hybrid/schedule	Schedule recurring execution
POST	/api/v1/hybrid/batch	Batch execute multiple goals
DELETE	/api/v1/hybrid/cancel/{process_id}	Cancel execution
Health & Metrics
Method	Endpoint	Description
GET	/api/v1/health	Health check
GET	/api/v1/metrics	Prometheus metrics
GET	/api/v1/admin/status	Admin status
GET	/api/v1/admin/health	Admin health
Example Request
json
POST /api/v1/hybrid/execute
{
  "goal": "Scan example.com for vulnerabilities",
  "target": "example.com",
  "priority": "high",
  "mode": "async",
  "budget_limit": 100.0,
  "tags": {
    "department": "security",
    "project": "pentest-q1"
  },
  "webhook_url": "https://webhook.example.com/callback",
  "parameters": {
    "scan_depth": "standard",
    "include_subdomains": true
  }
}
Example Response
json
{
  "process_id": "proc_abc123def456",
  "status": "pending",
  "goal": "Scan example.com for vulnerabilities",
  "target": "example.com",
  "created_at": "2024-01-01T00:00:00Z"
}
🐳 Docker Setup
Building Images
bash
# Build all images
./scripts/build-all.sh

# Build specific image
docker build -t eso-worker-nmap:latest -f docker/workers/security/nmap/Dockerfile .

# List built images
docker images | grep eso-worker
Running with Docker Compose
bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
Worker Images
Tool	Image	Size
Base	eso-worker-base:latest	~15MB
Nmap	eso-worker-nmap:latest	~32MB
Nuclei	eso-worker-nuclei:latest	~87MB
SQLMap	eso-worker-sqlmap:latest	~104MB
Gobuster	eso-worker-gobuster:latest	~23MB
☸️ Kubernetes Deployment
Prerequisites
Kubernetes 1.24+

kubectl configured

Ingress controller (optional)

Deploy to Kubernetes
bash
# Create namespace
kubectl create namespace security

# Apply ConfigMap and Secrets
kubectl apply -f kubernetes/configmap.yaml
kubectl apply -f kubernetes/secrets.yaml

# Deploy API
kubectl apply -f kubernetes/api-deployment.yaml

# Deploy workers
kubectl apply -f kubernetes/ml-worker-deployment.yaml
kubectl apply -f kubernetes/llm-worker-deployment.yaml
kubectl apply -f kubernetes/security-worker-deployment.yaml

# Check status
kubectl -n security get pods
kubectl -n security get services
Scale Deployment
bash
# Scale API
kubectl -n security scale deployment/security-orchestrator-api --replicas=5

# Auto-scaling is configured in HPA
kubectl -n security get hpa
🔒 Security
Security Features
Multi-tenancy Isolation

Data isolation per tenant

Compute isolation

Network isolation

Authentication & Authorization

JWT tokens

API keys

RBAC/ABAC policies

Data Protection

Field-level encryption

Secrets management

Data masking

Compliance

SOC2

GDPR

HIPAA

PCI-DSS

Security Best Practices
bash
# Scan images for vulnerabilities
trivy image eso-worker-nmap:latest

# Sign images (production)
cosign sign --key cosign.key eso-worker-nmap:latest

# Run runtime security
docker run -d --name falco -v /var/run/docker.sock:/host/var/run/docker.sock falcosecurity/falco
📊 Monitoring & Observability
Metrics Endpoint
bash
# Prometheus metrics
curl http://localhost:8000/api/v1/metrics
Grafana Dashboards
Access Grafana at http://localhost:3000 (default credentials: admin/admin)

Available dashboards:

API Dashboard - Request rates, latencies, errors

Worker Dashboard - Container status, resource usage

Execution Dashboard - Task success rates, durations

Security Dashboard - Audit logs, compliance status

Logging
bash
# View logs
docker-compose logs -f api

# Structured logs in JSON format
tail -f logs/audit.log | jq '.'
Tracing
Jaeger UI available at http://localhost:16686

🧪 Testing
Unit Tests
bash
# Run all unit tests
pytest tests/unit/ -v

# Run specific test file
pytest tests/unit/autonomous/test_adaptive_scanner.py -v

# Run with coverage
pytest --cov=src tests/ --cov-report=html
Integration Tests
bash
# Run integration tests
pytest tests/integration/ -v

# Run performance tests
pytest tests/performance/ -v
Test Runner Script
bash
# Interactive test runner
./tests/run_all_tests.sh

# Run all tests
python3 run_all_tests.py
🔍 Troubleshooting
Common Issues
Workers not staying running
bash
# Check container status
docker ps -a | grep worker

# View logs
docker logs worker_nmap_xxx

# Restart workers
docker restart worker_nmap_xxx
API won't start
bash
# Check for port conflicts
sudo lsof -i :8000

# Verify environment variables
python3 -c "from src.core.config import get_settings; print(get_settings().dict())"

# Check database connection
psql $POSTGRES_DSN -c "SELECT 1"
LLM not responding
bash
# Check Ollama status
ollama list
ollama ps

# Test LLM directly
curl http://localhost:11434/api/generate -d '{"model": "qwen2.5:3b", "prompt": "Hello"}'
Docker permission denied
bash
# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
Debug Mode
bash
# Enable debug logging
export LOG_LEVEL=DEBUG
uvicorn src.api.app:app --reload --log-level debug
🤝 Contributing
Development Workflow
Fork the repository

Create a feature branch

bash
git checkout -b feature/amazing-feature
Install development dependencies

bash
poetry install --with dev
pre-commit install
Make your changes

Run tests

bash
pytest tests/ -v
Commit with conventional commits

bash
git commit -m "feat: add amazing feature"
Push and create Pull Request

Code Style
Black for formatting

isort for import sorting

flake8 for linting

mypy for type checking

bash
# Format code
black src/ tests/
isort src/ tests/

# Run linters
flake8 src/ tests/
mypy src/
Branch Strategy
main - Production-ready code

develop - Development branch

feature/* - New features

bugfix/* - Bug fixes

release/* - Release preparation

📄 License
Copyright © 2024 [Your Company]. All rights reserved.

This software is proprietary and confidential. Unauthorized copying, distribution, or use of this software is strictly prohibited.

🙏 Acknowledgments
FastAPI team for the amazing framework

Docker for containerization

Kubernetes for orchestration

All open-source contributors whose libraries made this possible

<div align="center"> <sub>Built with ❤️ by the Security Team</sub> <br> <sub>© 2024 Your Company. All rights reserved.</sub> </div>
