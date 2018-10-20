"""
InstanceManager.py
******************
"""

import time

import flask
from flask_login import current_user
from keystoneauth1 import exceptions as ksa_exceptions
from novaclient.client import Client as NovaClient
from novaclient.v2.servers import ServerManager as OSServerManager

from resela.app import APP
from resela.app import DATABASE
from resela.backend.SqlOrm.User import User as UserModel
from resela.backend.SqlOrm.Vlan import Vlan as VlanModel
from resela.backend.classes.NetworkHandler import NetworkHandler
from resela.backend.managers.ManagerException import InstanceManager404
from resela.backend.managers.ManagerException import InstanceManagerAnotherActiveLab
from resela.backend.managers.ManagerException import InstanceManagerCreationFail
from resela.backend.managers.ManagerException import InstanceManagerParameter
from resela.backend.managers.ManagerException import InstanceManagerTooManyActiveInstancesInLab
from resela.backend.managers.ManagerException import InstanceManagerTooManyLabs
from resela.backend.managers.ManagerException import InstanceManagerUnknownFault
from resela.backend.managers.MikrotikManager import MikrotikManager


# Refer to
# https://developer.openstack.org/api-ref/compute/?expanded=list-servers-detail#listServers
# for a list of available options for the `search_opt` argument of `list()`.


