#!/usr/bin/env bash

# Author Fredrik Johansson
# Openstack version Mitaka
# Ubuntu Server version 16.04 LTS

# Load the variables containing user input
. controllerInstall

echo "Installing python3-keystoneauth1 and python3-keystoneclient..."
apt-get install -y python3-keystoneauth1 python3-keystoneclient

echo "Replacing the keystone policy file..."
cp -f ./Controller/Mitaka/ReSeLa_policies/keystone.json ${keystonePolicyPath}

echo "Replacing the nova policy file..."
cp -f ./Controller/Mitaka/ReSeLa_policies/nova.json ${novaPolicyPath}

echo "Replacing the glance policy file..."
cp -f ./Controller/Mitaka/ReSeLa_policies/glance.json ${glancePolicyPath}

echo "Replacing the neutron policy file..."
cp -f ./Controller/Mitaka/ReSeLa_policies/neutron.json ${neutronPolicyPath}

. admin-openrc

echo "Creating the default project..."
openstack project create default --domain default

echo "Creating the image library..."
openstack domain create imageLibrary --description "The image library where all uploaded images
is placed"

echo "Creating the snapshot factory domain..."
openstack domain create snapshotFactory --description "The domain that contains all the snapshot
factory projects owned by teachers"

echo "Creating the roles for teacher, student and PRU..."
openstack role create teacher
openstack role create student
openstack role create PRU

echo "Creating the user PRU..."
openstack user create ${pruEmail} --domain default --email ${pruEmail} --password ${pruPass} \
--description "Password recovery user (PRU)"

echo "Creating the groups students, teachers and admin..."
openstack group create students --domain default
openstack group create teachers --domain default
openstack group create admin --domain default

echo "Adding admin to group admin..."
openstack group add user admin admin

echo "Assigning roles to groups and users..."
openstack role add PRU --user ${pruEmail} --domain default
openstack role add PRU --user ${pruEmail} --project default
openstack role add admin --user admin --domain default
openstack role add admin --user admin --project default
openstack role add student --group students --domain default
openstack role add student --group students --project default
openstack role add teacher --group teachers --domain default
openstack role add teacher --group teachers --project default

echo "Creating image library projects..."
python3 ./Controller/Mitaka/setupImageLibrary.py admin ${openStackAdminPass}

echo "Giving the admin user a name..."
python3 ./Controller/Mitaka/babtize_admin.py ${openStackAdminPass}

# Assign roles for each group to the imageLibrary and its projects
echo "Assigning role for admin group in imageLibrary..."
openstack role add admin --group admin --domain imageLibrary
openstack role add admin --group admin --project "imageLibrary|default"
openstack role add admin --group admin --project "imageLibrary|snapshots"
openstack role add admin --group admin --project "imageLibrary|images"

echo "Assigning role for student group in imageLibrary..."
openstack role add student --group students --domain imageLibrary
openstack role add student --group students --project "imageLibrary|default"
openstack role add student --group students --project "imageLibrary|snapshots"
openstack role add student --group students --project "imageLibrary|images"

echo "Assigning role for teacher group in imageLibrary..."
openstack role add teacher --group teachers --domain imageLibrary
openstack role add teacher --group teachers --project "imageLibrary|default"
openstack role add teacher --group teachers --project "imageLibrary|snapshots"
openstack role add teacher --group teachers --project "imageLibrary|images"

echo "Assigning role for admin group in snapshotFactory domain..."
openstack role add admin --group admin --domain snapshotFactory

echo "Assigning role for teacher group in snapshotFactory domain..."
openstack role add teacher --group teachers --domain snapshotFactory

echo "Updating the nova quota..."
nova quota-class-update --instances -1 --ram -1 --cores -1 default

echo "Updating the neutron quota..."
neutron quota-update default --network 1024 --subnet 1024

echo "Configuring the file /etc/neutron/plugins/ml2/ml2_conf.ini..."
cat > /tmp/neutronConf << END_OF_CONF
network_vlan_ranges = provider:10:4094
END_OF_CONF
sed -i -e "/^\[ml2_type_vlan\]/r /tmp/neutronConf" ${neutronPluginConfPath}

mkdir /var/lib/resela
cp -f ./Controller/Mitaka/resela_sec_group_cleanup.py /var/lib/resela/resela_sec_group_cleanup.py

cat > /etc/cron.d/resela_sec_group_cleanup << END_OF_CONF
0 0 * * * root python3 /var/lib/resela/resela_sec_group_cleanup.py admin ${openStackAdminPass}
END_OF_CONF

