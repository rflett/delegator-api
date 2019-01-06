FROM postgres:10.5

ENV POSTGRES_USER=etemt
ENV POSTGRES_PASSWORD=etemt
ENV POSTGRES_DB=etemt

COPY sql/ /docker-entrypoint-initdb.d
