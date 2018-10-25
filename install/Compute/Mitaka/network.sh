#!/usr/bin/env bash

# Author Fredrik Johansson, Annika Hansson
# Openstack version Mitaka

. computeInstall

# Configures the hosts file
echo "Configuring /etc/hosts..."

rm -f ${hostsPath}
echo -e "# localhost\n127.0.0.1\tlocalhost\n" > ${hostsPath}

echo -e "# controller\n${contIP}\tcontroller\n" >> ${hostsPath}

counter=0
while [ ${compNr} -ne ${counter} ]
do
	echo -e "#compute$((counter + 1))\n${compIP[${counter}]}\tcompute$((counter + 1))\n" >> ${hostsPath}
	counter=$((${counter} + 1))
done

# Configures the interface file
echo "Configuring /etc/network/interfaces..."
cat > ${interfacesPath} << END_OF_CONF
# The loopback network interface
auto lo
iface lo inet loopback

# The management network interface
auto ${manInt}
iface ${manInt} inet static
address ${nodeIP}/24
gateway ${gatewayIP}
dns-nameservers 192.168.212.2 192.168.0.1

# The provider network interface
auto ${provInt}
iface ${provInt} inet manual
up ip link set dev \$IFACE up
down ip link set dev \$IFACE down
END_OF_CONF

# Restarting interfaces
echo "A restart of the compute node is needed. After reboot run script again to continue installation."
read -p "Press any key to continue..." </dev/tty
reboot
