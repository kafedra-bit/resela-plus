"""
MikrotikManager.py
******************
"""

from contextlib import contextmanager

import paramiko

from resela.app import APP
from resela.backend.classes.NetworkHandler import NetworkHandler
from resela.backend.managers.ManagerException import UserManagerCreationFail

# TODO(jiah): Bind to self instead of global
FIRST_ADDRESS = 1
LAST_ADDRESS = 14


class MikrotikManager:
    """An interface for all the functions ReSeLa uses with thr mikrotik"""

    def __init__(self):
        """Initiate an SSH connection to the mikrotik"""

        config = APP.iniconfig['mikrotik']
        self.hostname = config.get('host')
        self.username = config.get('user')
        self.password = config.get('pass')
        self.port = config.getint('port')

    @contextmanager
    def ssh_connect(self):
        """SSH connect wrapper for use with `with` statements."""
        ssh_client = paramiko.SSHClient()
        # Auto accepts the fingerprint verification.
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(
            hostname=self.hostname,
            username=self.username,
            password=self.password,
            port=self.port,
            allow_agent=False,
            look_for_keys=False
        )
        try:
            yield ssh_client
        finally:
            ssh_client.close()

    def update_password(self, user_new_pass, user_email):
        """
        Update the VPN password for a given user

        :param user_new_pass: The new password
        :type user_new_pass: str
        :param user_email: The mikrotik user of which the password should
        :type user_email: str
        :raises SSHException: When the server fails to execute a command
        """

        with self.ssh_connect() as ssh_client:
            cmd = '/ppp secret set password=%s [find where name=%s]' \
                  % (user_new_pass, user_email)
            ssh_client.exec_command(cmd)

        return 'Success'

    def create_vpn_user(self, user_email, password):
        """
        Create VPN user with email as username

        :param user_email: The username for the VPN user
        :type user_email: str
        :param password: The password for the VPN user
        :type password: str
        :raises SSHException: When the server fails to execute a command
        """
        with self.ssh_connect() as ssh_client:
            cmd = '/ppp secret add name=%s service=pptp password=%s' \
                  % (user_email, password)
            ssh_client.exec_command(cmd)

        return 'Success'

    def delete_vpn_user(self, user_email):
        """
        Unbind and delete a specified VPN user

        :param user_email: The username of the deletee
        :type user_email: str
        :raises SSHException: When the server fails to execute a command
        """
        with self.ssh_connect() as ssh_client:
            cmd = '/ppp secret remove %s' \
                  % user_email
            ssh_client.exec_command(cmd)

        return 'Success'

    def bind_vpn_to_vlan(self, vlan, user_email):
        """
        Bind a specified vlan to a specified VPN user

        :param vlan: The vlan tag to be bind to a user
        :type vlan: str
        :param user_email: The user to be bound to a vlan
        :type user_email: str
        :raises SSHException: When the server fails to execute a command
        """
        pptp_name = 'pptp-vlan' + str(vlan)
        with self.ssh_connect() as ssh_client:
            cmd = '/ppp secret set %s profile=%s' \
                  % (user_email, pptp_name)
            ssh_client.exec_command(cmd)
        return 'Success'

    def unbind_vpn_to_vlan(self, user_email):
        """
        Unset the binding of a specified user

        :param user_email: The specified users username
        :type user_email: str
        :raises SSHException: When the server fails to execute a command
        """

        with self.ssh_connect() as ssh_client:
            cmd = '/ppp secret set %s profile=default' \
                  % user_email
            ssh_client.exec_command(cmd)
        return 'Success'

    def create_vlan(self, vlan):
        """
        Create a VLAN
        The VLAN is created in 4 steps.
        1. Create the vlan interface
        2. Add addresses to the VLAN
        3. Create VPN profile
        4. Create firewall rule

        :param vlan: Vlan tag to be used
        :type vlan: int
        :raises SSHException: When the server fails to execute a command
        """
        cidr = self.get_cidr_for_subnet(vlan)
        local_address, remote_address = self.vpn_addresses_vlan(cidr)
        network, mask = cidr.split('/')

        with self.ssh_connect() as ssh_client:
            cmd = '/interface vlan add arp=proxy-arp interface=bridge-provider name=vlan%s vlan-id=%s' \
                  % (str(vlan), str(vlan))
            ssh_client.exec_command(cmd)

            cmd = """
                /ppp profile add name=pptp-vlan%s local-address=%s remote-address=%s use-mpls=default only-one=yes
                use-compression=default use-encryption=required change-tcp-mss=default use-upnp=default address-list=""
                """ % (str(vlan), local_address, remote_address)
            ssh_client.exec_command(cmd)

            cmd = "/ip address add address=%s/28 interface=vlan%s network=%s comment=vlan%s" \
                  % (local_address, str(vlan), network, str(vlan))
            ssh_client.exec_command(cmd)

            cmd = "/ip firewall filter add chain=forward dst-address=%s src-address=%s comment=vlan%s" \
                  % (cidr, cidr, str(vlan))
            ssh_client.exec_command(cmd)
            cmd = "/ip firewall filter move [find where comment=vlan%s] destination=14" \
                  % vlan
            ssh_client.exec_command(cmd)
        return 'Success'

    def delete_vlan(self, vlan): 
        """
        Delete a VLAN from the mikrotik
        The deletion follows 4 steps, the reverse order of create vlan
        1. Remove firewall filter
        2. Remove VPN profile
        3. Remove addresses from VLAN
        4. Remove VLAN interface

        :param vlan: The VLAN tag of the vlan to be removed
        :type vlan: int
        :raises SSHException: When the server fails to execute a command
        """

        with self.ssh_connect() as ssh_client:
            cmd = '/ip firewall filter remove [find where comment=vlan%s]' \
                  % (str(vlan))
            ssh_client.exec_command(cmd)

            cmd = '/ppp profile remove pptp-vlan%s'\
                  % str(vlan)
            ssh_client.exec_command(cmd)

            cmd = '/ip address remove [find where comment=vlan%s]' \
                  % str(vlan)
            ssh_client.exec_command(cmd)

            cmd = "/interface vlan remove vlan%s" \
                  % str(vlan)
            ssh_client.exec_command(cmd)

        return 'Success'

    @staticmethod
    def vpn_addresses_vlan(cidr):
        """Calculate and return first host address in the VLAN and the last host address.

        These will be used in the VPN configuration in the Mikrotik. The first host address is for the gateway, and the
        last one is for the remote vpn user.

        :param cidr: The network address with subnet mask length.
        :type cidr: str
        :return: local host address and remote host address
        :rtype: str, str
        """
        # Split the network address into four parts.
        a, b, c, d = cidr.split('.')
        # Extract the last network piece from the network mask.
        host, mask = d.split('/')
        # Calculate the new addresses.
        local = str(int(host) + FIRST_ADDRESS)
        remote = str(int(host) + LAST_ADDRESS)

        return '%s.%s.%s.%s' % (a, b, c, local), '%s.%s.%s.%s' % (a, b, c, remote)

    @staticmethod
    def get_cidr_for_subnet(vlan_number):
        """
        Calculates the full cidr depending on the vlan-number provided
        by openstack. The calculations makes it possible to dynamically
        create up to 4096 vlans.

        with then calculation the following cidrs will be created
        vlan 1:     10.2.0.0/28
        vlan 19:    10.2.1.32/28
        vlan 105:   10.2.6.128/28
        vlan 2674:  10.2.167.16/28
        vlan 3921:  10.2.245.0/28

        :param vlan_number: VLAN-id
        :type vlan_number: int
        :return: VLAN network address
        :rtype: str
        """
        config = APP.iniconfig['network']
        base = config.get('basenetwork')
        a, b, c, d = base.split('.')
        tag = vlan_number - 1
        x = int(tag / 16)
        y = int((tag % 16) * 16)

        return '%s.%s.%s.%s/28' % (a, b, x, y)