# api

API is a Python Flask application.

Requirements:
- Python 3.7
- pipenv (installed via pip)
- Docker

Local development setup steps
1. Install python3.7
2. Install [Docker](https://www.docker.com/get-started)
3. Install pipenv ```pip install pipenv```

Now that your environment is set up, run `pipenv install` in the project root to setup your virtualenv and requirements.

## Local development with hot reload
To run the api with hot reloading just run

``` pipenv run flask run --reload ``` 

in the project root. Then visit or curl ``` localhost:5000 ```. The Flask server will update when files are changed.

## Build and run container stack
cd to the dev folder then

``` bash local_launch.sh ```

or

``` cmd local_launch.sh ```

Alternatively, just run ``` docker compose up --build ``` in the dev folder. Either way this will build the API docker image, and then run the API image along side an NGINX container. This will provide the most accurate replication of the production environment. 

## Local development vs production deployment
Locally, development is best supported when executing ``` flask run ``` with hot reloading. This runs the flask development server which is not ideal in production.. 

Instead, in production the ``` api.py ``` file is executed using gunicorn, which is a production ready HTTP WSGI server.
