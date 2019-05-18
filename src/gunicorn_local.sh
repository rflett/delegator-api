#!/usr/bin/env bash

export APP_ENV=Local
pipenv run gunicorn -b 0.0.0.0:5000 -w 4 --log-level debug api:app
