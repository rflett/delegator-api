#!/bin/bash
eval $(aws.cmd ecr get-login --no-include-email)
docker-compose down
docker-compose pull
docker-compose build --no-cache
docker-compose up  --build
