#!/bin/sh
set -e

# Remove Docker's log symlinks so nginx writes to a real file on disk
rm -f /var/log/nginx/error.log /var/log/nginx/access.log

# Quoted heredoc — $hostname and $nginx_version are NOT expanded by the shell
# and pass through literally for nginx to resolve at request time
cat > /tmp/nginx.tmpl << 'TMPL'
upstream app_backend {
    server 127.0.0.1:3000;
}

server {
    listen 80;
    server_name _;
    default_type application/json;

    error_log /var/log/nginx/error.log warn;
    access_log /var/log/nginx/access.log;

    location /status {
        return 200 '{"server_id":"${SERVER_ID}","cluster":"${CLUSTER}","hostname":"$hostname","app_status":"ok","message":"${MESSAGE}","nginx":{"version":"$nginx_version","status":"running"},"ports":{"http":80}}';
    }

    location /app {
        proxy_pass http://app_backend;
        proxy_connect_timeout 2s;
        proxy_read_timeout 2s;
        proxy_send_timeout 2s;
    }
}
TMPL

# Substitute only our env vars; leave $hostname and $nginx_version for nginx
envsubst '${SERVER_ID} ${CLUSTER} ${MESSAGE}' < /tmp/nginx.tmpl > /etc/nginx/conf.d/default.conf
rm /tmp/nginx.tmpl

nginx -g 'daemon off;' &
NGINX_PID=$!
sleep 2

# Hit the dead upstream 15 times to pre-fill the error log with connection failures
for i in $(seq 1 15); do
    wget -q -O /dev/null http://localhost/app 2>/dev/null || true
done

wait $NGINX_PID
