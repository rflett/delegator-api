FROM python:3.7-alpine

ARG FLASK_ENV=production
ENV FLASK_ENV=${FLASK_ENV}

ARG APP_ENV=Staging
ENV APP_ENV=${APP_ENV}

ENV FLASK_APP=api.py

RUN mkdir /api
COPY api.py Pipfile config.py /api/
COPY app /api/app
WORKDIR /api

RUN apk update && apk add postgresql-dev build-base
RUN pip install pipenv && pipenv install

EXPOSE 5000

CMD ["pipenv", "run", "gunicorn", "-b", "0.0.0.0:5000", "-w", "4", "api:app"]
