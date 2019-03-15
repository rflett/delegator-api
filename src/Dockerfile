FROM 008492826001.dkr.ecr.ap-southeast-2.amazonaws.com/python:latest

ARG COMMIT_SHA=local
ENV COMMIT_SHA=${COMMIT_SHA}

ARG FLASK_ENV=production
ENV FLASK_ENV=${FLASK_ENV}

ARG APP_ENV=Staging
ENV APP_ENV=${APP_ENV}

ENV FLASK_APP=api.py

RUN mkdir /api
COPY api.py Pipfile config.py /api/
COPY app /api/app
WORKDIR /api

RUN pipenv install

EXPOSE 5000

CMD ["pipenv", "run", "gunicorn", "-b", "0.0.0.0:5000", "-w", "4", "--log-level", "debug", "api:app"]
