"""
account.py
**********

This blueprint defines routes for login, logout, the settings page, and
password recovery.
"""

import json
import flask
import logging

from functools import partial
from flask_login import current_user, login_user, logout_user, login_required
from itsdangerous import URLSafeTimedSerializer, BadSignature
from keystoneauth1 import exceptions as ksa_exceptions
from resela.model.User import User, authenticate as user_authenticate
from resela.app import APP
from resela.model.RecaptchaModel import RecaptchaModel
from resela.model.UtilityModel import is_safe_url
from resela.backend.managers.UserManager import UserManager
from resela.backend.managers.MikrotikManager import MikrotikManager
from resela.backend.managers.RoleManager import requires_roles
from resela.backend.managers.ErrorManager import error_handling

account = flask.Blueprint('account', __name__, url_prefix='/account')
LOG = logging.getLogger(__name__)
error_handling = partial(error_handling, log=LOG)


@account.route('/login', methods=["POST", "GET"])
@error_handling
def login():
    """Present a login page and authenticate login credentials.

    One is forwarded here when accessing the index page or any page decorated
    with the `@require_login` as an un-authenticated user. Normally, one is
    forwarded to the index page on a successful login. Otherwise, if the
    `next` parameter is passed in the url, one is redirected to page if it is
    deemed safe.  Refer to the docstring of the `is_safe_url` function for
    those criteria.

    Request input:
        * **username** (*form*): Username. Part of the login credentials.
        * **password** (*form*): Password. Part of the login credentials.
    Resulting states:
        * **Success** (*GET request*): The login page is presented.
        * **Success** (*POST request*): A user is authenticated and \
            to either the index page or the page in the `next` parameter.
        * **Success** (*Already authenticated*): Redirect to the index page.
        * **Fail** (*Unsafe forward using next*): Present a error page.
        * **Fail** (*Incorrect credentials*): Stay on the login page. Let \
            the user attempt again.
        * **Fail** (*Username and password not provided*): Present the login \
            page again.
    """

    if current_user.is_authenticated:
        return flask.redirect(flask.url_for('default.index'))

    next = flask.request.args.get('next')

    if 'failed_login' not in flask.session:
        flask.session['failed_login'] = 0

    try:
        if flask.request.method == 'POST':

            credentials = {
                'username': flask.request.form['username'].lower(),
                'password': flask.request.form['password']
            }

            if flask.session['failed_login'] >= 3:
                ''' reCAPTCHA validation '''
                captcha_response = flask.request.form['g-recaptcha-response']
                post_response = RecaptchaModel.validate(captcha_response)
                ''' end of reCAPTCHA '''
                if not post_response['success']:
                    flask.flash('Failed to validate reCAPTCHA.', 'error')
                    return flask.render_template('account/login.html', show_captcha=True)

            session = user_authenticate(credentials)
            user_m = UserManager(session=session)
            user = user_m.get(user=session.auth.auth_ref['user']['id'])

            session_user_kwargs = {
                'user_id': session.auth.auth_ref['user']['id'],
                'email': session.auth.auth_ref['user']['name'],
                'name': user.first_name,
                'surname': user.last_name,
                'role': session.auth.auth_ref['roles'][0]['name'],
            }

            session_user = User(**session_user_kwargs)
            login_user(session_user)
            flask.session['session'] = json.dumps(session.get_auth_headers())

            # Abort if the `next` argument does not lead to a "safe" page.
            if not is_safe_url(next):
                return flask.abort(400)

            return flask.redirect(next or flask.url_for('default.index'))
        else:
            return flask.render_template('account/login.html',
                                         next=next,
                                         show_captcha=flask.session['failed_login'] >= 3)

    except KeyError as error:
        LOG.exception('Probable missing argument.')
        flask.abort(500)
    except ksa_exceptions.http.Unauthorized:
        flask.flash('Incorrect login credentials!', 'error')
        flask.session['failed_login'] += 1
        return flask.redirect(flask.url_for('default.index'))


@account.route('/logout')
@error_handling
def logout():
    """
    Remove a logged in user's authentication information from the Flask
    session file and forward to the index page.
    """

    flask.session.clear()
    logout_user()
    return flask.redirect(flask.url_for('default.index'))


@account.route('/settings')
@login_required
@requires_roles('admin', 'teacher', 'student')
@error_handling
def settings():
    """Forward users to the settings page for their account."""

    return flask.render_template('account/settings.html')


