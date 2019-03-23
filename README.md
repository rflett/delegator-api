# api

## Directory Structure

### Repo Root

- `.gitlab-ci.yml` - CI configuration
- `.API.postman_collection.json` - Postman collection for API routes
- `apiary.apib` - API Blueprint for https://backburner.docs.apiary.io/#

### deploy/
Contains scripts and configuration for deploying to ECS. Used in the CI pipeline.

### dev/
Scripts for local development, stands up the databases/redis/api etc.

### src/
Source files. This should be what you open in PyCharm.

## Development

API is a Python Flask application.

Requirements:
- Python 3.7
- pipenv (installed via pip)
- Docker

Local development setup steps
1. Install python3.7
2. Install [Docker](https://www.docker.com/get-started)
3. Install pipenv ```pip install pipenv```
4. `cd src`
5. `pipenv install`
6. `pipenv shell`
7. `./local.sh`
8. `curl localhost:5000/health`

## Full Stack Testing
1. `cd dev`
2. `./local_launch.sh`
3. `curl localhost:5000/health`
