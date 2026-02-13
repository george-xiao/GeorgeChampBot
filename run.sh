#!/bin/bash

# Check if container is already running
if sudo docker ps -q -f name=george_champ_bot_instance | grep -q .; then
    echo "Container is already running. Attaching..."
    sudo docker attach george_champ_bot_instance
    exit 0
fi

# Make database directory if it doesn't exist
mkdir -p database

sudo docker image build . --tag george_champ_bot

# database directory is bound to the docker container
# This makes the database info persistent
sudo docker container run \
    --name george_champ_bot_instance \
    -d \
    --mount type=bind,source="$(pwd)"/database,target=/database \
    george_champ_bot

echo "Container started. Attaching..."
sudo docker attach george_champ_bot_instance
