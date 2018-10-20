"""
LabManager.py
*************
"""

import logging
from time import sleep

import flask
from flask_login import current_user
from keystoneauth1 import exceptions as ksa_exceptions
from keystoneclient.v3.client import Client as KeystoneClient
from keystoneclient.v3.projects import ProjectManager
from flask import current_app

from resela.backend.classes.SecurityGroupHandler import SecurityGroupHandler
from resela.backend.managers.CourseManager import CourseManager
from resela.backend.managers.FlavorManager import FlavorManager
from resela.backend.managers.GroupManager import GroupManager
from resela.backend.managers.ImageManager import ImageManager
from resela.backend.managers.InstanceManager import InstanceManager
from resela.backend.managers.ManagerException import InstanceManagerInstanceActive
from resela.backend.managers.ManagerException import InstanceManagerUnknownFault
from resela.backend.managers.ManagerException import LabManagerCreationFail
from resela.backend.managers.RoleManager import RoleManager, ROLES

LOG = logging.getLogger(__name__)


class LabManager(ProjectManager):
    """Represents a OpenStack project manager
    :raise LabManagerCreationFail: When Manager is not able to be created
    """
    def __init__(self, session=None, client=None):
        if session:
            client = KeystoneClient(session=session)
        if client:
            super().__init__(client)
        else:
            raise LabManagerCreationFail("Neither session nor client provided")

        self._client = client

    def launch_lab(self, lab_id):
        """ Initializes the lab for a user

        :param auth_manager: Authentication manager object
        :type auth_manager: AuthenticationManager.AuthenticationManager
        :param lab_id: Id of the lab which should be launched
        :type lab_id: str
        :param user_id: Id of the user which tries to launch the lab
        :type user_id: str
        :raise LabManagerLaunchFail: When the lab fails to launch because of \
            too many instances in lab or an active lab
        :return:
        """

        from resela.model.User import authenticate

        image_manager = ImageManager(session=current_user.session)
        flavor_manager = FlavorManager(session=current_user.session)
        user_manager = self._client.users

        lab = self.get(lab_id)  # TODO(Kaese): Check returned value ?
        lab_images = lab.img_list
        instance_name_base = lab.name + '|' + current_user.email

        # Required since instances are launched in the project to which
        # the session belongs
        project_session = authenticate(
            credentials=current_user.token,
            project_domain_name=lab.name.split('|')[0],
            project_name=lab.name
        )

        local_instance_manager = InstanceManager(session=project_session)
        for image_descriptor in lab_images:
            try:
                image_id = image_descriptor[0]
                image_amount = image_descriptor[1]
                image_object = image_manager.get(image_id)
                flavor_object = flavor_manager.find(name=image_object.flavor_name)

                total_active_instances = \
                    len(local_instance_manager.list_my_instances_for_image(
                        show_all=False, image_id=image_id))

                # Create each remaining not started instances
                for i in range(int(image_amount) - total_active_instances):
                    local_instance_manager.create_instance(
                        lab=lab,
                        instance_name=instance_name_base,
                        image=image_object,
                        flavor=flavor_object,
                        user_session=current_user.session,
                        user_m=user_manager
                    )

            except InstanceManagerUnknownFault as error:
                # TODO(jiah): These really need to be handled
                # raise LabManagerLaunchFail(e)
                LOG.exception(error)
                pass
            except InstanceManagerInstanceActive:
                # Basically means the instance is already active
                pass

    def create_lab(self, course_id, lab_title, lab_internet, lab_description):
        """Create a lab to a course. Granting the course group permissions to the lab.
        :param auth_handler: An AuthenticationHandler of the current user logged in.
        :param course_id: Course id to add the lab to
        :type course_id: str
        :param lab_title: Title of the lab
        :type lab_title: str
        :param lab_internet: If the lab should have internet access or not
        :type lab_internet: bool
        :return: Lab id for the created lab / None
        """
        from resela.model.User import authenticate

        course_m = self._client.domains
        group_m = self._client.groups
        role_m = self._client.roles
        base_network = current_app.iniconfig.get('network', 'basenetwork') + '/16'

        course = course_m.get(domain=course_id)
        lab_title = lab_title.replace('|', '')
        lab = self.create(
            name='{}|{}'.format(course.name, lab_title),
            domain=course_id,
            img_list=[],
            internet=lab_internet,
            description=lab_description
        )

        for role in ROLES:
            if role == 'admin':
                group = group_m.find(name='admin')
            else:
                group = group_m.find(name='{}|{}s'.format(course.name, role))
            os_role = role_m.find(name=role)
            role_m.grant(role=os_role, group=group, project=lab)

        session = authenticate(
            credentials=current_user.token,
            project_domain_name=course.name,
            project_name=lab.name)
        security_handler = SecurityGroupHandler(session=session)

        # Create internet group
        internet_group = security_handler.create(
            name="internet",
            description='Allow internet access',
            tenant_id=lab.id
        )

        # Clear default rules
        security_handler.delete_all_rules(
            internet_group['security_group']['id'])

        # Create new internet (No internet)
        security_handler.create_rule(
            security_group_id=internet_group['security_group']['id'],
            description=lab.name,
            direction='ingress',
            ethertype='IPv4'
        )

        security_handler.create_rule(
            security_group_id=internet_group['security_group']['id'],
            description=lab.name,
            direction='egress',
            ethertype='IPv4'
        )

        # Create no-internet group
        no_internet_group = security_handler.create(
            name="no-internet",
            description='Do not allow internet access',
            tenant_id=lab.id
        )

        # Clear default rules
        security_handler.delete_all_rules(
            no_internet_group['security_group']['id'])

        # Create new internet (No internet)
        security_handler.create_rule(
            security_group_id=no_internet_group['security_group']['id'],
            direction='ingress',
            ethertype='IPv4'
        )

        security_handler.create_rule(
            security_group_id=no_internet_group['security_group']['id'],
            direction='egress',
            ethertype='IPv4',
            remote_ip_prefix=base_network,
            description='Only local egress traffic.'
        )
        return lab.id

    def delete_lab(self, lab_id, user_m):
        """
        Removes the lab and all instances associated with the lab!

        :param user_m: UserManager
        :param lab_id: Lab to delete
        :return: True / False
        """

        from resela.model.User import authenticate

        # TODO(vph): Will it retrieve a session?

        lab_m = LabManager(session=current_user.session)

        # TODO(vph): Will it retrieve a token?
        # TODO(vph): Couldn't this be an admin? Will this work as admin?
        lab = lab_m.get(project=lab_id)
        session = authenticate(
            credentials=current_user.token,
            project_domain_name=lab.name.split("|", 1)[0],
            project_name=lab.name
        )
        lab_name = lab.name.split('|')
        instance_m = InstanceManager(session=session)
        for instance in instance_m.list():
            temp_name = instance.name.split('|')
            if temp_name[0] == lab_name[0] and temp_name[1] == lab_name[1]:
                instance_m.delete_instance(
                    user_m=user_m,
                    session=session,
                    lab=lab,
                    instance_id=instance.id
                )

        sec_handler = SecurityGroupHandler(session)
        sec_group = sec_handler.list()
        if sec_group is not None:
            for i in sec_group['security_groups']:
                if i['tenant_id'] == lab_id and 'internet' in i['name']:
                    sec_handler.delete(i['id'])

        sleep(4)
        self._client.projects.delete(project=lab_id)
        return True

    def create_snapshot_factory_project(self, user):
        """
        Creates the snapshot factory project for the assigned user

        :param auth_m: An authentication manager object
        :param user: The object of the user that the project shall be created for
        :return:
        """

        from resela.model.User import authenticate

        course_m = CourseManager(current_user.session)
        role_m = RoleManager(current_user.session)
        group_m = GroupManager(current_user.session)

        snapshot_factory_domain = course_m.find(name='snapshotFactory')
        teacher_role = role_m.find(name='teacher')
        admin_group = group_m.find(name='admin')
        admin_role = role_m.find(name='admin')

        snapshot_factory_project = self.create(
            name='snapshotFactory|{}'.format(user.email),
            domain=snapshot_factory_domain,
            description='',
            base_img='',
            img_name='',
            flavor='',
            internet='',
            keywords='',
            os='',
            version=''
        )

        role_m.grant(
            role=teacher_role,
            user=user,
            project=snapshot_factory_project
        )

        role_m.grant(
            role=admin_role,
            group=admin_group,
            project=snapshot_factory_project
        )

        session = authenticate(
            credentials=current_user.token,
            project_domain_name='snapshotFactory',
            project_name=snapshot_factory_project.name
        )

        SecurityGroupHandler.create_security_groups(
            lab=snapshot_factory_project,
            lab_session=session
        )