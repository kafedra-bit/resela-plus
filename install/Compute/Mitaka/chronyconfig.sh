#!/usr/bin/env bash

# Author Fredrik Johansson, Annika Hansson
# Openstack version Mitaka

#Chrony installation
. computeInstall

# Installs chrony NTP services
echo "Installing chrony..."
apt-get -y -q install chrony

echo "Configuring /etc/chrony/chrony.conf..."

#comment out all lines starting with server
sed -i 's/^server/# server/' ${chronyPath}
sed -i 's/^pool/# server/' ${chronyPath}

#remove all comments in config file
sed -i '/^#/d' ${chronyPath}
sed -i '/^\s*$/d' ${chronyPath}
sed -i '1!{/^\[.*\]/{s/^/\n/}}' ${chronyPath}

#insert line at end of file
echo -e "\nserver controller iburst" >> ${chronyPath}

echo "Restarting chrony..."
service chrony restart
