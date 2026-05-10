#!/bin/sh
set -e

envsubst '${SERVER_ID} ${CLUSTER} ${MESSAGE}' \
  < /etc/nginx/templates/default.conf.template \
  > /etc/nginx/conf.d/default.conf

nginx -g 'daemon off;' &
NGINX_PID=$!
sleep 2

# Append invalid syntax — nginx keeps serving from its loaded config,
# but nginx -t will now report a syntax error
printf '\n# corrupted entry\nserver {\n    listen 9090\n    invalid_directive\n' \
  >> /etc/nginx/conf.d/default.conf

wait $NGINX_PID
