FROM python:3.7-alpine

ENV FLASK_APP=api.py
ENV APP_ENV=Local

RUN mkdir /api
COPY api.py Pipfile config.py /api/
COPY app /api/app
WORKDIR /api

RUN pip install pipenv && pipenv install

EXPOSE 5000

CMD ["pipenv", "run", "gunicorn", "-b", "0.0.0.0:5000", "-w", "4", "api:app"]
