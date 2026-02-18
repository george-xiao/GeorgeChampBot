#!/bin/bash

# Check if container exists (running or stopped)
if ! docker ps -a -q -f name=george_champ_bot_instance | grep -q .; then
    echo "Container 'george_champ_bot_instance' does not exist."
    exit 1
fi

echo "Stopping container..."
docker stop george_champ_bot_instance

echo "Removing container..."
docker rm george_champ_bot_instance

echo "Container stopped and removed successfully."
