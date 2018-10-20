"""
CourseManager.py
****************
"""

from keystoneclient.v3.client import Client as KeystoneClient
from keystoneclient.v3.domains import DomainManager

from flask_login import current_user

from resela.backend.managers.InstanceManager import InstanceManager
from resela.backend.managers.ManagerException import CourseManagerCreationFail
from resela.backend.managers.RoleManager import ROLES

IGNORE_COURSES = ('Default', 'default', 'heat', 'imageLibrary', 'snapshotFactory')


class CourseManager(DomainManager):
    """Represents a Openstack domain manager"""
    def __init__(self, session=None, client=None):
        if session:
            client = KeystoneClient(session=session)
        if client:
            super().__init__(client)
        else:
            raise CourseManagerCreationFail("Neither session nor client provided")

        self._client = client

    def list_courses(self, **kwargs):
        """ List OpenStack domains that are actual courses.
        
        :return: A list of OpenStack domain objects that are courses.
        :rtype: `list` of `keystoneclient.v3.domains.Domain`
        """
        return [course for course in self.list(**kwargs) if course.name
                not in IGNORE_COURSES]

    def list_my_courses(self):
        """ List courses that belong to current user

        :return: A list of users courses.
        :rtype: `list` of courses
        """
        my_courses = self.get_course_names(current_user.user_id)
        return [self.find(name=name) for name in my_courses]

    def create_course(self, course_name, course_description):
        """
        Creates a course. Only admins have the required permissions to do this!
        Creates the groups student and teacher for the created course.

        :param course_name: The course code
        :param course_description: The name of the course
        :return: Course id for the created course / None
        """

        group_m = self._client.groups
        role_m = self._client.roles

        course = self.create(
            name=course_name.replace('|', ''),
            description=course_description
        )

        for role in ROLES:
            if role == 'admin':
                group = group_m.find(name='admin')
            else:
                group_name = '{}|{}s'.format(course.name, role)
                group = group_m.create(
                    name=group_name,
                    description='{}s for course {}'.format(role, course_name),
                    domain=course.id
                )

            os_role = role_m.find(name=role)
            role_m.grant(role=os_role, group=group.id, domain=course.id)

        return course.id

    def get_course_names(self, user_id):
        """
        Return a list of all course names, extracted from a user's group
        names.

        :param user_id: A user to filter by
        :type user_id: str

        :return List of course name which the user is part of
        :rtype List
        """
        return [group.name.split('|')[0] for group in
                self._client.groups.list(user=user_id) if '|' in group.name]

    def check_in_course(self, user_id, course_id):
        """Check if a specified user in a specific course.

        :param user_id: A user ID to filter by
        :type user_id: str
        :param course_id: A course ID to filter by
        :type course_id: str

        :return True or false depending on whether the user is in the course
        :rtype boolean
        """
        #TODO: This function does not work (_client fails)
        user_groups = [group for group in self._client.groups.list(user=user_id) if
                       group.name not in ('students', 'teachers')]

        return any(group.domain_id == course_id for group in user_groups)

    def add_user(self, course_id, email, role):
        """This will add a list of users to a course. The users needs to be in the system before added
        to a course. also checks if the user has the correct role in the default-domain!

        :param auth_handler: An AuthenticationHandler of the current user logged in.
        :param course_id: Course to add user to
        :param user_email: User email
        :param role: Role for the user
        :return: List with users that was not added
        """

        # TODO(vph): Add "raises" in docstring.

        user_m = self._client.users
        course_m = self._client.domains
        group_m = self._client.groups

        course = course_m.get(domain=course_id)
        # If the `role` argument is not an actual role, this will fail.
        # TODO(vph): Can this be misused? Verify beforehand?
        group = group_m.find(name='%s|%ss' % (course.name, role))

        # If the `email` argument does not correspond to a user, this will
        # fail.
        user = user_m.find(name=email)
        user_m.add_to_group(user=user, group=group.id)

    def remove_user(self, user_id, course_id, role):
        """Will remove a user from a course. Will remove the users instances on the course!

        :param session: An AuthenticationHandler of the current user logged in.
        :param user_id: User id for the user
        :param course_id: Course to remove the user from
        :param role: The role for the user to be added
        :return: True / None
        """

        from resela.model.User import authenticate

        user_m = self._client.users
        course_m = self._client.domains
        group_m = self._client.groups
        lab_m = self._client.projects

        course = course_m.get(domain=course_id)

        # Deletes all the users instances in the course
        if role == 'admin':
            instance_m = InstanceManager(current_user.session)
            for lab in lab_m.list(domain=course_id):
                for instance in instance_m.list(search_opts={'all_tenants': True, 'user_id': user_id}):
                    instance_m.delete_instance(
                        user_m=user_m,
                        session=self._client.session,
                        lab=lab,
                        instance_id=instance.id
                    )

        else:
            for lab in lab_m.list(domain=course_id):
                session = authenticate(
                    credentials=current_user.token,
                    project_domain_name=lab.name.split('|')[0],
                    project_name=lab.name)
                instance_m = InstanceManager(session)

                for instance in instance_m.list():
                    if instance.user_id == user_id:
                        instance_m.delete_instance(
                            user_m=user_m,
                            session=session,
                            lab=lab,
                            instance_id=instance.id
                        )

        for group in group_m.list(user=user_id):
            if group.name == '{}|students'.format(course.name):
                # TODO(vph): Handle get() exception.
                user_m.remove_from_group(user=user_m.get(user_id),
                                         group=group.id)

            elif group.name == '{}|teachers'.format(course.name):
                # TODO(vph): Handle get() exception.
                user_m.remove_from_group(user=user_m.get(user_id),
                                         group=group.id)

        return True

