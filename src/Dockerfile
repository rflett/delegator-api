FROM 008492826001.dkr.ecr.ap-southeast-2.amazonaws.com/python:latest

RUN mkdir /api
WORKDIR /api

COPY Pipfile /api/
RUN pipenv install

ARG COMMIT_SHA=local
ENV COMMIT_SHA=${COMMIT_SHA}

ARG FLASK_ENV=production
ENV FLASK_ENV=${FLASK_ENV}

ARG APP_ENV=Staging
ENV APP_ENV=${APP_ENV}

ENV FLASK_APP=api.py
ENV AWS_DEFAULT_REGION=ap-southeast-2

EXPOSE 5000

COPY api.py config.py /api/
COPY app /api/app

CMD ["pipenv", "run", "gunicorn", "-b", "0.0.0.0:5000", "-w", "4", "--log-level", "debug", "api:app"]
