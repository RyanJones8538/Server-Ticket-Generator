#!/bin/sh
set -e

envsubst '${SERVER_ID} ${CLUSTER} ${MESSAGE}' \
  < /etc/nginx/templates/default.conf.template \
  > /etc/nginx/conf.d/default.conf

nginx -g 'daemon off;' &
NGINX_PID=$!
sleep 1

# Repeatedly kill nginx worker processes (children of the master).
# The master automatically respawns them, creating a visible crash loop in ps aux.
(while kill -0 $NGINX_PID 2>/dev/null; do
    sleep 8
    for pid in $(ls /proc/ 2>/dev/null); do
        [ -f /proc/$pid/stat ] || continue
        ppid=$(awk '{print $4}' /proc/$pid/stat 2>/dev/null)
        [ "$ppid" = "$NGINX_PID" ] && kill "$pid" 2>/dev/null || true
    done
done) &

wait $NGINX_PID
