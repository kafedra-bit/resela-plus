#!/usr/bin/env bash
#
# Resela web application setup script
#
# Author: Jim Ahlstrand
# Copyright 2017 resela
#
# TODO: Add option for https installation

RED='\e[0;31m'
GREEN='\e[0;32m'
YELLOW='\e[0;33m'
NC='\e[;0m'

SCRIPTPATH="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Make sure only root can run our script
if [ "$(id -u)" != "0" ]; then
   echo -e "${RED}This script must be run as root${NC}" 1>&2
   exit 1
fi

WEBDIR="/var/www"
REQUIREMENTS=$(realpath -s "${SCRIPTPATH}/requirements.txt")
APTREQUIREMENTS=$(realpath -s "${SCRIPTPATH}/apt_requirements.txt")
RESELACONFIG=$(realpath -s "${SCRIPTPATH}/../resela/config/application.ini")
TESTSCONFIG=$(realpath -s "${SCRIPTPATH}/../resela/config/tests.ini")

TESTMODE='false'
INITMODE='false'

hasApache='false'

# Check parameters
while getopts ":tih" opt
  do
    case "$opt" in
      "t")
        # Testmode is NOT intended for end users, it's only use is to generate a
        # config that works with development CI
        TESTMODE='true'
        ;;
      "i")
        INITMODE='true'
        ;;
      "h")
        echo -e "${GREEN}ReSeLa+ web application setup${NC}"
        echo -e "\t® 2017 resela"
        echo ""
        echo -e "\t-i\tInitialize project only, generates the required config files to run resela"
        echo -e "\t-h\tDisplay this help"
        exit 1
        ;;
      "?")
        echo "${RED}Unknown option ${OPTARG}${NC}" 1>&2
        exit 1
        ;;
      ":")
        echo "No argument value for option ${OPTARG}"
        ;;
      *)
      # Should not occur
        echo "${RED}Unknown error while processing options${NC}" 1>&2
        exit 1
        ;;
    esac
  done

###########################################################
# DEPENDENCIES
###########################################################

echo -e "${GREEN}Installing dependencies${NC}"
apt-get -qq update
apt-get -qy install $(cat ${APTREQUIREMENTS})

echo -e "${GREEN}Installing python packages${NC}"
pip3 install --upgrade pip
pip3 install -r "${REQUIREMENTS}"

npm update -g
npm install -g \
    npm \
    jslint

###########################################################
# ENVIRONMENT CONFIG
###########################################################

# Check python link exist
if [[ -z "$(which python)" ]]; then
    echo -e "${RED}Python not found!${NC} Make sure python is found in your path."
    echo -e "You may want to run 'ln -s /usr/bin/python3 /usr/bin/python'"
    exit 1
fi

# Check if config file exists else create it
if [ ! -f "${RESELACONFIG}" ]; then
    # If test use testconfig instead
    if [ "${TESTMODE}" == 'false' ]; then
        "${SCRIPTPATH}/../run.py" --dump-config > "${RESELACONFIG}"
    else
        cp "${TESTSCONFIG}" "${RESELACONFIG}"
    fi

    if [ "${INITMODE}" == 'false' ]; then
        chown root:www-data "${RESELACONFIG}"
        chmod 440 "${RESELACONFIG}"
    fi
    echo -e "${GREEN}Config file created${NC}"
fi

# Check if controller domain exists else configure
if ! grep -q -E '^[[:blank:]]*([0-9]{1,3}\.){3}[0-9]{1,3}[[:blank:]]+controller' /etc/hosts; then
    addHostController='false'

    # Do not prompt in testmode
    if [ "${TESTMODE}" == 'false' ]; then
        echo -e "${YELLOW}It appears that you do not have an IP mapped for the controller${NC}"
        read -n 1 -e -p "Do you want to add controller to hosts? y/n" prompt
        if [[ ${prompt} =~ ^[Yy]$ ]]; then
            addHostController='true'
        fi
    else
        addHostController='true'
    fi

    if [ "${addHostController}" == 'true' ]; then
        # Load global
        [[ -z "${CONTROLLER_IP}" ]] && read -e -i "127.0.0.1" -p "Controller IP: " controllerIP || controllerIP="${CONTROLLER_IP}"

        echo -e "${GREEN}Added controller to hosts${NC}"
        echo "${controllerIP} controller" >> /etc/hosts
    fi
fi

