FROM 650215746119.dkr.ecr.ap-southeast-2.amazonaws.com/python:runtime-master-8df2e914

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
RUN pipenv install --system

# copy project src
COPY . .

# version
ARG COMMIT_SHA=local
ENV COMMIT_SHA=${COMMIT_SHA}

# su
USER daemon

# run
CMD ["gunicorn", "-b", "0.0.0.0:5000", "-w", "4", "--log-level", "warning", "--access-logfile", "-", "--access-logformat", "%(h)s %(t)s %(m)s %(U)s %(s)s %(B)s %(a)s %(D)s", "--config", "/app/gunicorn.py", "api:app"]
