#!/usr/bin/env bash -ex

# Author Fredrik Johansson, Annika Hansson
# Openstack version Mitaka
# Ubuntu Server version 16.04 LTS

if [ "$EUID" -ne 0 ]
    then echo "This script must be run as root!"
    exit
fi

if [ ! -e controllerInstall ]; then
    ./Controller/Mitaka/input.sh
    ./Controller/Mitaka/networkConfig.sh
fi

./Controller/Mitaka/chronyConfig.sh
./Controller/Mitaka/environmentConfig.sh
./Controller/Mitaka/keystoneConfig.sh
./Controller/Mitaka/glanceConfig.sh
./Controller/Mitaka/novaConf.sh
./Controller/Mitaka/neutronConf.sh
./Controller/Mitaka/reselaConfig.sh
./Controller/Mitaka/providerNetworksConfig.sh

rm -f controllerInstall

echo "Installation complete! Reboot in 10 sec..."
sleep 10
reboot
