"""
InstanceHandler.py
******************
"""

import time
import novaclient.client as nclient

from resela.app import APP


class InstanceHandler:
    """Instance Handler class. Used to create, start, manage and delete instances."""

    def __init__(self, session, instance_id=None):
        """Constructor for the Instance Handler class.

        :param session: session from authentication
        :param string instance_id: the id of the instance to edit, defaults to None
                                    may be left out but with limited functionality
        :return: initiated InstanceHandler
        """

        # handle input parameters
        self.session = session
        self.__instance = None
        self.nova_client = nclient.Client(version='2.19',
                                          session=self.session)

        if instance_id is not None:
            try:
                self.__instance = self.nova_client.servers.get(instance_id)

            except Exception as error:
                # TODO: Change when logging is added
                if APP.config['DEBUG']:
                    print(error)

    def create(self, instance_name, image_name, flavor_name, net_ids, internet):
        """Creates an instance with the given parameters and saves the instance-object.

        :param string instance_name: name of the instance to be created
        :param string image_name: name of the image to use
        :param string flavor_name: name of the flavor to use
        :param string[] net_ids: a list of strings containing uid's of
                                networks this instance should be connected to
        :param internet:
        :return: None
        """

        instance = None
        nics = []

        for net in net_ids:
            nics = [{'net-id': net}]

        # get image,flavor, networks
        try:
            image = self.nova_client.images.find(name=image_name)
            flavor = self.nova_client.flavors.find(name=flavor_name)
            # create instance
            instance = self.nova_client.servers.create(name=instance_name, image=image,
                                                       flavor=flavor, nics=nics,
                                                       description=image_name.rsplit('|', 1)[1])

            time.sleep(1)
            if internet != 'True':
                self.nova_client.servers.remove_security_group(instance.id, "default")
                self.nova_client.servers.add_security_group(instance.id, "no-internet")
            else:
                self.nova_client.servers.remove_security_group(instance.id, "default")
                self.nova_client.servers.add_security_group(instance.id, "internet")

        except Exception as error:
            # TODO: Change when logging is added
            if APP.config['DEBUG']:
                print(error)

        if instance is not None:
            self.__instance = instance

    def start(self):
        """Generic function for starting/resuming instances.

        :return: None
        """

        status = None

        try:
            status = self.get_status()

        except Exception as error:
            # TODO: Change when logging is added
            if APP.config['DEBUG']:
                print(error)

        if status == 'SHUTOFF':
            try:
                self.__instance.start()

            except Exception as error:
                # TODO: Change when logging is added
                if APP.config['DEBUG']:
                    print(error)

        elif status == 'SUSPENDED':
            try:
                self.__instance.resume()

            except Exception as error:
                # TODO: Change when logging is added
                if APP.config['DEBUG']:
                    print(error)

    def manage(self, name):
        """Function for changing the name of an instance.

        :param string name: the new name for the instance
        :return: None
        """

        # TODO: Should this do more?

        try:
            self.__instance.update(name)

        except Exception as error:
            # TODO: Change when logging is added
            if APP.config['DEBUG']:
                print(error)

    def delete(self):
        """Function for deleting an instance.

        :return: None
        """

        if self.__instance is None:
            return None

        else:
            try:
                self.__instance.delete()
                return True

            except Exception as error:
                # TODO: Change when logging is added
                if APP.config['DEBUG']:
                    print(error)

                return False

    def suspend(self):
        """Function for suspending an instance.

        :return: None
        """

        if self.__instance is None:
            return None

        else:
            if self.get_status() == 'ACTIVE':

                try:
                    self.__instance.suspend()

                except Exception as error:
                    # TODO: Change when logging is added
                    if APP.config['DEBUG']:
                        print(error)

    def snapshot(self):
        """Function for taking a snapshot (not implemented yet).

        :return: None
        """
        # TODO:Implement function snapshot

        return None

    def stop(self):
        """Function for stopping an instance.

        :return: None
        """

        if self.__instance is None:
            return None

        else:
            if self.get_status() == 'ACTIVE':

                try:
                    self.__instance.stop()

                except Exception as error:
                    # TODO: Change when logging is added
                    if APP.config['DEBUG']:
                        print(error)

    def reboot(self, reboot_type='SOFT'):
        """Function for rebooting an instance.

        :param string reboot_type: reboot type, can be set to 'SOFT' or 'HARD' (defaults to soft)
        :return: None
        """

        if self.__instance is None:
            return None

        else:
            if self.get_status() == 'ACTIVE':

                try:
                    self.__instance.reboot(reboot_type)

                except Exception as error:
                    # TODO: Change when logging is added
                    if APP.config['DEBUG']:
                        print(error)

    def reset(self):
        """Function that resets the instance to its original state.

        :return: None
        """

        # todo: should we check state ???

        if self.__instance is None:
            return None

        else:
            try:
                self.__instance.rebuild(self.__instance.image.get('id'))

            except Exception as error:
                # TODO: Change when logging is added
                if APP.config['DEBUG']:
                    print(error)

    def list(self):
        """Function that lists all instances.

        :return: server[], `list` of instances
        """

        try:
            return self.nova_client.servers.list()

        except Exception as error:
            # TODO: Change when logging is added
            if APP.config['DEBUG']:
                print(error)

    def list_all(self, user_id=None):
        """Function that lists all instances.

        :param user_id: If a specific user_id is given, filter on user_id
        :return: server[] `list` of instances
        """

        if user_id:
            search_opts = {'all_tenants': True, 'user_id': user_id}
        else:
            search_opts = {'all_tenants': True}

        try:
            return self.nova_client.servers.list(detailed=True, search_opts=search_opts)

        except Exception as error:
            # TODO: Change when logging is added
            if APP.config['DEBUG']:
                print(error)

    def get_instance_id(self):
        """Get id of current instance.

        :return string: id of this instance
        """

        if self.__instance is not None:
            return self.__instance.id

        else:
            raise ValueError("instance has not been set")

    def get_instance_name(self):
        """Get name of current instance.

        :return string: name of this instance
        """

        if self.__instance is not None:
            return self.__instance.name

        else:
            raise ValueError("instance has not been set")

    def get_instance(self):
        """Function that updates returns an instance (this).

        :return server: this instance
        """

        if self.__instance is not None:
            try:
                self.__instance = self.nova_client.servers.get(self.__instance.id)
                return self.__instance

            except Exception as error:
                # TODO: Change when logging is added
                if APP.config['DEBUG']:
                    print(error)

        else:
            return None

    def set_instance(self, instance_id):
        """Sets the instance to be used.

        :param string instance_id: instance uid to use
        :return server: this instance
        """

        if self.__instance is None:
            try:
                self.__instance = self.nova_client.servers.get(instance_id)

            except Exception as error:
                # TODO: Change when logging is added
                if APP.config['DEBUG']:
                    print(error)

    def get_status(self):
        """Gets the status of an instance (this).

        :return string: status of the instance
        """

        if self.__instance is not None:

            try:
                self.__instance = self.nova_client.servers.get(self.__instance.id)
                return self.__instance.status

            except Exception as error:
                # TODO: Change when logging is added
                if APP.config['DEBUG']:
                    print(error)
                return None

        else:
            return None

    def get_vnc(self, vnc_type):
        """Get a link for a vnc session.

        :param vnc_type: type of vnc (currently only supports 'novnc')
        :return: a vnc link for the specified type or none if unsuccessful
        """

        vnc = None

        try:
            if vnc_type == 'novnc':
                vnc = self.__instance.get_vnc_console('novnc')['remote_console']['url']
            else:
                pass

        except Exception as error:
            # TODO: Change when logging is added
            if APP.config['DEBUG']:
                print(error)

        return vnc

    # Floating IP is not used!
    def attach_floating_ip(self, instance_id, floating_ip):
        """Attaches a floating ip to current instance.

        :param instance_id: Id of instance to get floating ip
        :type instance_id: str
        :param floating_ip: Id of which floating ip to attach
        :type floating_ip: str
        :return: None
        """

        try:
            self.nova_client.servers.add_floating_ip(server=instance_id, address=floating_ip)

        except Exception as error:
            # TODO: Change when logging is added
            if APP.config['DEBUG']:
                print('Failed with associating: ' + str(error))

    def get_floating_ip(self):
        """Returns floating ips associated with current instance.

        :return: list of floating ip objects
        :rtype: `list`
        """

        to_return = list()

        try:
            for item in self.__instance.addresses:
                for network in self.__instance.addresses[item]:
                    if network['OS-EXT-IPS:type'] == 'floating':
                        to_return.append(network)

        except Exception as error:
            # TODO: Change when logging is added
            if APP.config['DEBUG']:
                print('Error in listing floating IP: ' + str(type(error)))

        return to_return

    def detach_floating_ip(self):
        """
        Detaches all attached floating ips from current instance.

        :return: Nothing
        """
        try:
            to_delete = self.get_floating_ip()
            for item in to_delete:
                print(item['addr'])
                print(type(item['addr']))
                # This does not remove the floating ip, it only disassociates the floating IP
                self.nova_client.servers.remove_floating_ip(self.__instance.id, item['addr'])

        except Exception as error:
            # TODO: Show error message?
            print('Error in remove floating IP: ' + str(type(error)))
