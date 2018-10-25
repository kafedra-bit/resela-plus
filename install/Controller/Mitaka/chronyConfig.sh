#!/usr/bin/env bash

# Author Fredrik Johansson, Annika Hansson
# Openstack version Mitaka
# Ubuntu Server version 16.04 LTS

# Load the variables containing user input
. controllerInstall

echo 'Installing chrony...'
apt-get -y -q install chrony
# Use the lines below and change NTP_SERVER to use different ntp servers. To add more servers, just add an another row
#cat >> ${chronyPath} << END_OF_CONF
#server NTP_SERVER iburst
#END_OF_CONF

if [ $(lsb_release -rs) == "16.04" ]; then
    echo "allow ${managementNetwork}/24" >> ${chronyPath}
fi

echo 'Restarting chrony...'
service chrony restart