#!/usr/bin/env bash

# Author Fredrik Johansson, Annika Hansson
# Openstack version Mitaka
# Ubuntu Server version 16.04 LTS

# Load the variables containing user input
. controllerInstall

echo 'Configuring /etc/hosts...'
cat > ${hostsPath} << END_OF_CONF
# localhost
127.0.0.1   localhost
# controller
${contIP}   controller
END_OF_CONF

counter=0
while [ ${compNr} -ne ${counter} ]
do
	echo -e "#compute${counter}\n${compIP[${counter}]}\tcompute$((${counter} + 1))\n" >> ${hostsPath}
	counter=$((${counter} + 1))
done

echo 'Configuring /etc/network/interfaces...'
cat > ${interfacesPath} << END_OF_CONF
# The loopback network interface
auto lo
iface lo inet loopback

# The management network interface
auto ${manInt}
iface ${manInt} inet static
address ${contIP}/24
gateway ${gatewayIP}
dns-nameservers 8.8.8.8

# The provider network interface
auto ${provInt}
iface ${provInt} inet manual
up ip link set dev \$IFACE up
down ip link set dev \$IFACE down
END_OF_CONF

echo "A restart of the controller node is required to configure the network settings."
echo "After reboot execute the installation script once again to continue the installation."
read -p "Press Enter to reboot..." < /dev/tty
reboot