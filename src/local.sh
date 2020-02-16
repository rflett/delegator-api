#!/bin/bash
export FLASK_ENV=development
export FLASK_APP=api
export APP_ENV=Local
#export AWS_DEFAULT_PROFILE=production
export MOCK_AWS=true
flask run --reload