class InstanceManager(OSServerManager):
    """Represents a OpenStack instance manager
    :raise InstanceManagerCreationFail: when the InstanceManager was unable to be created
    """

    def __init__(self, session=None, client=None):
        if session:
            client = NovaClient(version='2', session=session)
        if client:
            super().__init__(client)
        else:
            raise InstanceManagerCreationFail("Neither session nor client provided")
        self.session = session
        self._client = client

    @staticmethod
    def count_vms_in_lab(my_vms, lab_id, statuses=('ACTIVE', 'BUILDING', 'SUSPENDED', 'SHUTOFF', 'ERROR', 'REBOOTING')):
        return len([vm for vm in my_vms if vm.status in statuses and vm.tenant_id == lab_id])

    @staticmethod
    def count_other_labs(my_vms, lab_id):
        return len(set([vm.tenant_id for vm in my_vms if vm.tenant_id != lab_id]))

    def list_my_instances(self, show_all=True):
        """ Return list of vm's current user own
        This function is required as a normal user do not have filter permissions in openstack.
        Listing with search opts is limited to admin api, however in resela students and teachers
        have special privileges which allows all_tenants. This list is then filtered after
        current user
        :return: list of instances owned by current user
        """

        return [
            vm for vm in self._client.servers.list(search_opts={'all_tenants': show_all})
            if current_user.user_id in vm.user_id
        ]

    def list_my_instances_for_image(self, image_id, show_all=True):
        """ Return list of vm's current user own
        This function is required as a normal user do not have filter permissions in openstack.
        Listing with search opts is limited to admin api, however in resela students and teachers
        have special privileges which allows all_tenants. This list is then filtered after
        current user
        :return: list of instances owned by current user
        """

        return [
            vm for vm in self._client.servers.list(search_opts={'all_tenants': show_all})
            if current_user.user_id in vm.user_id and vm.image['id'] == image_id
        ]

    def list_instances_for(self, user, show_all=True):
        """ Return list of vm's user own
        :return: list of instances owned by current user
        """
        return [
            vm for vm in self._client.servers.list(search_opts={'all_tenants': show_all})
            if user.id in vm.user_id
        ]

    def create_instance(self, lab, instance_name, image, flavor, user_session, user_m):
        """Create an instance in the OpenStack

        :param lab: The lab that the instance should be started in
        :type lab: lab object
        :param instance_name: The name of the instance that should be started
        :type instance_name: str
        :param image: The image which should be used to create the instance
        :type image: Image object or Image id
        :param flavor: The flavor chosen for this instance
        :type flavor: flavor object or flavor id
        :param user_session: Session of the project
        :type user_session: Keystone Session
        :param user_m: UserManager that manages the users
        :type user_m: UserManager
        :raise InstanceManagerAnotherActiveLab: When another lab is already active
        :raise InstanceManagerTooManyInstancesInLab: When too many instances are active already
        :raise InstanceManagerTooManyLabs: When too many labs are already active
        :raise InstanceManagerUnknownFault: When the InstanceManager reaches an unknown error
        :return: Returns the instance object created
        """
        my_vms = self.list_my_instances()
        user = user_m.get(current_user.user_id)

        make_new_network = False

        number_of_active_instances = self.count_vms_in_lab(my_vms=my_vms, lab_id=lab.id,
                                                           statuses=('ACTIVE', 'BUILDING'))
        number_of_total_instances = self.count_vms_in_lab(my_vms=my_vms, lab_id=lab.id)
        number_of_other_labs = self.count_other_labs(my_vms=my_vms, lab_id=lab.id)

        # Check if another lab is active
        if any(vm for vm in my_vms if vm.status == 'ACTIVE' and vm.tenant_id != lab.id):
            # TODO (Kaese): Fix conflicts with snapshotFactory project.
            raise InstanceManagerAnotherActiveLab('Another lab is active')

        # Check number of active VMs in this lab

        if number_of_active_instances >= APP.iniconfig.getint('resela', 'instance_limit'):
            raise InstanceManagerTooManyActiveInstancesInLab('Instances in lab limit reached')

        elif number_of_total_instances is 0:
            make_new_network = True

            # Check whether the maximum number of labs have been reached (active or inactive)
        if number_of_other_labs >= APP.iniconfig.getint('resela', 'instance_limit'):
            raise InstanceManagerTooManyLabs('Too many labs started')

        # TODO(Kaese): If booking is implemented, it should be here !

        instance = None

        if make_new_network:
            user_model = UserModel.query.get(user.id)
            network_handler = NetworkHandler(user_session)
            network = network_handler.create_network(network_name=user.name + '|' + lab.name)
            network = network['network']
            vlan = network['provider:segmentation_id']
            subnet_cidr = MikrotikManager.get_cidr_for_subnet(vlan)
            network_handler.create_subnet(network['id'], user.email +
                                          '|subnet_%s' % str(vlan), cidr=subnet_cidr)

            # Update mikrotik
            mikrotik_m = MikrotikManager()
            mikrotik_m.create_vlan(vlan)
            mikrotik_m.bind_vpn_to_vlan(vlan, user.email)

            # Update DB
            vlan_model = VlanModel(vlan, lab.id)
            DATABASE.session.add(vlan_model)
            DATABASE.session.commit()

            if user_model is None:
                user_model = UserModel(user.id, vlan_model.vlan_id)
                user_model.vlans.append(vlan_model)
                DATABASE.session.add(user_model)
            else:
                user_model.active_vlan = vlan_model.vlan_id
                user_model.vlans.append(vlan_model)

            DATABASE.session.commit()
            # Update keystone
            user_m.update(user=user, network_id=network['id'], vlan=vlan)

        user = user_m.get(user.id)
        network_id = user.network_id
        nics = [{'net-id': network_id}]
        has_internet = lab.internet
        instance = self.create(name=instance_name,
                               image=image,
                               flavor=flavor,
                               nics=nics,
                               meta={'image_name': image.name.split('|')[2]})

        self.wait_for_status(instance.id, 'ACTIVE')

        # Set security groups
        if has_internet:
            self.add_security_group(instance.id, 'internet')
        else:
            self.add_security_group(instance.id, 'no-internet')
        self.remove_security_group(instance.id, 'default')

        return instance

    def wait_for_status(self, instance_id, expected_status):
        """ Wait for a specific status for an instance

        :param instance_id: The id of the instance that is being observed
        :type instance_id: str
        :param expected_status: The status expected on a specific instance
        :type expected_status: str
        :raises InstanceManagerUnknownFault: When the instance fails return the expected result
        :return: returns status after timeout or success
        """
        timeout = 0
        status = 'ERROR'
        while timeout < 360:
            try:
                status = self.get(instance_id).status
            except Exception:  # Ugly fix since we dont know what 404 exception is thrown
                status = 'DELETED'
            if status == expected_status:
                break
            elif status == 'ERROR':
                raise InstanceManagerUnknownFault('Instance returned ERROR')
            time.sleep(1)
            timeout += 1

        return status

    def change_instance_state(self, user_m, lab_id, instance_id, expected_status):
        """ Change state of instance

        :param user_m: UserManager that handles users
        :type user_m: UserManager
        :param lab_id: Id of the lab where the instance is located
        :type lab_id: str
        :param instance_id: Instance that should have it's state changed
        :type instance_id: str
        :param expected_status: State which an instance is expected to change to
        :type expected_status: str
        :raise InstanceManagerParameter: When function failed to get username
        :raise InstanceManagerAnotherActiveLab: When too many labs are already active
        :raise InstanceManagerTooManyInstancesInLab: When too many instances are active already
        :raise InstanceManager404: If the instance was not found
        :return: The state which the instance is in as the function ends
        """
        result = 'ERROR'
        try:
            # TODO(Kaese): Enable people to pass in an instance object or instance_id
            instance = self.get(instance_id)

            if expected_status == 'SUSPENDED':
                if instance.status == 'ACTIVE':
                    self.suspend(instance_id)

            elif expected_status == 'SHUTOFF':
                if instance.status in ('SUSPENDED', 'ACTIVE'):
                    self.stop(instance_id)

            elif expected_status == 'ACTIVE':
                if current_user.user_id != instance.user_id:
                    raise InstanceManagerParameter('Not your instance')

                my_vms = self.list_my_instances()

                # Check if another lab is active
                if any(vm for vm in my_vms if
                       vm.status == 'ACTIVE' and vm.tenant_id != instance.tenant_id):
                    raise InstanceManagerAnotherActiveLab('Another lab is active')

                # Check amount of active VMs in this lab
                if len([vm for vm in my_vms if vm.status in (
                       'ACTIVE', 'BUILDING') and vm.tenant_id == instance.tenant_id]) >= 3:
                    # TODO(Kaese): Add configurable maximum amount of instances per lab
                    raise InstanceManagerTooManyActiveInstancesInLab(
                        'Active VM limit for lab reached')

                if instance.status == 'SHUTOFF':
                    self.start(instance_id)
                elif instance.status == 'SUSPENDED':
                    self.resume(instance_id)
                elif instance.status == 'ACTIVE':
                    self.reboot(instance_id)

                instance = self.find(id=instance_id)
                instance_name = instance.name.split('|')

                if instance_name[0] == 'snapshotFactory':
                    email = instance_name[1]
                else:
                    email = instance_name[2]

                new_active_vlan = None
                user_model = UserModel.query.get(instance.user_id)

                for vlan in user_model.vlans:
                    if vlan.lab_id == lab_id:
                        new_active_vlan = vlan.vlan_id

                if user_model.active_vlan is None or user_model.active_vlan is not new_active_vlan:
                    user_model.active_vlan = new_active_vlan
                    DATABASE.session.commit()
                    mikrotik_m = MikrotikManager()
                    mikrotik_m.bind_vpn_to_vlan(new_active_vlan, email)

                    # Update OpenStack
                    user = user_m.get(user_model.user_id)
                    network_h = NetworkHandler(self.session)
                    subnets = network_h.list_subnets()
                    network_id = None

                    for subnet in subnets:
                        if subnet['name'] == email + '|subnet_' + str(new_active_vlan):
                            network_id = subnet['network_id']

                    if network_id is not None:
                        user_m.update(
                            user=user,
                            network_id=network_id,
                            vlan=new_active_vlan
                        )

            result = self.wait_for_status(instance_id, expected_status)

        except ksa_exceptions.NotFound:
            raise InstanceManager404('The instance was not found')

        # except InstanceManagerUnknownFault:
        #     result = "ERROR"
        # Catches all exceptions
        except Exception as error:
            print(error)
            result = "ERROR"

        return result

    def delete_instance(self, user_m, session, lab, instance_id):
        try:
            user = user_m.get(self.get(instance_id).user_id)

            # Delete the instance
            self.delete(instance_id)
            self.wait_for_status(instance_id, 'DELETED')

            total_vms = self.list_instances_for(user, show_all=False)

            if len(total_vms) == 0:
                vlan = None
                # Remove vlan from Database
                user_model = UserModel.query.get(user.id)
                for vlan_object in user_model.vlans:
                    if vlan_object.lab_id == lab.id:
                        vlan = vlan_object.vlan_id
                        vlan_model = vlan_object
                        user_model.vlans.remove(vlan_model)
                        DATABASE.session.delete(vlan_model)
                if user_model.active_vlan is vlan:
                    user_model.active_vlan = None
                DATABASE.session.commit()

                # Remove vlan from OpenStack
                network_h = NetworkHandler(session)
                networks = network_h.list_networks()
                network_name = '%s|%s' % (user.email, lab.name)

                if user.vlan == vlan:
                    user_m.update(user=user, network_id='', vlan='')
                for network in networks:
                    if network['name'] == network_name:
                        network_h.delete_network(network['id'])

                # Remove vlan from Mikrotik
                mikrotik_m = MikrotikManager()
                mikrotik_m.delete_vlan(vlan)
                mikrotik_m.unbind_vpn_to_vlan(user.email)

        except Exception as error:
            print(error)
