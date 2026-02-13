#!/bin/bash

# Check if container exists (running or stopped)
if ! sudo docker ps -a -q -f name=george_champ_bot_instance | grep -q .; then
    echo "Container 'george_champ_bot_instance' does not exist."
    exit 1
fi

echo "Stopping container..."
sudo docker stop george_champ_bot_instance

echo "Removing container..."
sudo docker rm george_champ_bot_instance

echo "Container stopped and removed successfully."
