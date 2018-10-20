#!/usr/bin/env bash
#
# Docker image setup
#
# Author: Jim Ahlstrand
# Copyright 2017 resela

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

PRODDIR="$(realpath -s "${SCRIPTPATH}/Docker/Prod-env")"
TESTDIR="$(realpath -s "${SCRIPTPATH}/Docker/Test-env")"
WEBDIR="$(realpath -s "/var/www/resela")"
LOGDIR="$(realpath -s "/var/log/apache2")"
LEDIR="$(realpath -s "/etc/letsencrypt")"
STARTSCRIPT="$(realpath -s "${SCRIPTPATH}/Docker/start.sh")"
STARTSCRIPTPATH="/usr/bin/"

BUILDTEST='false'

# Check parameters
while getopts ":th" opt
  do
    case "$opt" in
      "t")
        # Testmode is NOT intended for end users, it's only use is to generate a
        # config that works with development CI
        BUILDTEST='true'
        ;;
      "h")
        echo -e "${GREEN}ReSeLa+ docker application setup${NC}"
        echo -e "This script builds a docker container for the resela application"
        echo -e "\t® 2017 resela"
        echo ""
        echo -e "\t-t\tBuild resela docker image for automatic testing with CI"
        echo -e "\t-h\tDisplay this help"
        exit 1
        ;;
      "?")
        echo -e "${RED}Unknown option ${OPTARG}${NC}" 1>&2
        exit 1
        ;;
      ":")
        echo "No argument value for option ${OPTARG}"
        ;;
      *)
      # Should not occur
        echo -e "${RED}Unknown error while processing options${NC}" 1>&2
        exit 1
        ;;
    esac
  done

# Make sure docker is installed
# type docker >/dev/null 2>&1 || { echo -e "${RED}Docker is not installed!${NC}" 1>&2; exit 1; }
if ! type docker >/dev/null 2>&1; then
    # Install docker
    echo -e "${RED}Docker is not installed!${NC}"
    echo -e "${GREEN}Installing docker${NC}"
    apt-get -qy install apt-transport-https ca-certificates curl software-properties-common
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -
    apt-key fingerprint 0EBFCD88
    sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
    apt-get update
    apt-get -qy install docker-ce
fi

# Create necessary folders
mkdir -p ${WEBDIR}
mkdir -p ${LOGDIR}
mkdir -p ${LEDIR}

# Make sure the requirements.txt is present
if [ ! -f "$(realpath -s "${SCRIPTPATH}/requirements.txt")" ]; then
    echo -e "${RED}requirements.txt is missing!${NC}" 1>&2
    exit 1
fi

# Make sure the application.ini is present
if [ ! -f "$(realpath -s "${SCRIPTPATH}/application.ini")" ]; then
    echo -e "${RED}application.ini is missing!${NC}" 1>&2
    exit 1
fi

# Download resela
git clone -b production https://gitlab.resela.eu/resela/resela.git ${WEBDIR}
# Copy application.ini
cp ${SCRIPTPATH}/application.ini ${WEBDIR}/resela/config/application.ini
# Crete logfile
touch "${WEBDIR}/log/resela.log"

# Edit permissions
chgrp -R www-data "${WEBDIR}"
find "${WEBDIR}" -type f -exec chmod 660 {} \;
chmod 660 "${WEBDIR}/log/resela.log"

# Make sure firewall rules are set
if iptables -S | grep -q -E "\-P FORWARD DROP"; then
    # Allow forward
    echo -e "${GREEN}Adding firewall rules${NC}"
    iptables -P FORWARD ACCEPT

    # Install persistent iptables
    echo -e "${GREEN}Installing persistent iptables${NC}"
    debconf-set-selections <<< "iptables-persistent iptables-persistent/autosave_v4 boolean true"
    debconf-set-selections <<< "iptables-persistent iptables-persistent/autosave_v6 boolean true"
    apt-get -yq install iptables-persistent
    iptables-save > /etc/iptables/rules.v4
fi

# If test mode build resela:test
if [[ "${BUILDTEST}" == 'true' ]]; then
    echo -e "${GREEN}Building docker image 'resela:test'${NC}"
    docker build -t resela:test -f "${TESTDIR}/Dockerfile" "${SCRIPTPATH}"
else
    # Else build normal resela for production
    echo -e "${GREEN}Building docker image 'resela'${NC}"
    docker build -t resela -f "${PRODDIR}/Dockerfile" "${SCRIPTPATH}"
fi

# Adding start resela to startup
if [ ! -f "${STARTSCRIPTPATH}/startresela.sh" ]; then
    # Copy start scrit
    echo -e "${GREEN}Enabling autostart${NC}"
    cp "${STARTSCRIPT}" "${STARTSCRIPTPATH}/startresela.sh"

    # Hook to systemd
    cat > "/etc/systemd/system/resela.service" << END_OF_CONFIG
[Unit]
Description=Start ReSeLa docker application

[Service]
Type=oneshot
ExecStart=${STARTSCRIPTPATH}/startresela.sh

[Install]
WantedBy=multi-user.target
END_OF_CONFIG
    chmod 644 /etc/systemd/system/resela.service
    systemctl enable resela
fi