FROM 239304980652.dkr.ecr.ap-southeast-2.amazonaws.com/python:runtime

# env setup
ENV APP_ENV=Local
ENV AWS_DEFAULT_REGION=ap-southeast-2
ENV FLASK_ENV=production
ENV FLASK_APP=api.py

EXPOSE 5000

# app dir
WORKDIR /app


# project requirements
COPY Pipfile Pipfile.lock ./
RUN pipenv install

# copy project src
COPY . .

# version
ARG COMMIT_SHA=local
ENV COMMIT_SHA=${COMMIT_SHA}

# run
CMD ["pipenv", "run", "gunicorn", "-b", "0.0.0.0:5000", "-w", "4", "--log-level", "warning", "--access-logfile", "-", "--access-logformat", "%(h)s %(t)s %(D)s delegator-api %(r)s %(s)s", "--config", "/app/gunicorn.config", "api:app"]
