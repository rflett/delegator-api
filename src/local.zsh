#!/bin/zsh

export FLASK_ENV=development
export FLASK_APP=api
export APP_ENV=Local
export AWS_DEFAULT_PROFILE=production
flask run --reload --port 5000 --host 127.0.0.1
