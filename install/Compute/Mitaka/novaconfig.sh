#!/usr/bin/env bash

# Author Fredrik Johansson, Annika Hansson
# Openstack version Mitaka

#Nova installation
. computeInstall

# enables the OpenStack repository
echo "Enabeling the OpenStack repository..."
apt-get -y -q install software-properties-common
add-apt-repository -y cloud-archive:mitaka

echo "Updating and upgrading the system..."
apt-get -y -q update
apt-get -y -q dist-upgrade

echo "Installing OpenStack client..."
apt-get -y -q install python-openstackclient

#start installing nova
echo "Installing nova-compute..."
apt-get -y -q install nova-compute

echo "Configuring /etc/nova/nova.conf..."
#comment out all lines in section
sed -i '/^\[keystone_authtoken\]/,/^\[.*\]/{/^\[.*\]/!{s/^/#/}}' ${novaConfPath}
sed -i 's/^logdir/# logdir/' ${novaConfPath}

#default section
cat >/tmp/nova<<END_NOVA
rpc_backend = rabbit
auth_strategy = keystone
my_ip = ${nodeIP}
use_neutron = True
firewall_driver = nova.virt.firewall.NoopFirewallDriver
END_NOVA

sed --in-place --regexp-extended -e '/^\[DEFAULT\]/r /tmp/nova' ${novaConfPath}

#oslo_messaging_rabbit section
rm /tmp/nova
cat >/tmp/nova<<END_NOVA
rabbit_host = controller
rabbit_userid = openstack
rabbit_password = ${rabbitPass}
END_NOVA

echo -e "\n\n[oslo_messaging_rabbit]" >> ${novaConfPath}
sed --in-place --regexp-extended -e '/^\[oslo_messaging_rabbit\]/r /tmp/nova' ${novaConfPath}

#keystone_authtoken section
cat >/tmp/nova<<END_NOVA
auth_uri = http://controller:5000
auth_url = http://controller:35357
memchached_servers = controller:11211
auth_type = password
project_domain_name = default
user_domain_name = default
project_name = service
username = nova
password = ${novaPass}
END_NOVA

echo -e "\n\n[keystone_authtoken]" >> ${novaConfPath}
sed --in-place --regexp-extended -e '/^\[keystone_authtoken\]/r /tmp/nova' ${novaConfPath}

#vnc section
cat >/tmp/nova<<END_NOVA
enabled = True
vncserver_listen = 0.0.0.0
vncserver_proxyclient_address = \$my_ip
novncproxy_base_url = http://${contIP}:6080/vnc_auto.html
END_NOVA

echo -e "\n\n[vnc]" >> ${novaConfPath}
sed --in-place --regexp-extended -e '/^\[vnc\]/r /tmp/nova' ${novaConfPath}

#glance section
cat >/tmp/nova<<END_NOVA
api_servers = http://controller:9292
END_NOVA

echo -e "\n\n[glance]" >> ${novaConfPath}
sed --in-place --regexp-extended -e '/^\[glance\]/r /tmp/nova' ${novaConfPath}

#oslo_concurrency section
cat >/tmp/nova<<END_NOVA
lock_path = /var/lib/nova/tmp
END_NOVA

echo -e "\n\n[oslo_concurrency]" >> ${novaConfPath}
sed --in-place --regexp-extended -e '/^\[oslo_concurrency\]/r /tmp/nova' ${novaConfPath}

if  egrep -c '(vmx|svm)' /proc/cpuinfo | grep -q '0'; then
	echo "Configuring /etc/nova/nova-compute.conf..."
	sed -i 's/^virt_type/# virt_type/' ${novaComputeConfPath}
	sed -i '/^\[libvirt\]/a\virt_type = qemu' ${novaComputeConfPath}
fi

echo "Restarting nova-compute..."
service nova-compute restart
