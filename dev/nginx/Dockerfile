FROM nginx:1.15.8-alpine
COPY local.conf /etc/nginx/conf.d/
COPY ssl/ /etc/ssl
RUN rm -f /etc/nginx/conf.d/default.conf
