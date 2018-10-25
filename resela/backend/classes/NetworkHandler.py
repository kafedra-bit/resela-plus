"""
NetworkHandler.py
*****************
"""

import neutronclient.v2_0.client as netclient

from resela.app import APP


class NetworkHandler:
    """Network Handler class. Creates and manages networks. Also deletes, modifies and lists
    them."""

    def __init__(self, session):
        """Constructor for the network handler."""

        self.session = session
        self.neutron_client = netclient.Client(session=self.session)

    def create_network(self, network_name, shared=True):
        """Function that creates a network (private or public).

        :param network_name: The name of the network to be created
        :type network_name: str
        :param shared: If the network is available from all projects/users
        :type shared: bool
        :return: Network object or None (in case of error)
        """
        try:
            new_network_dict = {'name': network_name, 'admin_state_up': True,
                                'provider:physical_network': 'provider',
                                'provider:network_type': 'vlan', 'shared': shared}
            return self.neutron_client.create_network({'network': new_network_dict})

        except netclient.exceptions.OverQuotaClient as error:
            print("Exception in Network Handler - create_network:\n\t"
                  "Exceeded quota for this client")
            # Propegate errors
            raise error

        except Exception as error:
            # Propegate errors
            raise error

    def delete_network(self, network_id_to_delete):
        """Function for deleting networks. Return network object that can be used for verification.

        :param network_id_to_delete: ID of the network that is to be deleted
        :type network_id_to_delete: str
        :return: Network object of the deleted network
        """
        try:
            # if network_id_to_delete is not None and network_id_to_delete in
            # self.list_networks('id'):
            assert network_id_to_delete is not None
            deleted_network = self.neutron_client.delete_network(network_id_to_delete)

        except netclient.exceptions.NotFound:
            print("delete_network: Network ID missing")
            deleted_network = ()

        except AssertionError:
            print("delete_network: Invalid data-type on input")
            deleted_network = None

        except Exception as exc:
            # TODO: Change when logging is added
            if APP.config['DEBUG']:
                print("delete_network; " + str(type(exc)))

            deleted_network = None

        return deleted_network

    def list_networks(self, list_filter=None):
        """Function that lists networks or a set property from all of the networks, i.e. 'name'.

        :param list_filter: Which property to list from all of the networks.
        :type list_filter: str
        :return: List of networks (objects) or list of property from all of the networks
        """

        list_of_networks = self.neutron_client.list_networks()['networks']
        network_ids_filtered = list()
        try:
            assert isinstance(list_of_networks, list)
            temporary_network_dict = list_of_networks[0]
            assert isinstance(temporary_network_dict, dict)
            if list_filter is not None and list_filter in temporary_network_dict.keys():
                for item in list_of_networks:
                    network_ids_filtered.append(item[list_filter])

            else:
                return list_of_networks

        except Exception as exc:
            # TODO: Change when logging is added
            if APP.config['DEBUG']:
                print(exc.args)

            return None

        return network_ids_filtered

    def modify_network(self, network_id, network_name=None, port_security_enabled=None,
                       shared=False):
        """
        Modify a given property of a certain network.

        :param network_id: Mandatory parameter, UUID of existing network
        :type port_security_enabled: bool
        :param network_name: Network name to change to
        :type network_name: str
        :param port_security_enabled: If port security should be enabled or not
        :type network_id: UUID - str
        :param shared:
        :type shared: bool
        :return: None or dict containing properties of modified network
        """
        try:
            network_dict = dict()
            if network_name is None and port_security_enabled is None and shared is None:
                return None

            elif network_name is not None:
                assert isinstance(network_name, str)
                network_dict['name'] = network_name

            elif port_security_enabled is not None:
                assert isinstance(port_security_enabled, bool)
                network_dict['port_security_enabled'] = port_security_enabled

            elif shared is not None:
                assert isinstance(shared, bool)
                network_dict['shared'] = shared

            modified_network = self.neutron_client.update_network(network_id,
                                                                  {'network': network_dict})

        except AssertionError:
            print("modify_network: Invalid data-type on input")
            modified_network = None

        except netclient.exceptions.NotFound:
            print("modify_network: Network ID missing")
            modified_network = None

        except Exception as exc:
            # TODO: Change when logging is added
            if APP.config['DEBUG']:
                print("modify_network: " + str(type(exc)))

            modified_network = None

        return modified_network

    def show_network(self, network_id):
        """Display a network.

        :param network_id: the ID of the network to display.
        :return: None or dict containing the network
        """

        try:
            result = self.neutron_client.show_network(network=network_id)['network']

        except netclient.exceptions.NotFound:
            print("Could not find network.")
            result = None

        except Exception as error:
            # TODO: Change when logging is added
            if APP.config['DEBUG']:
                print(error)

            result = None

        return result

    # TODO(jiah): These errors need to be handled and notify user on error
    def create_subnet(self, network_id, subnet_name, cidr):
        """Creates a subnet belonging to an network the CIDR needs to specified along with start and
        end addresses of the allocation pool and ip version.

        :param network_id: id of the network the subnet attaches to
        :type network_id: str
        :param subnet_name: the name of the network
        :type subnet_name: str
        :param cidr: The addresscope for the subnet "10.0.0.1/24"
        :type cidr: str
        :return: subnet object or None
        """

        try:
            # TODO(jiah): Don't hardcode google dns
            new_subnet_dict = {'network_id': network_id, 'name': subnet_name, 'ip_version': 4,
                               'cidr': cidr, 'dns_nameservers': ["192.168.212.2", "192.168.0.1"]}
            new_subnet = self.neutron_client.create_subnet({'subnet': new_subnet_dict})

        except netclient.exceptions.OverQuotaClient:
            print("Exception in Network Handler - create_subnet:\n\tExceeded quota for this client")
            new_subnet = None

        except AssertionError:
            print("Create_subnet: Invalid type of parameter")
            new_subnet = None

        except netclient.exceptions.BadRequest:
            print("Create_subnet: Invalid parameter values")
            new_subnet = None

        except Exception as error:
            print(error)
            new_subnet = None

        return new_subnet

    def list_subnets(self, list_filter=None):
        """Returns a list of subnets, the filter parameter can be used to get specific fields in the
        list.

        :param list_filter: Which property to list from all of the subnets (i.e. 'id')
        :type list_filter: str
        :return: a list of subnet objects
        """
        subnet_list = self.neutron_client.list_subnets()['subnets']
        subnet_list_filtered = list()

        try:
            assert isinstance(subnet_list, list)
            temporary_subnet_dict = subnet_list[0]
            assert isinstance(temporary_subnet_dict, dict)
            if list_filter is not None and list_filter in temporary_subnet_dict.keys():
                for item in subnet_list:
                    subnet_list_filtered.append(item[list_filter])

            else:
                return subnet_list

        except Exception as error:
            # TODO: Change when logging is added
            if APP.config['DEBUG']:
                print(error)

            return None

        return subnet_list_filtered

    def delete_subnet(self, subnet_id):
        """Deletes the subnet with the given id and returns the subnet or returns None if it fails
        or subnet does not exists

        :param subnet_id: Id of the subnet to delete
        :type subnet_id: str
        :return: subnet object/None
        """

        deleted_subnet = ()
        if subnet_id is not None and subnet_id in self.list_subnets('id'):

            try:
                deleted_subnet = self.neutron_client.delete_subnet(subnet_id)

            except netclient.exceptions.NotFound:
                print("delete_subnet: subnet ID missing")
                deleted_subnet = ()

            except AssertionError:
                print("delete_subnet: Invalid data-type on input")
                deleted_subnet = None

            except Exception as error:
                # TODO: Change when logging is added
                if APP.config['DEBUG']:
                    print(error)

                deleted_subnet = None

        return deleted_subnet

    def modify_subnet(self, subnet_id, name=None):
        """Takes the id of a subnet and what parameters to update, updates the object and returns
        it.

        :param subnet_id: Id of the subnet to modify
        :type subnet_id: str
        :param name: Name of the subnet
        :type name: str
        :return: The modified subnet
        """
        try:
            subnet_dict = dict()

            if name is None:
                return None

            elif name is not None:
                assert isinstance(name, str)
                subnet_dict['name'] = name

            modified_subnet = self.neutron_client.update_subnet(subnet_id, {'subnet': subnet_dict})

        except AssertionError:
            print("Invalid data-type on input")
            modified_subnet = None

        except netclient.exceptions.NotFound:
            print("Subnet ID missing")
            modified_subnet = None

        except Exception as error:
            # TODO: Change when logging is added
            if APP.config['DEBUG']:
                print(error)

            modified_subnet = None

        return modified_subnet

        # Subnet pool

    def create_subnet_pool(self, name, prefixes, default_prefixlen=25):
        """
        Creates a subnetpool the amount of addresses available is determined by the list of
        prefixes.

        :param name: Name of the subnetpool
        :type name: str
        :param prefixes: A list of prefixes e.g ["192.168.0.0/16", "10.10.0.0/21"]
        :type prefixes: `list`
        :param default_prefixlen: The default length of the prefix in the cidr address of \
        the subnet's acquired by the pool
        :type default_prefixlen: int
        :return: a subnetpool object
        """
        try:
            assert isinstance(name, str)
            assert isinstance(prefixes, list)
            assert isinstance(default_prefixlen, int)
            new_subnetpool_dict = \
                {'name': name, 'prefixes': prefixes, 'default_prefixlen': default_prefixlen}
            new_subnetpool = \
                self.neutron_client.create_subnetpool({'subnetpool': new_subnetpool_dict})

        except netclient.exceptions.OverQuotaClient:
            print("Exception in Network Handler - create_subnet_pool:\n\t"
                  "Exceeded quota for this client")
            new_subnetpool = None

        except AssertionError:
            print("create_subnet_pool: Invalid type of parameter")
            new_subnetpool = None

        except netclient.exceptions.BadRequest:
            print("create_subnet_pool: Invalid parameter values")
            new_subnetpool = None

        except Exception as error:
            # TODO: Change when logging is added
            if APP.config['DEBUG']:
                print(type(error))
                print(error)

            new_subnetpool = None

        return new_subnetpool

    def list_subnet_pools(self, list_filter=None):
        """Returns a list of subnetpool's, the filter parameter can be used to get specific
        fields in the list.

        :param list_filter: Filter for getting out specific fields e.g id, name
        :type list_filter: str
        :return: `list` of subnet objects
        """

        subnetpool_list = self.neutron_client.list_subnetpools()['subnetpools']
        subnetpool_list_filtered = list()

        try:
            assert isinstance(subnetpool_list, list)
            temporary_subnetpool_dict = subnetpool_list[0]
            assert isinstance(temporary_subnetpool_dict, dict)
            if list_filter is not None and list_filter in temporary_subnetpool_dict.keys():
                for item in subnetpool_list:
                    subnetpool_list_filtered.append(item[list_filter])

            else:
                return subnetpool_list

        except Exception as error:
            # TODO: Change when logging is added
            if APP.config['DEBUG']:
                print(error)

            return None

        return subnetpool_list_filtered

    def delete_subnet_pool(self, subnetpool_id):
        """Deletes the subnet with the given id and returns the deleted object or returns None if it
        fails or if subnetpool does not exist.

        :param subnetpool_id: Id of the subnet to delete
        :type subnetpool_id: str
        :return: subnet object/None
        """

        deleted_subnetpool = None
        if subnetpool_id is not None and subnetpool_id in self.list_subnet_pools('id'):
            try:
                deleted_subnetpool = self.neutron_client.delete_subnetpool(subnetpool_id)

            except netclient.exceptions.NotFound:
                print("delete_subnet_pool: subnetpool ID missing")
                deleted_subnetpool = None

            except AssertionError:
                print("delete_subnet_pool: Invalid data-type on input")
                deleted_subnetpool = None

            except Exception as error:
                # TODO: Change when logging is added
                if APP.config['DEBUG']:
                    print(error)

                deleted_subnetpool = None

        return deleted_subnetpool

    def modify_subnet_pool(self, subnetpool_id, name, prefixes, default_prefixlen=None):
        """Takes the id of a subnetpool and what parameters to update, updates the object and
        returns it.

        :param subnetpool_id: Id of the subnetpool to modify
        :type subnetpool_id: str
        :param name: Name of the subnetpool
        :type name: str
        :param prefixes: A list of prefixes e.g ["192.168.0.0/16", "10.10.0.0/21"]
        :type prefixes: `list`
        :param default_prefixlen: The default length of the prefix in the cidr address of \
        the subnet's acquired by the pool
        :type default_prefixlen: int
        :return: The modified subnetpool object
        """
        try:
            subnetpool_dict = dict()

            if name is None and prefixes is None and default_prefixlen is None:
                return None

            elif name is not None:
                assert isinstance(name, str)
                subnetpool_dict['name'] = name

            elif prefixes is not None:
                assert isinstance(prefixes, list)
                subnetpool_dict['prefixes'] = prefixes

            elif default_prefixlen is not None:
                assert isinstance(default_prefixlen, str)
                subnetpool_dict['default_prefixlen'] = default_prefixlen

            modified_subnetpool = \
                self.neutron_client.update_subnet(subnetpool_id, {'subnet': subnetpool_dict})

        except AssertionError:
            print("Invalid data-type on input")
            modified_subnetpool = None

        except netclient.exceptions.NotFound:
            print("Subnetpool ID missing")
            modified_subnetpool = None

        except Exception as error:
            # TODO: Change when logging is added
            if APP.config['DEBUG']:
                print(error)

            modified_subnetpool = None

        return modified_subnetpool

    # Router
    def create_router(self, name):
        """Creates a virtual router and returns it on success.

        :param name: Name of the router
        :type name: str
        :return: a router object
        """

        try:
            new_router_dict = {'name': name}
            new_router = self.neutron_client.create_router({'router': new_router_dict})

        except Exception as error:
            # TODO: Change when logging is added
            if APP.config['DEBUG']:
                print(type(error))

            new_router = None

        return new_router

    def list_routers(self, list_filter=None):
        """Returns a list of routers, the filter parameter can be used to get specific fields in the
        list.

        :param list_filter: Filter for getting out specific fields e.g id, name
        :type list_filter: str
        :return: `list` of router objects
        """
        router_list = self.neutron_client.list_routers()['routers']
        router_list_filtered = list()

        try:
            assert isinstance(router_list, list)
            temporary_router_dict = router_list[0]
            assert isinstance(temporary_router_dict, dict)

            if list_filter is not None and list_filter in temporary_router_dict.keys():

                for item in router_list:
                    router_list_filtered.append(item[list_filter])
            else:
                return router_list

        except Exception as error:
            # TODO: Change when logging is added
            if APP.config['DEBUG']:
                print(error)
            return None

        return router_list_filtered

    def delete_router(self, router_id):
        """Deletes the router with the given id and returns the deleted object or returns None if it
        fails or if router does not exist.

        :param router_id: Id of the router to remove
        :type router_id: str
        :return:
        """
        deleted_router = None

        if router_id is not None and router_id in self.list_routers('id'):
            try:
                deleted_router = self.neutron_client.delete_router(router_id)
            except netclient.exceptions.NotFound:
                print("delete_router: Router ID missing")
                deleted_router = None
            except AssertionError:
                print("delete_router: Invalid data-type on input")
                deleted_router = None
            except Exception as error:
                # TODO: Change when logging is added
                if APP.config['DEBUG']:
                    print(error)
                deleted_router = None

        return deleted_router

    def modify_router(self, router_id, name=None, admin_state_up=None):
        """Takes the id of a router and what parameters to update, updates the object and returns
        it.

        :param router_id: Id of the router to modify
        :type router_id: str
        :param name: Name of the router
        :type name: str
        :param admin_state_up: Determines if the administrative state is up is True/False
        :type admin_state_up: bool
        :return: The modified router object
        """
        try:
            router_dict = dict()
            if name is None and admin_state_up is None:
                return None

            elif name is not None:
                assert isinstance(name, str)
                router_dict['name'] = name

            elif admin_state_up is None:
                assert isinstance(admin_state_up, bool)
                router_dict['admin_state_up'] = admin_state_up

            modified_router = self.neutron_client.update_router(router_id, {'router': router_dict})

        except AssertionError:
            print("Invalid data-type on input")
            modified_router = None

        except netclient.exceptions.NotFound:
            print("Router ID missing")
            modified_router = None

        except Exception as error:
            # TODO: Change when logging is added
            if APP.config['DEBUG']:
                print(error)

            modified_router = None

        return modified_router

    def create_router_interface(self, router_id, subnet_id):
        """Connects a subnet to a virtual router.

        :param router_id: Id of a virtual router
        :type router_id: str
        :param subnet_id: Id of the subnet to connect subnet
        :type subnet_id: str
        :return: The created router interface
        """

        try:
            new_interface_dict = {'subnet_id': subnet_id}
            new_interface = self.neutron_client.add_interface_router(router_id, new_interface_dict)

        except Exception as error:
            # TODO: Change when logging is added
            if APP.config['DEBUG']:
                print(type(error))

            new_interface = None

        return new_interface

    def delete_router_interface(self, router_id, subnet_id):
        """Disconnects a subnet from a router.

        :param router_id: Id of a virtual router
        :type router_id: str
        :param subnet_id: Id of the subnet to disconnect
        :type subnet_id: str
        :return: The deleted router interface
        """
        try:
            deleted_interface_dict = {'subnet_id': subnet_id}
            deleted_interface = \
                self.neutron_client.remove_interface_router(router_id, deleted_interface_dict)

        except Exception as error:
            # TODO: Change when logging is added
            if APP.config['DEBUG']:
                print(error)

            deleted_interface = None

        return deleted_interface

    # Floating-IP
    def list_floating_ip(self, list_filter=None):
        """Returns a list of floating ip objects, the filter parameter can be used to get specific
        fields in the list.

        :param list_filter: Filter for getting out specific fields e.g id, name
        :type list_filter: str
        :return: `list` of floating ip objects
        :rtype: `list`
        """

        floating_ip_list = self.neutron_client.list_floatingips()['floatingips']
        floating_ip_list_filtered = list()

        try:
            assert isinstance(floating_ip_list, list)
            temp_floating_ip_dict = floating_ip_list[0]
            assert isinstance(temp_floating_ip_dict, dict)

            if list_filter is not None and list_filter in temp_floating_ip_dict.keys():
                for item in floating_ip_list:
                    floating_ip_list_filtered.append(item[list_filter])

            else:
                return floating_ip_list

        except Exception as error:
            # TODO: Change when logging is added
            if APP.config['DEBUG']:
                print(error)

            return None

        return floating_ip_list_filtered

    def create_floating_ip(self, floating_network_id, port_id=None, floating_ip_address=None):
        """Creates a Floating ip and returns it on success.

        :param floating_network_id: Id of the network to get a floating ip, the network needs to\
        have a subnet attached.
        :type floating_network_id: str
        :param port_id: Port to be associated with floating ip
        :type port_id: str
        :param floating_ip_address: The floating ip address, if None it will be retrived automaticly
        :return: The created floating ip object
        """

        try:
            new_floating_ip_dict = {'floating_network_id': floating_network_id, 'port_id': port_id,
                                    'floating_ip_address': floating_ip_address}
            new_floating_ip = \
                self.neutron_client.create_floatingip({'floatingip': new_floating_ip_dict})

        except Exception as error:
            # TODO: Change when logging is added
            if APP.config['DEBUG']:
                print(error)

            new_floating_ip = None

        return new_floating_ip

    def delete_floating_ip(self, floatingip_id):
        """Deletes the floating ip with the given id and returns the deleted object or returns None if
        it fails or if router does not exist.

        :param floatingip_id: Id of the floating ip object to remove
        :type floatingip_id: str
        :return:
        """
        deleted_floating_ip = None

        if floatingip_id is not None and floatingip_id in self.list_floating_ip("id"):

            try:
                deleted_floating_ip = self.neutron_client.delete_floatingip(floatingip_id)

            except netclient.exceptions.NotFound:
                print("delete_floating ip: Floating ip ID missing")
                deleted_floating_ip = None

            except AssertionError:
                print("delete_floating ip: Invalid data-type on input")
                deleted_floating_ip = None

            except Exception as error:
                # TODO: Change when logging is added
                if APP.config['DEBUG']:
                    print(error)

                deleted_floating_ip = None

        return deleted_floating_ip

    def delete_floating_ip_by_ip(self, floating_ip):
        """Deletes the floating ip with the given id and returns the deleted object or returns None
        if it fails or if router does not exist.

        :param floating_ip: The floating IP to delete
        :type floating_ip: str
        :return: Confirmation if deletion was successful
        :rtype: bool
        """

        floating_ip_id = None
        try:
            list_of_floating_ip = self.list_floating_ip()
            print('This is the list: ' + str(type(list_of_floating_ip)))
            print('Looking for ' + str(floating_ip) + ' ' + str(type(floating_ip)))
            for item in list_of_floating_ip:
                print(item['floating_ip_address'])
                if item['floating_ip_address'] == floating_ip:
                    floating_ip_id = item['id']

            self.neutron_client.delete_floatingip(floating_ip_id)
            return True

        except Exception as exc:
            # TODO: Change when logging is added
            if APP.config['DEBUG']:
                print('Exception in delete_floating_ip_by_ip' + str(type(exc)))

            return False

    def modify_floating_ip(self, floating_ip_id, port_id=None, floating_ip_address=None):
        """Takes the id of a floating ip and what parameters to update, updates the object and
        returns it.

        :param floating_ip_id: Id of the floating ip to modify
        :type floating_ip_address: str
        :param port_id: Port to be associated with floating ip
        :type port_id: str
        :param floating_ip_address: The floating ip address
        :return: The modified floating ip object
        """

        try:
            floating_ip_dict = dict()
            if port_id is None and floating_ip_address is None:
                return None

            elif port_id is not None:
                assert isinstance(port_id, str)
                floating_ip_dict['port_id'] = port_id

            elif floating_ip_dict is not None:
                assert isinstance(floating_ip_address, str)
                floating_ip_dict['floating_ip_address'] = floating_ip_address

            modified_floating_ip = \
                self.neutron_client.update_floatingip(floating_ip_id, {'floatingip':
                                                                           floating_ip_dict})

        except AssertionError:
            print("Invalid data-type on input")
            modified_floating_ip = None

        except netclient.exceptions.NotFound:
            print("Floating ip ID missing")
            modified_floating_ip = None

        except Exception as error:
            # TODO: Change when logging is added
            if APP.config['DEBUG']:
                print(error)

            modified_floating_ip = None

        return modified_floating_ip

    # Firewall (policies)

    # VPN

    # Flavor
    def list_net_flavor(self, list_filter=None):
        """Returns a list of network flavor objects, the filter parameter can be used to get
        specific
        fields in the list.

        :param list_filter: Filter for getting out specific fields e.g id, name
        :return: `list` of network flavors
        """

        flavor_list = self.neutron_client.list_flavors()['flavors']
        flavor_list_filtered = list()

        try:
            assert isinstance(flavor_list, list)
            temp_flavor_dict = flavor_list[0]
            assert isinstance(temp_flavor_dict, dict)

            if list_filter is not None and list_filter in temp_flavor_dict.keys():

                for item in flavor_list:
                    flavor_list_filtered.append(item[list_filter])

            else:
                return flavor_list

        except Exception as error:
            # TODO: Change when logging is added
            if APP.config['DEBUG']:
                print(error)

            return None

        return flavor_list_filtered

    def create_net_flavor(self, service_type, name="", description=""):
        """Creates a network flavor and returns it.

        :param service_type: Service type e.g LOADBALANCERV2
        :type service_type: str
        :param name: Name of the network flavor
        :type name: str
        :param description: Description of the network flavor
        :return: The created network flavor
        """

        try:
            new_flavor_dict = \
                {'service_type': service_type, 'name': name, 'description': description}
            new_flavor = self.neutron_client.create_flavor({'flavor': new_flavor_dict})

        except Exception as error:
            # TODO: Change when logging is added
            if APP.config['DEBUG']:
                print(error)

            new_flavor = None

        return new_flavor

    def delete_net_flavor(self, flavor_id):
        """Deletes the network flavor with the given id and returns the deleted object or returns
        None if it fails or if router does not exist.

        :param flavor_id: Id of the flavor to delete
        :type flavor_id: str
        :return:
        """

        deleted_flavor = None

        if flavor_id is not None and flavor_id in self.list_net_flavor("id"):

            try:
                deleted_flavor = self.neutron_client.delete_flavor(flavor_id)

            except netclient.exceptions.NotFound:
                print("delete_flavor: Flavor ID missing")
                deleted_flavor = None

            except AssertionError:
                print("delete_flavor: Invalid data-type on input")
                deleted_flavor = None

            except Exception as error:
                # TODO: Change when logging is added
                if APP.config['DEBUG']:
                    print(error)

                deleted_flavor = None

        return deleted_flavor

    def modify_flavor(self, net_flavor_id, name=None, description=None, enabled=None):
        """Takes the id of a network flavor and what parameters to update, updates the object and
        returns it.

        :param net_flavor_id: Id of the network flavor to modify
        :type net_flavor_id: str
        :param name: Name of the flavor
        :type name: str
        :param description: Description of the flavor
        :type description: str
        :param enabled: Indicates if the flavor is enabled is True/False
        :type enabled: bool
        :return: The modified network flavor
        """

        try:
            net_flavor_dict = dict()
            if name is None and description is None and enabled is None:
                return None

            elif name is not None:
                assert isinstance(name, str)
                net_flavor_dict['name'] = name

            elif description is not None:
                assert isinstance(description, str)
                net_flavor_dict['description'] = description

            elif enabled is not None:
                assert isinstance(enabled, bool)
                net_flavor_dict['enabled'] = None

            modified_net_flavor = \
                self.neutron_client.update_flavor(net_flavor_id, {'flavor': net_flavor_dict})

        except AssertionError:
            print("Invalid data-type on input")
            modified_net_flavor = None

        except netclient.exceptions.NotFound:
            print("Flavor ID missing")
            modified_net_flavor = None

        except Exception as error:
            # TODO: Change when logging is added
            if APP.config['DEBUG']:
                print(error)

            modified_net_flavor = None

        return modified_net_flavor

    # Port
    def list_ports(self, list_filter=None):
        """Returns a list of port objects, the filter parameter can be used to get specific
        fields in the list.

        :param list_filter: Filter for getting out specific fields e.g id, name
        :type list_filter: str
        :return: `list` of ports
        """
        port_list = self.neutron_client.list_ports()['ports']
        port_list_filtered = list()

        try:
            assert isinstance(port_list, list)
            temp_port_dict = port_list[0]
            assert isinstance(temp_port_dict, dict)

            if list_filter is not None and list_filter in temp_port_dict.keys():

                for item in port_list:
                    port_list_filtered.append(item[list_filter])

            else:
                return port_list

        except Exception as error:
            # TODO: Change when logging is added
            if APP.config['DEBUG']:
                print(error)

            return None

        return port_list_filtered

    def create_port(self, network_id, name):
        """Creates a port belonging to a given network.

        :param network_id: Id of the network the port belongs to
        :type network_id: str
        :param name: name for the port
        :type name: str
        :return: The created port object
        """

        try:
            new_port_dict = {'network_id': network_id, 'name': name, 'admin_state_up': True}
            new_port = self.neutron_client.create_port({'port': new_port_dict})

        except Exception as error:
            # TODO: Change when logging is added
            if APP.config['DEBUG']:
                print(error)

            new_port = None

        return new_port

    def delete_port(self, port_id):
        """ Deletes the port with the given id and returns the deleted object or returns None if it
        fails or if router does not exist.

        :param port_id: id of the port to remove
        :type port_id: str
        :return:
        """
        deleted_port = None

        if port_id is not None and port_id in self.list_ports("id"):

            try:
                deleted_port = self.neutron_client.delete_port(port_id)

            except netclient.exceptions.NotFound:
                print("delete_port: Port ID missing")
                deleted_port = None

            except AssertionError:
                print("delete_port: Invalid data-type on input")
                deleted_port = None

            except Exception as error:
                # TODO: Change when logging is added
                if APP.config['DEBUG']:
                    print(error)

                deleted_port = None

        return deleted_port

    def modify_port(self, port_id, name=None, admin_state_up=None):
        """Takes the id of a port and what parameters to update, updates the object and returns it.

        :param port_id: Id of the port to modify
        :param name: Name of the port
        :param admin_state_up: Indicates if the port is enabled, is True/False
        :return: The modified port object
        """

        try:
            port_dict = dict()
            if name is None and admin_state_up is None:
                return None

            elif name is not None:
                assert isinstance(name, str)
                port_dict['name'] = name

            elif admin_state_up is not None:
                assert isinstance(admin_state_up, bool)
                port_dict['admin_state_up'] = admin_state_up

            modified_port = self.neutron_client.update_port(port_id, {'port': port_dict})

        except AssertionError:
            print("Invalid data-type on input")
            modified_port = None

        except netclient.exceptions.NotFound:
            print("Port ID missing")
            modified_port = None

        except Exception as error:
            # TODO: Change when logging is added
            if APP.config['DEBUG']:
                print(error)

            modified_port = None

        return modified_port

    def quota_available(self, quota_type, list_length):
        """Takes a quota type and a length of a list with the same type and calculates if there are
        resources available.

        :param quota_type: type of quota (network, subnet, etc ...)
        :type quota_type: str
        :param list_length: length of the list of a (network, subnet, etc ...)
        :type list_length: int
        :return: number of available resources
        """

        try:
            assert isinstance(quota_type, str)
            quota = self.neutron_client.show_quota(self.neutron_client.get_quotas_tenant())['quota']
            assert isinstance(quota, dict)
            assert isinstance(list_length, int)
            quota_left = quota[quota_type] - list_length
            if quota_left < 0:
                quota_left = 0

            return quota_left
        except AssertionError:
            print("Invalid data-type on input")

        except Exception as error:
            # TODO: Change when logging is added
            if APP.config['DEBUG']:
                print(error)

            return None

    def quota_limit(self, quota_type):
        """Takes a quota type and a length of a list with the same type and calculates if there are
        resources available.

        :param quota_type: type of quota (network, subnet, etc ...)
        :type quota_type: str
        :return: quota limit
        """

        try:
            assert isinstance(quota_type, str)
            quota = self.neutron_client.show_quota(self.neutron_client.get_quotas_tenant())['quota']
            assert isinstance(quota, dict)
            assert quota_type in quota.keys()
            quota_limit = quota[quota_type]
            return quota_limit

        except AssertionError:
            print("Invalid data-type on input")

        except Exception as error:
            # TODO: Change when logging is added
            if APP.config['DEBUG']:
                print(error)

            return None

    def get_seg_id(self, network_id):
        """Takes a network id and returns the networks segmentation id, this id is unique for each
        network.

        :param network_id: Id of a network
        :type network_id: str
        :return: Network segmentation id
        """

        segid = None
        try:
            assert isinstance(network_id, str)
            network = self.neutron_client.list_networks(id=network_id)['networks']
            segid = network[0]['provider:segmentation_id']

        except AssertionError:
            print("invalid data type")

        except Exception as error:
            # TODO: Change when logging is added
            if APP.config['DEBUG']:
                print(type(error))

        return segid

    def delete_user_network(self, network_id):
        """Takes the network id belonging to a user and deletes it along with the interface port and
        subnet that belongs to it.

        :param network_id: The users network id
        :type network_id: str
        :return:
        """

        try:
            assert isinstance(network_id, str)
            subnet = self.neutron_client.list_subnets(network_id=network_id)['subnets']
            subnet_id = subnet[0]['id']

            if subnet_id is not None:
                self.delete_subnet(subnet_id)

            self.delete_network(network_id)

        except AssertionError:
            print("invalid data type")

        except Exception as error:
            # TODO: Change when logging is added
            if APP.config['DEBUG']:
                print(type(error))

    def create_security_group(self, tenant_id, name='default', description=None):
        """This function is only usable by administrators. It is used to create a security group for
        another project based on ID

        :param tenant_id: ID of project on which the security group will be created
        :type tenant_id: str
        :param name: Name of the security group, 'default' is the default value
        :type name: str
        :param description: Description for the security group. If none: generated using name
        :type description: str
        :return: ID of created security group or none
        :rtype: str
        """

        try:
            if description is None:
                description = name + ' security group'

            new_security_group_dict = \
                {'name': name, 'tenant_id': tenant_id, 'description': description}

            print('Creating security group for project: ' + str(tenant_id))
            new_security_group_id = \
                self.neutron_client.create_security_group(
                    {'security_group': new_security_group_dict}
                )['security_group']['id']

        except Exception as error:
            # TODO: Change when logging is added
            if APP.config['DEBUG']:
                print('Failed create_security_group: ' + str(error) + ' - ' + str(type(error)))

            new_security_group_id = None

        return new_security_group_id

    def delete_security_group_by_tenant(self, tenant_id, name):
        """This function can be used to delete a security group based on the tenant(/project) ID and
        name.

        :param tenant_id: Project id from which to delete the security group
        :type tenant_id: str
        :param name: Name of the security group to delete (i.e. 'default')
        :type name: str
        :return: True or False depending on success
        :rtype: bool
        """

        try:
            security_group_list = self.neutron_client.list_security_groups()['security_groups']
            security_group_to_delete = None
            for item in security_group_list:
                if item['tenant_id'] == tenant_id and item['name'] == name:
                    security_group_to_delete = item['id']
                    break

            print('delete_security_group_by_tenant deleting: ' +
                  str(type(security_group_to_delete)) + ' ' + str(security_group_to_delete))
            # security_dict = {'name': name, 'tenant_id': tenant_id}

            assert not isinstance(security_group_to_delete, None)
            self.neutron_client.delete_security_group(security_group_to_delete)
            return True

        except Exception as error:
            # TODO: Change when logging is added
            if APP.config['DEBUG']:
                print('Failed delete_security_group_by_tenant due to: ' + str(error) + ' - ' +
                      str(type(error)))

            return False

    def delete_security_group(self, security_group_id):
        """Delete a security group by id.

        :param security_group_id: ID of security group delete
        :return:
        """

        try:
            self.neutron_client.delete_security_group(security_group_id)
            return True

        except Exception as error:
            # TODO: Change when logging is added
            if APP.config['DEBUG']:
                print('Failed delete_security_group due to: ' + str(error) + ' - ' +
                      str(type(error)))

            return False
