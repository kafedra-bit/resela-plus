"""
User.py
*******
"""

import json

from flask import session as flask_session
from flask_login import UserMixin, AnonymousUserMixin
from keystoneauth1 import session
from keystoneclient.auth.identity import v3

from resela.app import APP, LOGIN_MANAGER
from resela.backend.managers.UserManager import UserManager


class User(UserMixin):
    """Store user information.

    Used by Flask-Login to represent the current user (`flask.current_user`).
    """

    def __init__(self, user_id=None, email=None, token=None, name=None,
                 surname=None, role=None, session=None):
        # TODO(vph): `new_token` is a makeshift argument. It should supplant
        # TODO(vph): the `token` once we've migrated to Flask-Login.
        # TODO(vph): Its type is a `dict`, containing 'X-Auth-Token'.
        """
        :param user_id: A user's id. Corresponds to OpenStack user ids.
        :type user_id: `str`
        :param email: A user's e-mail address.
        :type email: `str`
        :param token: A database token, to retrieve a user's hashed password.
        :type token: `str`
        :param name: A user's name.
        :type name: `str`
        :param surname: A user's surname.
        :type surname: `str`
        :param role: A user's role.
        :type role: `str`
        """

        self.user_id = user_id
        self.email = email
        self.token = token
        self.name = name
        self.surname = surname
        self.role = role

        if token is not None:
            sess = authenticate(token)
            self.session = sess
        else:
            self.session = session

    @property
    def full_name(self):
        """Retrieve a user's full name."""
        return self.name + ' ' + self.surname

    def get_id(self):
        """Retrieve the user's id.

        This function is required by Flask-Login. The default implementation
        of `get_id` retrieves the attribute `id`, which this user
        implementation does not have.
        """

        return self.user_id


class AnonymousUser(AnonymousUserMixin, User):
    """An un-authenticated user, as prescribed by Flask-Login.

    The inheritance from both `AnonymousUserMixin` and `User` is necessary to
    possess all attributes that characterize a user, and still have all have
    the special attribute prescribed by Flask-Login set to the correct values.
    """

    def __init__(self):
        super().__init__()


def authenticate(credentials, user_domain_name='Default',
                 project_domain_name='Default', project_name='Default'):
    """Authenticate a user with either a password or a token.

    The occasion on which one authenticates with a username-password pair is
    the initial login. All future calls should authenticate with the token
    received from OpenStack.

    :param credentials: Login credentials.
    :type credentials: `dict`, either {'username': x, 'password': y } or {'X-Auth-Token': z}
    :param user_domain_name: User's domain name for authentication.
    :type user_domain_name: `str`
    :param project_domain_name: Project's domain name for project.
    :type project_domain_name: `str`
    :param project_name: Project name for project scoping.
    :type project_name: `str`
    :return: An authenticated OpenStack session.
    :rtype: `keystone1.session.Session`

    :raise: TypeError: No authentication credentials were provided.
    :raise: keystoneauth1.exceptions.http.Unauthorized: Authentication \
    failed.
    """

    if 'username' in credentials and 'password' in credentials:
        username = credentials['username']
        password = credentials['password']
        auth = v3.Password(
            auth_url=APP.iniconfig.get('openstack', 'keystone'),
            username=username,
            password=password,
            project_name=project_name,
            project_domain_name=project_domain_name,
            user_domain_name=user_domain_name
        )

    # The token returned by OpenStack through `get_auth_headers()` is set
    # in a `X-Auth-Token` field.
    elif 'X-Auth-Token' in credentials:
        token = credentials['X-Auth-Token']
        auth = v3.Token(
            auth_url=APP.iniconfig.get('openstack', 'keystone'),
            token=token,
            project_name=project_name,
            project_domain_name=project_domain_name
        )
    else:
        # TODO: Make a custom exception.
        raise TypeError('No credentials provided.', credentials)

    cert_path = APP.iniconfig.get('openstack', 'cert_path')
    sess = session.Session(auth=auth, verify=cert_path)

    # Check if authentication succeeds. Raises an error upon failure.
    sess.get_token()

    return sess


@LOGIN_MANAGER.user_loader
def load_user(user_id):
    """Load a user to be set as the `current_user`.

    According to the specification, `None` should be returned when
    a user with the provided user id cannot be retrieved. A return value of
    `None` will invalidate the Flask session, and Flask-Login will discard it,
    forcing the user to re-authenticate.

    :param user_id: User id of the user to be retrieved. Corresponds to the
        IDs used in OpenStack.
    :type user_id: `str`
    :return: An user object corresponding to the user id.
    :rtype: `model.User` or `None`
    """

    try:
        token = json.loads(flask_session['session'])
        os_session = authenticate(credentials=token)
        user_m = UserManager(session=os_session)
        user = user_m.get(user=user_id)

        session_user_kwargs = {
            'user_id': user.id,
            'email': user.name,
            'name': user.first_name,
            'surname': user.last_name,
            'role': os_session.auth.auth_ref['roles'][0]['name'],
            'token': json.loads(flask_session['session'])
        }

        return User(**session_user_kwargs)
    except:
        # TODO(vph): Add debug log message.
        return None

# TODO(vph): Moved from `app.py` so that it does not cause import cycles;
# TODO(vph): Should be moved somewhere else...
LOGIN_MANAGER.anonymous_user = AnonymousUser
