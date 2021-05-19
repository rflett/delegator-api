#!/bin/zsh

set -e

docker-compose down
docker-compose up --build
