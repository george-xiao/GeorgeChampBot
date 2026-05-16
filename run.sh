#!/bin/bash

CONTAINER_NAME="george_champ_bot_instance"
IMAGE_NAME="george_champ_bot"

####################################################################
# Prompt user to reuse existing or rebuild from scratch (if needed)
####################################################################
if docker ps -aq -f name=$CONTAINER_NAME | grep -q .; then
    if docker ps -q -f name=$CONTAINER_NAME | grep -q .; then
        echo "Container is running."
    else
        echo "Container exists but is stopped."
    fi

    read -p "Reuse existing container? (y/n): " choice
fi

####################################################################
# Reuse existing image + container (if prompted)
####################################################################
if [[ "$choice" =~ ^[Yy]$ ]]; then
    if ! docker ps -q -f name=$CONTAINER_NAME | grep -1 .; then
        docker start $CONTAINER_NAME
    fi
    docker logs -f $CONTAINER_NAME
    exit 0
fi

####################################################################
# Rebuild image + container from scratch (default)
####################################################################
# Cleanup previous container (if it exists)
echo "Removing container..."
docker stop $CONTAINER_NAME 2>/dev/null
docker rm $CONTAINER_NAME 2>/dev/null

# Make database directory if it doesn't exist
mkdir -p database

docker image build . --tag $IMAGE_NAME

# database directory is bound to the docker container
# This makes the database info persistent
docker container run \
    --name $CONTAINER_NAME \
    -d \
    --mount type=bind,source="$(pwd)"/database,target=/database \
    "$IMAGE_NAME"

echo "Container started. Following logs..."
docker logs -f $CONTAINER_NAME
