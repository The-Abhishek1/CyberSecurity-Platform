#!/bin/bash

echo "📊 Security Monitoring Dashboard"
echo "================================"
echo "Press Ctrl+C to exit"
echo ""

while true; do
    clear
    echo "🕒 $(date)"
    echo ""
    
    echo "🔒 CONTAINER SECURITY STATUS:"
    echo "-----------------------------"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Image}}" | grep -E "axr|falco"
    
    echo ""
    echo "🛡️  RUNTIME SECURITY (Last 10 Falco alerts):"
    echo "----------------------------------------"
    docker logs axr-falco --tail 10 2>/dev/null || echo "No alerts"
    
    echo ""
    echo "💻 RESOURCE USAGE:"
    echo "-----------------"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" | grep -E "axr|falco"
    
    echo ""
    echo "🌐 NETWORK ISOLATION:"
    echo "--------------------"
    docker network inspect axr_internal-net | grep -E "Subnet|Gateway" | head -2
    docker network inspect axr_scanning-net | grep -E "Subnet|Gateway" | head -2
    
    sleep 5
done