#!/bin/bash
eval $(aws ecr get-login --no-include-email)
docker-compose down
# docker-compose pull
docker-compose up --build
