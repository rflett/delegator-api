#!/bin/bash
export FLASK_ENV=production
export FLASK_APP=api
export APP_ENV=Local
#export AWS_DEFAULT_PROFILE=production
export MOCK_AWS=true
export MOCK_SERVICES=true
flask run --reload
