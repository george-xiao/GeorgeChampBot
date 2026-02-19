#!/bin/bash

CONTAINER_NAME="george_champ_bot_instance"
IMAGE_NAME="george_champ_bot"

# Check if container is already running
if docker ps -q -f name=george_champ_bot_instance | grep -q .; then
    echo "Container is already running. Attaching..."
    docker attach "$CONTAINER_NAME"
    exit 0
fi

# Check if container exists but is stopped
if docker ps -aq -f name=^${CONTAINER_NAME}$ | grep -q .; then
    echo "Container exists but is stopped. Starting and attaching..."
    docker start "$CONTAINER_NAME"
    docker attach "$CONTAINER_NAME"
    exit 0
fi

# Make database directory if it doesn't exist
mkdir -p database

docker image build . --tag "$IMAGE_NAME"

# database directory is bound to the docker container
# This makes the database info persistent
docker container run \
    --name "$CONTAINER_NAME" \
    -d \
    --mount type=bind,source="$(pwd)"/database,target=/database \
    "$IMAGE_NAME"

echo "Container started. Attaching..."
docker attach "$CONTAINER_NAME"