# TODO(vph): There are so many password-reset function -- don't know how
# TODO(vph): they should be decorated.
@account.route('/reset', methods=["POST"])
@error_handling
def new_password():
    """Send a password restoration mail to a specified e-mail address.

    The specified e-mail address is encoded into a token. The token is used
    to create a link to be sent to e-mail address. A mail is sent only if
    the specified e-mail belongs to a user. This function authenticates with
    OpenStack using a predefined password recovery account, which has access
    to user information.

    Request input:
        * **email** (*form*): E-mail address of the user whose account \
            password is to be recovered.
    Resulting states:
        * **Success**: An e-mail containing a restoration link is sent to the \
            specified e-mail address. One is forwarded to the index page.
        * **Fail** (*No e-mail address specified*): Redirect to the \
            "forgot password" page.
        * **Fail** (*The specified e-mail address does not belong to any user \
            in OpenStack*): No e-mail is sent. One is flask.redirected to the \
            index page.
    """

    email = flask.request.form.get('email', None).lower()
    serializer = URLSafeTimedSerializer(APP.iniconfig.get('flask', 'secret_key'))

    ''' reCAPTCHA validation '''
    captcha_response = flask.request.form['g-recaptcha-response']
    post_response = RecaptchaModel.validate(captcha_response)
    ''' end of reCAPTCHA '''

    if post_response['success']:
        credentials = {
            'username': APP.iniconfig.get('pru', 'user'),
            'password': APP.iniconfig.get('pru', 'pass')
        }

        pru_session = user_authenticate(credentials)
        token = serializer.dumps(email,
                                 salt=APP.iniconfig.get('flask', 'security_password_salt'))
        user_m = UserManager(session=pru_session)

        # Triggers an exception if no account exists.
        user_m.find(name=email)
        UserManager.email_user(to_email=email, token=token)
        flask.flash('An email with password reset '
                    'instructions has been sent to your email!', 'success')

        return flask.render_template('account/login.html')
    else:
        flask.flash('Failed to validate reCAPTCHA.', 'error')
        return flask.render_template('account/forgot_password.html')


@account.route('/reset/<string:token>', methods=['GET', 'POST'])
@error_handling
def reset_password(token):
    """Verify that a password restoration token corresponds to a correct
    e-mail, if so, forward to a password reset page.

    The function authenticates with OpenStack using a predefined password
    recovery account, which has access to user information.

    Params:
        * **token**: E-mail token.
    Resulting states:
        * **Success**: Forward to `edits/reset_password.html`.
        * **Fail** (*Bad Token*): Redirect to a 404 error page.
        * **Fail** (*Passwords does not match*): Redirected to reset/<token>.
        * **Fail** (*The specified e-mail address does not belong to any user \
            in OpenStack*): Redirect to a 404 error page.

    """

    try:
        serializer = URLSafeTimedSerializer(APP.iniconfig.get('flask', 'secret_key'))
        decoded_token = serializer.loads(
            token,
            salt=APP.iniconfig.get('flask', 'security_password_salt'),
            max_age=600)

        if flask.request.method == "POST":

            credentials = {'username': APP.iniconfig.get('pru', 'user'),
                           'password': APP.iniconfig.get('pru', 'pass')}

            pru_session = user_authenticate(credentials)
            user_m = UserManager(session=pru_session)

            email_reset = flask.request.form['email'].lower()
            new_passwd = flask.request.form['new_password']
            repeat_passwd = flask.request.form['repeat_password']

            if decoded_token != email_reset:
                flask.flash('Invalid permissions!', 'error')
                return flask.render_template('account/forgot_password.html')
            elif not (new_passwd == repeat_passwd):
                flask.flash('Passwords does not match!', 'error')
                return flask.render_template('account/reset_password.html', token=token)
            else:
                user = user_m.find(name=email_reset)
                if user:
                    user_m.update(user, password=new_passwd)
                    mikrotik_manager = MikrotikManager()
                    mikrotik_manager.update_password(new_passwd, user.email)
                    UserManager.email_user(to_email=user.email)

                    flask.flash('Password has been reset!', 'success')
                    return flask.render_template('account/login.html')
        else:
            return flask.render_template('account/reset_password.html', token=token)

    except BadSignature:
        LOG.debug('Password reset token mismatch.')
        flask.abort(403)


@account.route('/forgot_password')
@error_handling
def forgot_password():
    """Forward to the "forgot password" page."""
    return flask.render_template('account/forgot_password.html')