# Check if mikrotik domain exists else configure
if ! grep -q -E '^[[:blank:]]*([0-9]{1,3}\.){3}[0-9]{1,3}[[:blank:]]+mikrotik' /etc/hosts; then
    addHostMikrotik='false'

    # Do not prompt in testmode
    if [ "${TESTMODE}" == 'false' ]; then
        echo -e "${YELLOW}It appears that you do not have an IP mapped for mikrotik${NC}"
        read -n 1 -e -p "Do you want to add mikrotik to hosts? y/n" prompt
        if [[ ${prompt} =~ ^[Yy]$ ]]; then
            addHostMikrotik='true'
        fi
    else
        addHostMikrotik='true'
    fi

    if [ "${addHostMikrotik}" == 'true' ]; then
        # Load global
        [[ -z "${MIKROTIK_IP}" ]] && read -e -i "127.0.0.1" -p "Mikrotik IP: " mikrotikIP || mikrotikIP="${MIKROTIK_IP}"

        echo -e "${GREEN}Added mikrotik to hosts${NC}"
        echo "${mikrotikIP} mikrotik" >> /etc/hosts
    fi
fi

# Install apache2
# If init do no checks
if [ "${INITMODE}" == 'false' ]; then

    # Check if apache is installed
    if service --status-all | grep -Fq 'apache2'; then
        echo -e "${GREEN}Apache already installed${NC}"
    else
        # If not test check if user want to install apache
        if [ "${TESTMODE}" == 'false' ]; then
            read -n 1 -e -p "Do you want to install apache2? y/n" prompt
            if [[ ${prompt} =~ ^[Yy]$ ]]; then
                hasApache='true'
            fi
        fi
    fi

fi

# Check if apache is installed
if service --status-all | grep -Fq 'apache2'; then
    hasApache='true'
    apt-get -y install libapache2-mod-wsgi-py3
    a2enmod headers
    service apache2 restart
fi

# Set flask config
rng_key1="$(hexdump -n 16 -e '4/4 "%08x" 1 ""' /dev/urandom)"
rng_key2="$(hexdump -n 16 -e '4/4 "%08x" 1 ""' /dev/urandom)"

sed -i -E "s/^;(secret_key[ \t]*=[ \t]*)(.*)$/\1${rng_key1}/" "${RESELACONFIG}"
sed -i -E "s/^;(security_password_salt[ \t]*=[ \t]*)(.*)$/\1${rng_key2}/" "${RESELACONFIG}"


###########################################################
# WEBSREVER CONFIG
###########################################################

echo -e "${GREEN}Webserver Configuration${NC}"
echo -e "------------------------------"

if [[ ${hasApache} == 'true' ]]; then
    # Create resela group
    echo -e "${GREEN}Creating resela group${NC}"
    getent group resela || groupadd resela

    # Create apache site file
    echo -e "${GREEN}Creating apache configuration${NC}"

    if [ "${TESTMODE}" == 'false' ]; then
        [[ -z "${WEBHOST}" ]] && read -e -i "resela.eu" -p "Webserver hostname: " hostname || hostname="${WEBHOST}"
    else
        WEBHOST='resela.eu'
    fi

    cat > "/etc/apache2/sites-available/resela.conf" << END_OF_CONFIG
<VirtualHost *:80>

    ServerName ${hostname}
    ServerAlias www.${hostname}

    WSGIDaemonProcess resela user=www-data group=www-data threads=5 home=${WEBDIR}/resela/
    WSGIScriptAlias / ${WEBDIR}/resela/resela.wsgi

    Header always append X-Frame-Options DENY

    <Directory ${WEBDIR}/resela>
        WSGIProcessGroup resela
        WSGIApplicationGroup %{GLOBAL}
        WSGIScriptReloading On
        Order deny,allow
        Allow from all
    </Directory>
</VirtualHost>
END_OF_CONFIG

    # Crete logfile
    touch "${SCRIPTPATH}/../log/resela.log"

    # Edit permissions
    chgrp -R www-data "${SCRIPTPATH}/.."
    find "${SCRIPTPATH}/.." -type f -exec chmod 660 {} \;
    chmod 660 "${SCRIPTPATH}/../log/resela.log"

    echo -e "${GREEN}Enabling apache configuration${NC}"
    a2ensite resela.conf > /dev/null
    a2dissite 000-default.conf > /dev/null
    service apache2 restart

fi

echo -e "${GREEN}Done!${NC}"
echo ""
