#!/bin/bash
pipenv shell
export FLASK_ENV=development
export FLASK_APP=api
flask run --reload