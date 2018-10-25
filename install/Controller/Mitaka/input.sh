#!/usr/bin/env bash

# Author Fredrik Johansson, Annika Hansson
# Openstack version Mitaka
# Ubuntu Server version 16.04 LTS

variableFile=controllerInstall

restart=1
while [ ${restart} -eq 1 ]
do
    restart=0

    while true
    do
        read -p "Enter interface name for management network: " manInt
        if [[ -n ${manInt} ]]; then break
        else echo "Invalid input, try again!"
        fi
    done

    while true
    do
        read -p "Enter interface name for provider network: " provInt
        if [[ -n ${provInt} ]]; then break
        else echo "Invalid input, try again!"
        fi
    done

    while true
    do
        read -p "Enter the password for rabbit: " rabbitPass
        if [[ -n ${rabbitPass} ]]; then break
        else echo "Invalid input, try again!"
        fi
    done

    while true
    do
        read -p "Enter the password for the keystone database: " keystonePass
        if [[ -n ${keystonePass} ]]; then break
        else echo "Invalid input, try again!"
        fi
    done

    while true
    do
        read -p "Enter the password for the glance database: " glanceDBPass
        if [[ -n ${glanceDBPass} ]]; then break
        else echo "Invalid input, try again!"
        fi
    done

    while true
    do
        read -p "Enter the password for the glance user: " glancePass
        if [[ -n ${glancePass} ]]; then break
        else echo "Invalid input, try again!"
        fi
    done

    while true
    do
        read -p "Enter the password for the neutron database: " neutronDBPass
        if [[ -n ${neutronDBPass} ]]; then break
        else echo "Invalid input, try again!"
        fi
    done

    while true
    do
        read -p "Enter the password for the neutron user: " neutronPass
        if [[ -n ${neutronPass} ]]; then break
        else echo "Invalid input, try again!"
        fi
    done

    while true
    do
        read -p "Enter the password for the nova database: " novaDBPass
        if [[ -n ${novaDBPass} ]]; then break
        else echo "Invalid input, try again!"
        fi
    done

    while true
    do
        read -p "Enter the password for the nova user: " novaPass
        if [[ -n ${novaPass} ]]; then break
        else echo "Invalid input, try again!"
        fi
    done

    while true
    do
        read -p "Enter the password for the mysql root user: " mysqlDBPass
        if [[ -n ${mysqlDBPass} ]]; then break
        else echo "Invalid input, try again!"
        fi
    done

    while true
    do
        read -p "Enter the email for the password recovery user: " pruEmail
        if [[ ${pruEmail} =~ ^.+@.+\..+$ ]]; then break
        else echo "Invalid input, try again!"
        fi
    done

    while true
    do
        read -p "Enter the password for the password recovery user: " pruPass
        if [[ -n ${pruPass} ]]; then break
        else echo "Invalid input, try again!"
        fi
    done

    while true
    do
        read -p "Enter the password for the OpenStack admin user: " openStackAdminPass
        if [[ -n ${openStackAdminPass} ]]; then break
        else echo "Invalid input, try again!"
        fi
    done

    if [ $(lsb_release -rs) == "16.04" ]; then
        while true
        do
            read -p "Enter the management network (/24 network): " managementNetwork
            if [[ ${managementNetwork} =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then break
            else echo "Invalid input, try again!"
            fi
        done
    fi

    while true
    do
        read -p "Enter the IP number for the gateway: " gatewayIP
        if [[ ${gatewayIP} =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then break
        else echo "Invalid input, try again!"
        fi
    done

    while true
    do
        read -p "Enter the IP number for the controller: " contIP
        if [[ ${contIP} =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then break
        else echo "Invalid input, try again!"
        fi
    done

    while true
    do
        read -p "Enter the number of compute nodes: " compNr
        if [[ ${compNr} =~ ^[0-9]*$ ]]; then break
        else echo "Invalid input, try again!"
        fi
    done

    compIP=()
    counter=0
    while [ ${compNr} -ne ${counter} ]
    do
        while true
        do
            read -p "Enter the IP number for compute$((${counter} + 1)): " IP
            if [[ ${IP} =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then break
            else echo "Invalid input, try again!"
            fi
        done
        compIP+=(${IP})
        counter=$((${counter} + 1))
    done

    echo -e "\nManagement network interface name: ${manInt}"
    echo "Provider network interface name: ${provInt}"
    echo "Rabbit password: ${rabbitPass}"
    echo "Keystone database password: ${keystonePass}"
    echo "Glance database password: ${glanceDBPass}"
    echo "Glance user password: ${glancePass}"
    echo "Neutron database password: ${neutronDBPass}"
    echo "Neutron user password: ${neutronPass}"
    echo "Nova database password: ${novaDBPass}"
    echo "Nova user password: ${novaPass}"
    echo "MySQL root password: ${mysqlDBPass}"
    echo "Password recovery user email: ${pruEmail}"
    echo "Password recovery user password: ${pruPass}"
    echo "OpenStack admin password: ${openStackAdminPass}"

    if [ $(lsb_release -rs) == "16.04" ]; then
        echo "Management network: ${managementNetwork}"
    fi

    echo "Gateway IP number: ${gatewayIP}"
    echo "Controller IP number: ${contIP}"

    counter=0
    while [ ${compNr} -ne ${counter} ]
    do
        echo "Compute$((${counter} + 1)) IP number: ${compIP[${counter}]}"
        counter=$((${counter} + 1))
    done

    while true
    do
        read -p "Do you confirm the settings above? (y/n): " yn
        case ${yn} in
            [Yy]* ) break;;
            [Nn]* ) restart=1; break;;
            * ) echo "Please confirm with yes(y) or no(n).";;
        esac
    done
done

cat > ${variableFile} << END_OF_CONF
manInt=${manInt}
provInt=${provInt}
rabbitPass=${rabbitPass}
keystonePass=${keystonePass}
glanceDBPass=${glanceDBPass}
glancePass=${glancePass}
neutronDBPass=${neutronDBPass}
neutronPass=${neutronPass}
novaDBPass=${novaDBPass}
novaPass=${novaPass}
mysqlDBPass=${mysqlDBPass}
pruEmail=${pruEmail}
pruPass=${pruPass}
openStackAdminPass=${openStackAdminPass}
gatewayIP=${gatewayIP}
contIP=${contIP}
compNr=${compNr}
END_OF_CONF

if [ $(lsb_release -rs) == "16.04" ]; then
    echo "managementNetwork=${managementNetwork}" >> ${variableFile}
fi

counter=0
while [ ${compNr} -ne ${counter} ]
do
    echo "compIP[${counter}]=${compIP[${counter}]}" >> ${variableFile}
    counter=$((${counter} + 1))
done

cat >> ${variableFile} << END_OF_CONF
interfacesPath="/etc/network/interfaces"
hostsPath="/etc/hosts"
glanceAPIConfPath="/etc/glance/glance-api.conf"
glanceRegistryConfPath="/etc/glance/glance-registry.conf"
mysqlConfPathU14="/etc/mysql/conf.d/openstack.cnf"
mysqlConfPathU16="/etc/mysql/mariadb.conf.d/99-openstack.cnf"
mongoDBConfPath="/etc/mongodb.conf"
memcachedConfPath="/etc/memcached.conf"
chronyPath="/etc/chrony/chrony.conf"
dashboardSettingsPath="/etc/openstack-dashboard/local_settings.py"
keystoneConfPath="/etc/keystone/keystone.conf"
apacheConfPath="/etc/apache2/apache2.conf"
apacheKeystoneConfPath="/etc/apache2/sites-available/wsgi-keystone.conf"
neutronPluginConfPath="/etc/neutron/plugins/ml2/ml2_conf.ini"
neutronPluginAgentPath="/etc/neutron/plugins/ml2/linuxbridge_agent.ini"
neutronDCHPConfPath="/etc/neutron/dhcp_agent.ini"
neutronMetadataAgentPath="/etc/neutron/metadata_agent.ini"
neutronConfPath="/etc/neutron/neutron.conf"
novaConfPath="/etc/nova/nova.conf"
keystonePolicyPath="/etc/keystone/policy.json"
novaPolicyPath="/etc/nova/policy.json"
glancePolicyPath="/etc/glance/policy.json"
neutronPolicyPath="/etc/neutron/policy.json"
END_OF_CONF