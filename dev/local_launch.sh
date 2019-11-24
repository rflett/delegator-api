#!/bin/bash

set -e

eval $(aws.cmd ecr get-login --no-include-email --profile shared-services)
docker-compose down
# docker-compose pull
docker-compose up --build
