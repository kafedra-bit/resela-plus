#!/usr/bin/env bash

# Author Fredrik Johansson, Annika Hansson
# Openstack version Mitaka
# Ubuntu Server version 16.04 LTS

# Load the variables containing user input
. controllerInstall

echo 'Creating neutron database...'
mysql -u root -p${mysqlDBPass} -e "CREATE DATABASE neutron;"
mysql -u root -p${mysqlDBPass} -e "GRANT ALL PRIVILEGES ON neutron.* TO 'neutron'@'localhost' IDENTIFIED BY '${neutronDBPass}';"
mysql -u root -p${mysqlDBPass} -e "GRANT ALL PRIVILEGES ON neutron.* TO 'neutron'@'%' IDENTIFIED BY '${neutronDBPass}';"

echo 'Creating neutron user...'
# load admin env. variable
. admin-openrc
openstack user create --domain default --password ${neutronPass} neutron
openstack role add --project service --user neutron admin
openstack service create --name neutron --description "OpenStack Networking" network

echo 'Creating networking api endpoints...'
openstack endpoint create --region RegionOne network public http://controller:9696
openstack endpoint create --region RegionOne network internal http://controller:9696
openstack endpoint create --region RegionOne network admin http://controller:9696

echo 'Installing neutron components...'
apt-get -y -q install neutron-server neutron-plugin-ml2 neutron-linuxbridge-agent \
neutron-dhcp-agent neutron-metadata-agent

echo 'Configurating /etc/neutron/neutron.conf...'
# Comments out all lines in section
sed -i "/^\[keystone_authtoken\]/,/^\[.*\]/{/^\[.*\]/!{s/^/#/}}" ${neutronConfPath}
# Comments out previous connections
sed -i '/^\[database\]/,/^\[.*\]/{/^connection/{s/^/#/}}' ${neutronConfPath}

cat > /tmp/neutronConf << END_OF_CONF
connection = mysql+pymysql://neutron:${neutronDBPass}@controller/neutron
END_OF_CONF

sed --in-place -e "/^\[database\]/r /tmp/neutronConf" ${neutronConfPath}

cat > /tmp/neutronConf << END_OF_CONF
core_plugin = ml2
service_plugins =
rpc_backend = rabbit
auth_strategy = keystone
notify_nova_on_port_status_changes = True
notify_nova_on_port_data_changes = True
END_OF_CONF
sed --in-place -e "/^\[DEFAULT\]/r /tmp/neutronConf" ${neutronConfPath}

cat > /tmp/neutronConf << END_OF_CONF
quota_subnet = -1
quota_network = -1
END_OF_CONF
sed --in-place -e "/^\[quotas\]/r /tmp/neutronConf" ${neutronConfPath}

cat > /tmp/neutronConf << END_OF_CONF
rabbit_host = controller
rabbit_userid = openstack
rabbit_password = ${rabbitPass}
END_OF_CONF
sed --in-place -e "/^\[oslo_messaging_rabbit\]/r /tmp/neutronConf" ${neutronConfPath}

cat > /tmp/neutronConf << END_OF_CONF
auth_uri = http://controller:5000
auth_url = http://controller:35357
memcached_servers = controller:11211
auth_type = password
project_domain_name = default
user_domain_name = default
project_name = service
username = neutron
password = ${neutronPass}
END_OF_CONF
sed --in-place -e "/^\[keystone_authtoken\]/r /tmp/neutronConf" ${neutronConfPath}

cat > /tmp/neutronConf << END_OF_CONF
auth_url = http://controller:35357
auth_type = password
project_domain_name = default
user_domain_name = default
region_name = RegionOne
project_name = service
username = nova
password = ${novaPass}
END_OF_CONF
sed --in-place -e "/^\[nova\]/r /tmp/neutronConf" ${neutronConfPath}

echo 'Configuring /etc/neutron/plugins/ml2/ml2_conf.ini...'
cat > /tmp/neutronConf << END_OF_CONF
type_drivers = flat,vlan
tenant_network_types =
mechanism_drivers = linuxbridge
extension_drivers = port_security
END_OF_CONF
sed --in-place -e "/^\[ml2\]/r /tmp/neutronConf" ${neutronPluginConfPath}

cat > /tmp/neutronConf << END_OF_CONF
flat_networks = provider
END_OF_CONF
sed --in-place -e "/^\[ml2_type_flat\]/r /tmp/neutronConf" ${neutronPluginConfPath}

cat > /tmp/neutronConf << END_OF_CONF
enable_ipset = True
END_OF_CONF
sed --in-place -e "/^\[securitygroup\]/r /tmp/neutronConf" ${neutronPluginConfPath}

echo 'Configuring /etc/neutron/plugins/ml2/linuxbridge_agent.ini...'
cat > /tmp/neutronConf << END_OF_CONF
physical_interface_mappings = provider:${provInt}
END_OF_CONF
sed --in-place -e "/^\[linux_bridge\]/r /tmp/neutronConf" ${neutronPluginAgentPath}

cat > /tmp/neutronConf << END_OF_CONF
enable_vxlan = False
END_OF_CONF
sed --in-place -e "/^\[vxlan\]/r /tmp/neutronConf" ${neutronPluginAgentPath}

cat > /tmp/neutronConf << END_OF_CONF
enable_security_group = True
firewall_driver = neutron.agent.linux.iptables_firewall.IptablesFirewallDriver
END_OF_CONF
sed --in-place -e "/^\[securitygroup\]/r /tmp/neutronConf" ${neutronPluginAgentPath}

echo 'Configuring /etc/neutron/dhcp_agent.ini...'
cat > /tmp/neutronConf << END_OF_CONF
interface_driver = neutron.agent.linux.interface.BridgeInterfaceDriver
dhcp_driver = neutron.agent.linux.dhcp.Dnsmasq
enable_isolated_metadata = True
END_OF_CONF
sed --in-place -e "/^\[DEFAULT\]/r /tmp/neutronConf" ${neutronDCHPConfPath}

#random secret for neutron metadata
metaSecret=$(openssl rand -hex 10)

echo 'Configuring /etc/neutron/metadata_agent.ini...'
cat > /tmp/neutronConf << END_OF_CONF
nova_metadata_ip = controller
metadata_proxy_shared_secret = ${metaSecret}
END_OF_CONF
sed --in-place -e "/^\[DEFAULT\]/r /tmp/neutronConf" ${neutronMetadataAgentPath}

echo 'Configuring /etc/nova/nova.conf...'
cat >> ${novaConfPath} << END_OF_CONF

[neutron]
url = http://controller:9696
auth_url = http://controller:35357
auth_type = password
project_domain_name = default
user_domain_name = default
region_name = RegionOne
project_name = service
username = neutron
password = ${neutronPass}
service_metadata_proxy = True
metadata_proxy_shared_secret = ${metaSecret}
END_OF_CONF

echo "Populating neutron database..."
su -s /bin/sh -c "neutron-db-manage --config-file /etc/neutron/neutron.conf --config-file /etc/neutron/plugins/ml2/ml2_conf.ini upgrade head" neutron



echo "Restarting nova and neutron services..."
service nova-api restart
service neutron-server restart
service neutron-linuxbridge-agent restart
service neutron-dhcp-agent restart
service neutron-metadata-agent restart