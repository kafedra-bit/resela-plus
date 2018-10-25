#!/usr/bin/env bash

# Author Fredrik Johansson, Annika Hansson
# Openstack version Mitaka

. computeInstall
#Neutron installation

echo "Installing neutron-linuxbridge-agent..."
apt-get -y -q install neutron-linuxbridge-agent

echo "Configuring /etc/neutron/neutron.conf..."
cat >/tmp/neutronDefaultConf <<END_DEF_NEUTRON
rpc_backend = rabbit
auth_strategy = keystone
END_DEF_NEUTRON

cat >/tmp/neutronRabbitConf <<END_RAB_NEUTRON
rabbit_host = controller
rabbit_userid = openstack
rabbit_password = ${rabbitPass}
END_RAB_NEUTRON

cat >/tmp/neutronKeystoneConf <<END_KEY_NEUTRON
auth_uri = http://controller:5000
auth_url = http://controller:35357
memchached_servers = controller:11211
auth_type = password
project_domain_name = default
user_domain_name = default
project_name = service
username = neutron
password = ${neutronPass}
END_KEY_NEUTRON

#comment out all lines
sed -i '/^\s*$/d' ${neutronConfPath}
sed -i '/^\[keystone_authtoken\]/,/^\[.*\]/{/^\[.*\]/!{s/^/#/}}' ${neutronConfPath}
sed -i 's/^connection/# connection/' ${neutronConfPath}
#remove all comments in file
sed -i '/^#/d' ${neutronConfPath}
sed -i '/^\s*$/d' ${neutronConfPath}
sed -i '1!{/^\[.*\]/{s/^/\n/}}' ${neutronConfPath}

sed --in-place --regexp-extended -e '/^\[DEFAULT\]/r /tmp/neutronDefaultConf' ${neutronConfPath}
sed --in-place --regexp-extended -e '/^\[oslo_messaging_rabbit\]/r /tmp/neutronRabbitConf' ${neutronConfPath}
sed --in-place --regexp-extended -e '/^\[keystone_authtoken\]/r /tmp/neutronKeystoneConf' ${neutronConfPath}

echo "Configuring /etc/neutron/plugins/ml2/linuxbridge_agent.ini..."
cat >/tmp/linuxbridge <<END_LINUX_BRIDGE
physical_interface_mappings = provider:${provInt}
END_LINUX_BRIDGE

cat >/tmp/linuxbridgevlan <<END_LINUX_BRIDGE_VLAN
enable_vxlan = False
END_LINUX_BRIDGE_VLAN

cat >/tmp/linuxbridgesec <<END_LINUX_BRIDGE_SEC
enable_security_group = True
firewall_driver = neutron.agent.linux.iptables_firewall.IptablesFirewallDriver
END_LINUX_BRIDGE_SEC

#remove all comments
sed -i '/^#/d' ${linuxbridgeagentConf}
sed -i '/^\s*$/d' ${linuxbridgeagentConf}
sed -i '1!{/^\[.*\]/{s/^/\n/}}' ${linuxbridgeagentConf}

sed --in-place --regexp-extended -e '/^\[linux_bridge\]/r /tmp/linuxbridge' ${linuxbridgeagentConf}
sed --in-place --regexp-extended -e '/^\[vxlan\]/r /tmp/linuxbridgevlan' ${linuxbridgeagentConf}
sed --in-place --regexp-extended -e '/^\[securitygroup\]/r /tmp/linuxbridgesec' ${linuxbridgeagentConf}

echo "Configuring /etc/nova/nova.conf..."
cat >/tmp/nova <<END_NOVA
url = http://controller:9696
auth_url = http://controller:35357
auth_type = password
project_domain_name = default
user_domain_name = default
region_name = RegionOne
project_name = service
username = neutron
password = ${neutronPass}
END_NOVA

#remove all comments
sed -i '/^#/d' ${novaConfPath}
sed -i '/^\s*$/d' ${novaConfPath}
sed -i '1!{/^\[.*\]/{s/^/\n/}}' ${novaConfPath}

echo -e "\n\n[neutron]" >> ${novaConfPath}
sed --in-place --regexp-extended -e '/^\[neutron\]/r /tmp/nova' ${novaConfPath}

echo "Restarting nova-compute..."
service nova-compute restart

echo "Restarting neutron-linuxbridge-agent..."
service neutron-linuxbridge-agent restart
