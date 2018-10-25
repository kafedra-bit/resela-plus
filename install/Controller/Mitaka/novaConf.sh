#!/usr/bin/env bash

# Author Fredrik Johansson, Annika Hansson
# Openstack version Mitaka
# Ubuntu Server version 16.04 LTS

# Load the variables containing user input
. controllerInstall

echo 'Creating nova and nova api databases...'
mysql -u root -p${mysqlDBPass} -e "CREATE DATABASE nova_api; CREATE DATABASE nova;"
mysql -u root -p${mysqlDBPass} -e "GRANT ALL PRIVILEGES ON nova_api.* TO 'nova'@'localhost' IDENTIFIED BY '${novaDBPass}';"
mysql -u root -p${mysqlDBPass} -e "GRANT ALL PRIVILEGES ON nova_api.* TO 'nova'@'%' IDENTIFIED BY '${novaDBPass}';"
mysql -u root -p${mysqlDBPass} -e "GRANT ALL PRIVILEGES ON nova.* TO 'nova'@'localhost' IDENTIFIED BY '${novaDBPass}';"
mysql -u root -p${mysqlDBPass} -e "GRANT ALL PRIVILEGES ON nova.* TO 'nova'@'%' IDENTIFIED BY '${novaDBPass}';"

echo 'Creating nova user...'
# load admin env. variable
. admin-openrc
openstack user create --domain default --password ${novaPass} nova
openstack role add --project service --user nova admin
openstack service create --name nova --description "OpenStack Compute" compute

echo 'Creating compute service api endpoints...'
openstack endpoint create --region RegionOne compute public http://controller:8774/v2.1/%\(tenant_id\)s
openstack endpoint create --region RegionOne compute internal http://controller:8774/v2.1/%\(tenant_id\)s
openstack endpoint create --region RegionOne compute admin http://controller:8774/v2.1/%\(tenant_id\)s

echo 'Installing nova...'
apt-get -y -q install nova-api nova-conductor nova-consoleauth nova-novncproxy nova-scheduler

echo 'Configuring /etc/nova/nova.conf...'
# Comments out all lines in section
sed -i "/^\[keystone_authtoken\]/,/^\[.*\]/{/^\[.*\]/!{s/^/#/}}" ${novaConfPath}
sed -i '/^\[DEFAULT\]/,/^\[.*\]/{/^logdir/{s/^/#/}}' ${novaConfPath}
sed -i '/^\[DEFAULT\]/,/^\[.*\]/{/^enabled_apis/{s/^/#/}}' ${novaConfPath}

cat > /tmp/novaConf << END_OF_CONF
enabled_apis = osapi_compute,metadata
rpc_backend = rabbit
auth_strategy = keystone
my_ip = ${contIP}
use_neutron = True
firewall_driver = nova.virt.firewall.NoopFirewallDriver
END_OF_CONF
sed --in-place -e "/^\[DEFAULT\]/r /tmp/novaConf" ${novaConfPath}

cat >> ${novaConfPath} << END_OF_CONF

[api_database]
connection = mysql+pymysql://nova:${novaDBPass}@controller/nova_api

[database]
connection = mysql+pymysql://nova:${novaDBPass}@controller/nova

[oslo_messaging_rabbit]
rabbit_host = controller
rabbit_userid = openstack
rabbit_password = ${rabbitPass}

[keystone_authtoken]
auth_uri = http://controller:5000
auth_url = http://controller:35357
memcached_servers = controller:11211
auth_type = password
project_domain_name = default
user_domain_name = default
project_name = service
username = nova
password = ${novaPass}

[vnc]
vncserver_listen = \$my_ip
vncserver_proxyclient_address = \$my_ip

[glance]
api_servers = http://controller:9292

[oslo_concurrency]
lock_path = /var/lib/nova/tmp
END_OF_CONF

echo 'Populating compute databases...'
su -s /bin/sh -c "nova-manage api_db sync" nova
su -s /bin/sh -c "nova-manage db sync" nova

echo 'Restarting nova services...'
service nova-api restart
service nova-consoleauth restart
service nova-scheduler restart
service nova-conductor restart
service nova-novncproxy restart