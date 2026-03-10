#!/bin/bash
# docker/workers/nmap/entrypoint.sh

set -e

echo "Nmap Worker Container Started"
echo "Worker ID: ${WORKER_ID}"
echo "Tool: ${TOOL_NAME}"

# Process command
if [ $# -eq 0 ]; then
    # No arguments, start listening for jobs
    echo "Starting worker in listening mode..."
    
    # In production, this would connect to message queue
    # For now, just sleep
    while true; do
        sleep 60
    done
else
    # Execute nmap with arguments
    echo "Executing: nmap $@"
    nmap "$@"
fi