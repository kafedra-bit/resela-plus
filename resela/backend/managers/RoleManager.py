"""
RoleManager.py
**************
"""

from functools import wraps

from keystoneclient.v3.client import Client as KeystoneClient
from keystoneclient.v3.roles import RoleManager as OSRoleManager
from flask import jsonify, abort
from flask_login import current_user

from resela.backend.managers.ManagerException import RoleManagerCreationFail

""" Defined roles in resela """
ROLES = ['admin', 'teacher', 'student']


class RoleManager(OSRoleManager):
    """Represents a openstack role manager"""
    def __init__(self, session=None, client=None):
        if session:
            client = KeystoneClient(session=session)
        if client:
            super().__init__(client)
        else:
            raise RoleManagerCreationFail("Neither session nor client provided")

        self._client = client

    def retrieve_most_privileged_role(self, **kwargs):
        """
        Retrieve the most privileged role of a user based on the groups he or
        she belongs to.

        The order of precedence:
            1. Admin
            2. Teacher
            3. Student
        """

        groups = self._client.groups.list(**kwargs)

        role = None
        for group in groups:
            if group.name == 'admin':
                # If a user belongs to the `admin` group, he/she cannot be
                # escalated further.
                return 'admin'
            elif group.name == 'teacher':
                role = 'teacher'
            elif group.name == 'student' and role != 'teacher':
                role = 'student'
        return role


def requires_roles(*roles, api_call=False):
    """Set the roles that are authorized to access a view.

    Decorates the view functions.

    :param roles: Roles that are authorized to access a view.
    :type roles: `list` of `str`
    :param api_call: Flag indicating whether the decorated function is an \
        API function
    :type api_call: `bool`
    """

    def wrapper(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            """Check if the current user's role is authorized.

            Resulting states:
                * **Success**: The decorated view function is called with \
                    the provided args and kwargs.
                * **Fail (Not authorized)**: A 403 error page is presented.
            """
            if current_user.role not in roles:
                if api_call:
                    return jsonify({
                        'success': False,
                        'feedback': 'Role not authorized.'
                    })
                else:
                    return abort(401)
            return f(*args, **kwargs)
        return wrapped
    return wrapper
