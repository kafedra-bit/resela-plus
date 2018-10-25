#!/usr/bin/env bash

service apache2 start
service postfix start
echo "<CIP> controller" >> /etc/hosts
echo "<MIP>  mikrotik" >> /etc/hosts
tail -f /var/log/apache2/error.log
