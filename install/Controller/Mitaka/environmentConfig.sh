#!/usr/bin/env bash

# Author Annika Hansson, Fredrik Johansson
# Openstack version Mitaka
# Ubuntu Server version 16.04 LTS

# Load the variables containing user input
. controllerInstall

echo "Enabling the OpenStack repository..."
apt-get -y -q install software-properties-common
add-apt-repository -y cloud-archive:mitaka

echo "Updating and upgrading the system..."
apt-get -y -q update && apt-get -y -q dist-upgrade

echo "Installing OpenStack client..."
apt-get -y -q install python-openstackclient

echo "Installing MariaDB and PyMySQL..."
export DEBIAN_FRONTEND="nointeractive"
debconf-set-selections <<< "mariadb-server mysql-server/root_password password ${mysqlDBPass}"
debconf-set-selections <<< "mariadb-server mysql-server/root_password_again password ${mysqlDBPass}"
apt-get -y -q install mariadb-server python-pymysql
unset DEBIAN_FRONEND

if [ $(lsb_release -rs) == "14.04" ]; then
    echo "Configuring /etc/mysql/conf.d/openstack.cnf..."
    mariaDBTmp=${mysqlConfPathU14}
else
    echo "Changing character encoding, from utf8m4 to utf8, in directory /etc/mysql/mariadb.conf.d/..."
    find /etc/mysql/mariadb.conf.d/ -type f -exec sed -i "s/utf8m4/utf8/" {} \;
    echo "Configuring /etc/mysql/mariadb.conf.d/99-openstack.cnf..."
    mariaDBTmp=${mysqlConfPathU16}
fi

cat > ${mariaDBTmp} << END_OF_CONF
[mysqld]
bind-address = ${contIP}
default-storage-engine = innodb
innodb_file_per_table
max_connections = 4096
collation-server = utf8_general_ci
character-set-server = utf8
END_OF_CONF

echo "Restarting mysql..."
service mysql restart

mysql_secure_installation

echo "Installing MongoDB..."
apt-get -y -q install mongodb-server mongodb-clients python-pymongo

echo 'Configuring /etc/mongodb.conf...'
sed -i "/^bind_ip/{s/^/#/}" ${mongoDBConfPath}
cat >> ${mongoDBConfPath} << END_OF_CONF
bind_ip = ${contIP}
smallfiles = true
END_OF_CONF

echo "Restarting mongodb..."
service mongodb stop
rm /var/lib/mongodb/journal/prealloc.*
service mongodb start

echo 'Installing and configuring rabbit MQ server...'
apt-get -y -q install rabbitmq-server
rabbitmqctl add_user openstack ${rabbitPass}
rabbitmqctl set_permissions openstack ".*" ".*" ".*"

echo 'Installing memcached...'
apt-get -y -q install memcached python-memcache

echo 'Configuring /etc/memcached.conf...'
sed -i "s/^-l 127.0.0.1/-l ${contIP}/" ${memcachedConfPath}

echo 'Restarting memcached...'
service memcached restart