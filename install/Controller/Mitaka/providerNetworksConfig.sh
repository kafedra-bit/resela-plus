#!/usr/bin/env bash

# Author Fredrik Johansson
# Openstack version Mitaka
# Ubuntu Server version 16.04 LTS

. admin-openrc

echo "Creating the provider network..."
neutron net-create --shared --provider:physical_network provider --provider:network_type flat provider