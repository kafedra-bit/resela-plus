#!/usr/bin/env bash

# Author Fredrik Johansson, Annika Hansson
# Openstack version Mitaka
# Ubuntu 16.04

if [ "$EUID" -ne 0 ]
    then echo "This script must be run as root!"
    exit
fi

if [ ! -e computeInstall ]; then
    ./Compute/Mitaka/input.sh
    ./Compute/Mitaka/network.sh
else

    ./Compute/Mitaka/chronyconfig.sh
    ./Compute/Mitaka/novaconfig.sh
    ./Compute/Mitaka/neutronconfig.sh

    rm -f computeInstall

    echo "Installation complete! Reboot in 10 sec..."
    sleep 10
    reboot
fi