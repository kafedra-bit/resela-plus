#!/usr/bin/env bash

# Author Fredrik Johansson, Annika Hansson
# Openstack version Mitaka
# Ubuntu Server version 16.04 LTS

# Load the variables containing user input
. controllerInstall

echo 'Configuring keystone database...'
mysql -u root -p${mysqlDBPass} -e "CREATE DATABASE keystone;"
mysql -u root -p${mysqlDBPass} -e "GRANT ALL PRIVILEGES ON keystone.* TO 'keystone'@'localhost' IDENTIFIED BY '${keystonePass}';"
mysql -u root -p${mysqlDBPass} -e "GRANT ALL PRIVILEGES ON keystone.* TO 'keystone'@'%' IDENTIFIED BY '${keystonePass}';"

#generating admin token used for default configuration
tmpAdminToken=$(openssl rand -hex 10)

echo 'Configuring /etc/init/keystone.override...'
echo "manual" > /etc/init/keystone.override

echo 'Installing keystone and apache2...'
apt-get -y -q install keystone apache2 libapache2-mod-wsgi

echo 'Configuring /etc/keystone/keystone.conf...'
# Comments out any other connection
sed -i '/^\[database\]/,/^\[.*\]/{/^connection/{s/^/#/}}' ${keystoneConfPath}

cat > /tmp/keystoneConf << END_OF_CONF
admin_token = ${tmpAdminToken}
END_OF_CONF
sed --in-place -e "/^\[DEFAULT\]/r /tmp/keystoneConf" ${keystoneConfPath}

cat > /tmp/keystoneConf << END_OF_CONF
connection = mysql+pymysql://keystone:${keystonePass}@controller/keystone
END_OF_CONF
sed --in-place -e "/^\[database\]/r /tmp/keystoneConf" ${keystoneConfPath}

cat > /tmp/keystoneConf << END_OF_CONF
provider = fernet
END_OF_CONF
sed --in-place -e "/^\[token\]/r /tmp/keystoneConf" ${keystoneConfPath}

echo 'Populating the identity service database...'
su -s /bin/sh -c "keystone-manage db_sync" keystone

echo 'Initializing fernet keys...'
keystone-manage fernet_setup --keystone-user keystone --keystone-group keystone

echo 'Configuring /etc/apache2/apache2.conf...'
cat >> ${apacheConfPath} << END_OF_CONF
ServerName controller
END_OF_CONF

echo 'Configuring /etc/apache2/sites-available/wsgi-keystone.conf...'
cat > ${apacheKeystoneConfPath} << END_OF_CONF
Listen 5000
Listen 35357

<VirtualHost *:5000>
    WSGIDaemonProcess keystone-public processes=5 threads=1 user=keystone group=keystone display-name=%{GROUP}
    WSGIProcessGroup keystone-public
    WSGIScriptAlias / /usr/bin/keystone-wsgi-public
    WSGIApplicationGroup %{GLOBAL}
    WSGIPassAuthorization On
    ErrorLogFormat "%{cu}t %M"
    ErrorLog /var/log/apache2/keystone.log
    CustomLog /var/log/apache2/keystone_access.log combined

    <Directory /usr/bin>
        Require all granted
    </Directory>
</VirtualHost>

<VirtualHost *:35357>
    WSGIDaemonProcess keystone-admin processes=5 threads=1 user=keystone group=keystone display-name=%{GROUP}
    WSGIProcessGroup keystone-admin
    WSGIScriptAlias / /usr/bin/keystone-wsgi-admin
    WSGIApplicationGroup %{GLOBAL}
    WSGIPassAuthorization On
    ErrorLogFormat "%{cu}t %M"
    ErrorLog /var/log/apache2/keystone.log
    CustomLog /var/log/apache2/keystone_access.log combined

    <Directory /usr/bin>
        Require all granted
    </Directory>
</VirtualHost>
END_OF_CONF

echo 'Enabling identity service virtual hosts...'
ln -s /etc/apache2/sites-available/wsgi-keystone.conf /etc/apache2/sites-enabled

echo "Killing keystone service..."
service keystone stop

echo 'Restarting apache server...'
service apache2 restart

echo 'Removing SQLite database...'
rm -f /var/lib/keystone/keystone.db

# Added env. variables for further configuration
export OS_TOKEN=${tmpAdminToken}
export OS_URL='http://controller:35357/v3'
export OS_IDENTITY_API_VERSION=3

echo 'Creating service entity and api endpoints for keystone...'
openstack service create --name keystone --description "OpenStack Identity" identity
openstack endpoint create --region RegionOne identity public http://controller:5000/v3
openstack endpoint create --region RegionOne identity internal http://controller:5000/v3
openstack endpoint create --region RegionOne identity admin http://controller:35357/v3

echo 'Creating default domain...'
openstack domain create --description "Default Domain" default

echo 'Creating admin project...'
openstack project create --domain default --description "Admin Project" admin

echo 'Creating admin user...'
openstack user create --domain default --password ${openStackAdminPass} admin
openstack role create admin
openstack role add --project admin --user admin admin

echo 'Creating service project...'
openstack project create --domain default --description "Service Project" service

echo 'Creating admin-openrc...'
cat > admin-openrc << END_OF_CONF
export OS_PROJECT_DOMAIN_NAME=default
export OS_USER_DOMAIN_NAME=default
export OS_PROJECT_NAME=admin
export OS_USERNAME=admin
export OS_PASSWORD=${openStackAdminPass}
export OS_AUTH_URL=http://controller:35357/v3
export OS_IDENTITY_API_VERSION=3
export OS_IMAGE_API_VERSION=2
END_OF_CONF

echo 'Configuring /etc/keystone/keystone-paste.ini...'
# Deletes the admin_token_auth string in the sections: [pipeline:public_api], [pipeline:admin_api] and [pipeline:api_v3]
sed -i '/\[pipeline:public_api\]/,/\[.*\]/{/admin_token_auth/s/admin_token_auth//}' /etc/keystone/keystone-paste.ini
sed -i '/\[pipeline:admin_api\]/,/\[.*\]/{/admin_token_auth/s/admin_token_auth//}' /etc/keystone/keystone-paste.ini
sed -i '/\[pipeline:api_v3\]/,/\[.*\]/{/admin_token_auth/s/admin_token_auth//}' /etc/keystone/keystone-paste.ini

# Removing env. variables.
unset OS_TOKEN OS_URL

