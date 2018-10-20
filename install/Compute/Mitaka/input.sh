#!/usr/bin/env bash

# Author Fredrik Johansson, Annika Hansson
# Ubuntu 14.04 LTS and 16.04 LTS server
# Openstack version Mitaka

variableFile=computeInstall

restart=1
while [ ${restart} -eq 1 ]
do
    restart=0
    while true
    do
        read -p "Enter interface name for management network: " manInt
        if [[ ! -z ${manInt} ]]; then break
        else echo "Invalid input, try again!"
        fi
    done

    while true
    do
        read -p "Enter interface name for provider network: " provInt
        if [[ ! -z ${provInt} ]]; then break
        else echo "Invalid input, try again!"
        fi
    done

    while true
    do
        read -p "Enter the password for rabbit: " rabbitPass
        if [[ ! -z ${rabbitPass} ]]; then break
        else echo " Invalid input, try again!"
        fi
    done

    while true
    do
        read -p "Enter the password for the neutron user: " neutronPass
        if [[ ! -z ${neutronPass} ]]; then break
        else echo "Invalid input, try again"
        fi
    done

    while true
    do
        read -p "Enter the password for the nova user: " novaPass
        if [[ ! -z ${novaPass} ]]; then break
        else echo "Invalid input, try again!"
        fi
    done

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

    if [ ${compNr} -gt 1 ]
    then
        while true
        do
            read -p "Which compute node is this? [1-${#compIP[*]}]: " nodeNr
            if [[ ${nodeNr} =~ ^[1-${#compIP[*]}]$ ]]; then nodeIP=${compIP[$((${nodeNr} - 1))]}; break
            else echo "Invalid input, try again!"
            fi
        done
    else
        nodeIP=${compIP[0]};
    fi

    echo -e "\nManagement network interface name: ${manInt}"
    echo "Provider network interface name: ${provInt}"
    echo "Rabbit password: ${rabbitPass}"
    echo "Neutron user password: ${neutronPass}"
    echo "Nova user password: ${novaPass}"
    echo "Gateway IP number: ${gatewayIP}"
    echo "Controller IP number: ${contIP}"
    echo "This compute node: ${nodeIP}"

    counter=0
    while [ ${compNr} -ne ${counter} ]
    do
        echo "Compute$((counter + 1)) IP number: ${compIP[${counter}]}"
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

#variables
cat > ${variableFile} << END_OF_CONF
manInt=${manInt}
provInt=${provInt}
rabbitPass=${rabbitPass}
neutronPass=${neutronPass}
novaPass=${novaPass}
gatewayIP=${gatewayIP}
contIP=${contIP}
compNr=${compNr}
nodeIP=${nodeIP}
END_OF_CONF

counter=0
while [ ${compNr} -ne ${counter} ]
do
    echo "compIP[${counter}]=${compIP[${counter}]}" >> ${variableFile}
    counter=$((${counter} + 1))
done

#config file paths
cat >> ${variableFile} << END_OF_CONF
novaConfPath="/etc/nova/nova.conf"
hostsPath="/etc/hosts"
interfacesPath="/etc/network/interfaces"
chronyPath="/etc/chrony/chrony.conf"
novaComputeConfPath="/etc/nova/nova-compute.conf"
neutronConfPath="/etc/neutron/neutron.conf"
linuxbridgeagentConf="/etc/neutron/plugins/ml2/linuxbridge_agent.ini"
END_OF_CONF