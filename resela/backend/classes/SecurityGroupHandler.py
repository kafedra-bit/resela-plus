"""
SecurityGroupHandler.py
***********************
"""

from neutronclient.v2_0 import client
from flask import current_app

class SecurityGroupHandler:
    """Security group handler class. Used to manage the security groups in the ReSeLa project.
    Security groups works like virtual firewalls."""

    def __init__(self, session):
        """Constructor for the security group handler class.

        :param session: session from authentication
        :return: initiated SecurityGroupHandler
        """

        # handle input parameters
        self.session = session
        self.neutron_client = client.Client(session=self.session)

    def create(self, name, description, tenant_id):
        """Creates a new security group.

        :param name: name of the security group to create
        :param description: description of the security group to create
        :param tenant_id: id of the project where the security group will be created
        :return: SecurityGroupObject for the newly created security group
        """

        try:
            body = {'security_group': {'name': name, 'description': description, 'tenant_id':
                                       tenant_id}}
            return self.neutron_client.create_security_group(body=body)

        except Exception as error:
            print(error)

    def delete(self, security_group_id):
        """Deletes the security group with the specified id.

        :param security_group_id: id of the security group to delete
        :return:
        """

        try:
            self.neutron_client.delete_security_group(security_group_id)

        except Exception as error:
            print(error)

    def list(self):
        """List the security groups for the current project.

        :return: a list of security group objects
        """

        try:
            return self.neutron_client.list_security_groups()
        except Exception as error:
            print(error)

    def list_all(self):
        """List all the security groups on the system.

        :return: a list of security group objects
        """

        try:
            return self.neutron_client.list_security_groups()

        except Exception as error:
            print(error)

    def create_rule(self, security_group_id, direction, ethertype, protocol=None, description="",
                    port_range_min=None, port_range_max=None, remote_ip_prefix=None):
        """Creates a new rule on a security group with the specified properties.

        :param security_group_id: the id of the security group the rule should apply to
        :param direction: direction of traffic (egress/ingress)
        :param ethertype: IPv4 or IPv6
        :param protocol: string (icmp/tcp/udp)
        :param description: optional description of the rule
        :param port_range_min: beginning of the port range that should be allowed
        :param port_range_max: end of the port range that should be allowed
        :param remote_ip_prefix: network that should be allowed (0.0.0.0/0 for any)
        :return:
        """

        rule_dict = {'security_group_rule':
                         {'security_group_id': security_group_id, 'direction': direction,
                          'ethertype': ethertype, 'protocol': protocol, 'description': description,
                          'port_range_min': port_range_min, 'port_range_max': port_range_max,
                          'remote_ip_prefix': remote_ip_prefix
                         }
                    }

        try:
            self.neutron_client.create_security_group_rule(rule_dict)

        except Exception as error:
            print(error)

    def delete_all_rules(self, security_group_id):
        """Removes all rules from the selected security group.

        :param security_group_id: id of the security group to clear of rules.
        :return:
        """

        # Find group
        security_group = self.neutron_client.show_security_group(security_group=security_group_id)

        # Get a list of rules
        rules = security_group['security_group']['security_group_rules']

        # Go through list of rules and delete them
        try:
            for rule in rules:
                self.neutron_client.delete_security_group_rule(rule['id'])

        except Exception as error:
            print(error)

    @staticmethod
    def create_security_groups(lab, lab_session):
        security_handler = SecurityGroupHandler(lab_session)
        base_network = current_app.iniconfig.get('network', 'basenetwork') + '/16'
        # Create internet group
        internet_group = security_handler.create(name="internet",
                                                 description='Allow internet access',
                                                 tenant_id=lab.id)
        # Clear default rules
        security_handler.delete_all_rules(internet_group['security_group']['id'])

        # Create new internet (No internet)
        security_handler.create_rule(security_group_id=internet_group['security_group']['id'],
                                     description=lab.name, direction='ingress',
                                     ethertype='IPv4')
        security_handler.create_rule(security_group_id=internet_group['security_group']['id'],
                                     description=lab.name, direction='egress', ethertype='IPv4')
        # Create no-internet group
        no_internet_group = security_handler.create(name="no-internet",
                                                    description='Do not allow internet access',
                                                    tenant_id=lab.id)
        # Clear default rules
        security_handler.delete_all_rules(no_internet_group['security_group']['id'])
        # Create new internet (No internet)
        security_handler.create_rule(
            security_group_id=no_internet_group['security_group']['id'], direction='ingress',
            ethertype='IPv4')
        security_handler.create_rule(
            security_group_id=no_internet_group['security_group']['id'], direction='egress',
            ethertype='IPv4', remote_ip_prefix=base_network,
            description='Only local egress traffic.')
