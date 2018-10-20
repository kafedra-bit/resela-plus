"""
UserManager.py
**************
"""

import flask
from flask_mail import Mail, Message
from keystoneclient.v3.client import Client as KeystoneClient
from keystoneclient.v3.users import UserManager as OSUserManager

from resela.app import APP
from resela.backend.classes.NetworkHandler import NetworkHandler
from resela.backend.classes.SecurityGroupHandler import SecurityGroupHandler
from resela.backend.managers.CourseManager import CourseManager
from resela.backend.managers.GroupManager import GroupManager
from resela.backend.managers.InstanceManager import InstanceManager
from resela.backend.managers.LabManager import LabManager
from resela.backend.managers.ManagerException import UserManagerCreationFail, \
    CourseManagerCreationFail, GroupManagerCreationFail, InstanceManagerCreationFail, \
    MikrotikManagerCreationFail
from resela.backend.managers.MikrotikManager import MikrotikManager
from resela.backend.classes.SecurityGroupHandler import SecurityGroupHandler
from keystoneauth1 import exceptions as ksa_exceptions
from flask_login import current_user


from resela.app import DATABASE
from resela.backend.SqlOrm.User import User as UserModel


class UserManager(OSUserManager):
    """Represents a openstack user manager"""
    def __init__(self, session=None, client=None):
        if session:
            client = KeystoneClient(session=session)
        if client:
            super().__init__(client)
        else:
            raise UserManagerCreationFail("Neither session nor client provided")

        self._client = client

    def add_user(self, user_email, first_name, last_name, password, role):
        """
        Creates a password for the user and adds the user to openstack.

        :param auth_m: authentication manager of the user who is adding a new user.
        :param user_email: email address of the new user
        :param first_name: first name of the new user
        :param last_name: last name of the new user
        :param role: role for the new user
        :param password: the users password in plain text
        :return: user: newly created user object

        Resulting states:
            * **Success**: A user object is returned
            * **Fail** (Unauthorized creation of managers): Raises exception if course or \
            group manager creation fails.
            * **Fail** (Unable to create user or add user to group): Raises exception if the user \
            cannot be created or if the user cannot be added to a group (student/teacher).
        """

        course_m = CourseManager(current_user.session)
        group_m = GroupManager(current_user.session)

        user = self.create(
            name=user_email,
            domain=course_m.find(name='default').id,
            password=password,
            email=user_email,
            first_name=first_name,
            last_name=last_name,
            vlan='',
            network_id=''
        )

        # Add mikrotik VPN user
        mikrotik_m = MikrotikManager()
        mikrotik_m.create_vpn_user(user_email, password)

        # Add to database
        user_model = UserModel(user.id)
        DATABASE.session.add(user_model)
        DATABASE.session.commit()

        if user is None:
            raise Exception('Could not create user')

        if role == 'student':
            self.add_to_group(user, group_m.find(name='students'))
        elif role == 'teacher':
            self.add_to_group(user, group_m.find(name='teachers'))

        return user

    def delete_user(self, user, instance_m):
        """
        Deletes a user and the network that belongs to that user. The mikrotik configurations are
        also removed.
        :param user: user to be removed
        :type user: OpenStack user object
        :param instance_m: InstanceManager that can handle instances
        :type instance_m: InstanceManager
        :return:
        """
        from resela.model.User import authenticate
        if user:
            mikrotik_m = MikrotikManager()
            lab_m = LabManager(current_user.session)
            group_m = GroupManager(current_user.session)
            user_m = UserManager(current_user.session)

            # Remove router conf
            mikrotik_m.unbind_vpn_to_vlan(user.email)
            mikrotik_m.delete_vpn_user(user.email)

            instance_list = instance_m.list(
                detailed=True,
                search_opts={'all_tenants': True, 'user_id': user.id}
            )

            for instance in instance_list:
                instance_name = instance.name.split('|')
                lab_name = instance_name[0] + '|' + instance_name[1]
                lab = lab_m.find(name=lab_name)
                instance_m.delete_instance(
                    user_m=self,
                    session=current_user.session,
                    lab=lab,
                    instance_id=instance.id
                )

            teacher_group = group_m.find(name='teachers')

            try:
                user_m.check_in_group(user=user, group=teacher_group)
                snapshot_factory = lab_m.find(
                    name='snapshotFactory|{}'.format(user.email))

                session = authenticate(
                    credentials=current_user.token,
                    project_domain_name='snapshotFactory',
                    project_name=snapshot_factory.name
                )

                security_handler = SecurityGroupHandler(session=session)

                for sec_group in security_handler.list()['security_groups']:
                    if sec_group['tenant_id'] == snapshot_factory.id and \
                                    'internet' in sec_group['name']:
                        security_handler.delete(sec_group['id'])

                lab_m.delete(snapshot_factory)

            except ksa_exceptions.NotFound:
                # Removing students will cause en exception as they are not found.
                # Does not need to be handled.
                pass

            # Remove user from db
            try:
                user_model = UserModel.query.get(user.id)
                DATABASE.session.delete(user_model)
                DATABASE.session.commit()
            except Exception:
                # Ignore user not in database
                pass

            # Remove user from openstack
            removed = self.delete(user)

            if not removed:
                print('User was not deleted:', user.id)
                raise Exception(' user not deleted')

    # TODO(jiah): Rewrite this function to take flag parameter which explicitly states what \
    # email to send
    @staticmethod
    def email_user(to_email, password=None, token=None):
        """Sends an email to the user who requested a new password or a confirmation email to a
        user who has reset his or her password.
        If email and password is set, a mail is sent to a newly registrated user.
        If email and token is set, a request to reset password is sent to the user with a link and
        a temporary token.
        If only the email is set, an confirmation email is sent to the user that the password has
        been successfully reset.
        :param to_email: Email of user that has forgotten password.
        :param password: A auto generated password for the user when he or she is first added to \
        ReSeLa+
        :param token: The token that will be used to create the link.
        Resulting states:
            Success (Correctly set params): An email is sent to the user with information about \
            the ReSeLa account.
            Fail (Unset params): If params are not set correctly. No email is sent.
        """
        try:
            if password and token:
                raise Exception('No email has been sent. Both token and password is set.')
            mail = Mail(APP)
            if to_email and password:
                message = Message(
                    'Resela+ - Welcome!',
                    sender=APP.iniconfig.get('flask', 'mail_username'),
                    recipients=[to_email]
                )
                message.body = 'Greetings,\nYour password: ' + password + \
                               '\n\nWhen you first log in to the system remember to change the ' \
                               'password in settings.\n\n' + \
                               flask.url_for('default.index', _external=True) + \
                               '\n\nKind regards,\nThe ReSeLa+ Group'
            elif to_email and token:
                message = Message(
                    'Resela+ - Reset password request, link valid for 10 minutes',
                    sender=APP.iniconfig.get('flask', 'mail_username'),
                    recipients=[to_email]
                )
                message.body = 'Greetings, \nYou have requested to reset you password on ' \
                               'ReSeLa+. Follow the link to complete the password reset ' \
                               'process. \n\n' + \
                               flask.url_for('account.reset_password', _external=True,
                                             token=token) + \
                               '\n\nKind regards,\nThe ReSeLa+ group'
            elif to_email:
                message = Message(
                    'Resela+ - Confirmation password reset',
                    sender=APP.iniconfig.get('flask', 'mail_username'),
                    recipients=[to_email]
                )
                message.body = 'Greetings,\nYour password has now been reset. Log in to ' \
                               'ReSeLa+:\n\n' + flask.url_for('default.index', _external=True) + \
                               '\n\nIf you did not make this request, please contact your ' \
                               'ReSeLa+ administrator.\n\nKind regards,\nThe ReSeLa+ Group'
            else:
                raise Exception('No email has been sent. Invalid parameters.')
            mail.send(message)
        except Exception as error:
            print(error)
