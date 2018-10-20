#!/usr/bin/env bash

# Author Fredrik Johansson, Annika Hansson
# Openstack version Mitaka
# Ubuntu Server version 16.04 LTS

# Load the variables containing user input
. controllerInstall

echo 'Configuring glance database...'
mysql -u root -p${mysqlDBPass} -e "CREATE DATABASE glance;"
mysql -u root -p${mysqlDBPass} -e "GRANT ALL PRIVILEGES ON glance.* TO 'glance'@'localhost' IDENTIFIED BY '${glanceDBPass}';"
mysql -u root -p${mysqlDBPass} -e "GRANT ALL PRIVILEGES ON glance.* TO 'glance'@'%' IDENTIFIED BY '${glanceDBPass}';"

echo 'Creating glance user, role and service entity...'
# load admin env. variable
. admin-openrc
openstack user create --domain default --password ${glancePass} glance
openstack role add --project service --user glance admin
openstack service create --name glance --description "OpenStack Image" image

echo 'Creating image service api endpoints...'
openstack endpoint create --region RegionOne image public http://controller:9292
openstack endpoint create --region RegionOne image internal http://controller:9292
openstack endpoint create --region RegionOne image admin http://controller:9292

echo 'Installing glance...'
apt-get -y -q install glance

echo 'Configuring /etc/glance/glance-api.conf...'
#comment out all lines in section
sed -i '/^\[keystone_authtoken\]/,/^\[.*\]/{/^\[.*\]/!{s/^/#/}}' ${glanceAPIConfPath}
#remove all comments
#sed -i '/^#/d' ${glanceAPIConfPath}
#sed -i '/^\s*$/d' ${glanceAPIConfPath}
#sed -i '1!{/^\[.*\]/{s/^/\n/}}' ${glanceAPIConfPath}

cat > /tmp/glanceConfig << END_OF_CONF
connection = mysql+pymysql://glance:${glanceDBPass}@controller/glance
END_OF_CONF
sed --in-place -e "/^\[database\]/r /tmp/glanceConfig" ${glanceAPIConfPath}

cat > /tmp/glanceConfig << END_OF_CONF
auth_uri = http://controller:5000
auth_url = http://controller:35357
memcached_servers = controller:11211
auth_type = password
project_domain_name = default
user_domain_name = default
project_name = service
username = glance
password = ${glancePass}
END_OF_CONF
sed --in-place -e "/^\[keystone_authtoken\]/r /tmp/glanceConfig" ${glanceAPIConfPath}

cat > /tmp/glanceConfig << END_OF_CONF
flavor = keystone
END_OF_CONF
sed --in-place -e "/^\[paste_deploy\]/r /tmp/glanceConfig" ${glanceAPIConfPath}

cat > /tmp/glanceConfig << END_OF_CONF
stores = file,http
default_store = file
filesystem_store_datadir = /var/lib/glance/images/
END_OF_CONF
sed --in-place -e "/^\[glance_store\]/r /tmp/glanceConfig" ${glanceAPIConfPath}

echo "Configuring /etc/glance/glance-registry.conf..."
# Comments out all lines in section keystone_authtoken
sed -i "/^\[keystone_authtoken\]/,/^\[.*\]/{/^\[.*\]/!{s/^/#/}}" ${glanceRegistryConfPath}

cat > /tmp/glanceConfig << END_OF_CONF
connection = mysql+pymysql://glance:${glanceDBPass}@controller/glance
END_OF_CONF
sed --in-place -e "/^\[database\]/r /tmp/glanceConfig" ${glanceRegistryConfPath}

cat > /tmp/glanceConfig << END_OF_CONF
auth_uri = http://controller:5000
auth_url = http://controller:35357
memcached_servers = controller:11211
auth_type = password
project_domain_name = default
user_domain_name = default
project_name = service
username = glance
password = ${glancePass}
END_OF_CONF
sed --in-place -e "/^\[keystone_authtoken\]/r /tmp/glanceConfig" ${glanceRegistryConfPath}

cat > /tmp/glanceConfig << END_OF_CONF
flavor = keystone
END_OF_CONF
sed --in-place -e "/^\[paste_deploy\]/r /tmp/glanceConfig" ${glanceRegistryConfPath}

echo 'Populating the image service database...'
su -s /bin/sh -c "glance-manage db_sync" glance

echo 'Restarting glance registry...'
service glance-registry restart
echo 'Restarting glance api...'
service glance-api restart