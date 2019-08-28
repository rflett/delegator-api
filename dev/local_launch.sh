#!/bin/bash
eval $(aws.cmd ecr get-login --no-include-email)
docker-compose down
# docker-compose pull
docker-compose up --build
