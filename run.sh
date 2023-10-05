#!/bin/bash

# Make database directory if it doesn't exist
mkdir --parents database

sudo docker image build . --tag george_champ_bot

# database directory is bound to the docker container
# This makes the database info persistent 
sudo docker container run \
    --name george_champ_bot_instance \
    --rm \
    --mount type=bind,source="$(pwd)"/database,target=/database \
    george_champ_bot
