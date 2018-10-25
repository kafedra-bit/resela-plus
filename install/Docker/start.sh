#!/usr/bin/env bash

if [ "$(id -u)" != "0" ]; then
        echo "Must be root"
        exit 1
fi

docker run \
    -p 80:80 \
    -p 443:443 \
    --mount type=bind,src=/var/www/resela,dst=/var/www/resela \
    --mount type=bind,src=/var/log/apache2,dst=/var/log/apache2 \
    --mount type=bind,src=/etc/letsencrypt,dst=/etc/letsencrypt \
    -tdi resela

echo "Resela successfully started on port 80/443"