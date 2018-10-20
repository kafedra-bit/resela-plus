"""
edit.py
*******
"""

import json
import logging
from functools import partial
from time import sleep

import flask
from flask_login import login_required, current_user, login_user
from keystoneauth1 import exceptions as ksa_exceptions

from resela.backend.managers.CourseManager import CourseManager
from resela.backend.managers.ErrorManager import error_handling
from resela.backend.managers.GroupManager import GroupManager
from resela.backend.managers.LabManager import LabManager
from resela.backend.managers.MikrotikManager import MikrotikManager
from resela.backend.managers.RoleManager import requires_roles
from resela.backend.managers.UserManager import UserManager
from resela.model.User import User, authenticate as user_authenticate

edit = flask.Blueprint('edit', __name__, url_prefix='/edit')
LOG = logging.getLogger(__name__)
error_handling = partial(error_handling, log=LOG)


@edit.route('/course/<string:course_id>')
@login_required
@requires_roles('admin', 'teacher')
@error_handling
def course(course_id):
    """Render an editing page for specified course.

    Information about the course is retrieved and passed to the template
    rendering function.

    Flask input:
        * **id**: Course id of the course to be edited.
    """

    group_manager = GroupManager(current_user.session)
    course_manager = CourseManager(current_user.session)
    user_manager = UserManager(current_user.session)
    lab_manager = LabManager(current_user.session)

    course = course_manager.get(course_id)

    course_teachers = group_manager.find(name=course.name + '|teachers')
    course_students = group_manager.find(name=course.name + '|students')

    teachers = user_manager.list(group=course_teachers.id)
    students = user_manager.list(group=course_students.id)
    labs = lab_manager.list(domain=course_id)

    return flask.render_template('edit/course.html',
                                 course=course,
                                 teachers=teachers,
                                 labs=labs,
                                 students=students)


@edit.route('/user/<string:user_id>')
@login_required
@requires_roles('admin', 'teacher')
@error_handling
def user(user_id):
    """Render an editing page for a specified user.

    Information about the specified user is retrieved and passed to a template
    rendering function.

    Flask input:
        * **id**: User id of the user whose information is to be edited.
    """

    user_manager = UserManager(current_user.session)
    course_manager = CourseManager(current_user.session)
    group_manager = GroupManager(current_user.session)

    enrolled_courses = [course for course in course_manager.list_courses()
                        if course_manager.check_in_course(user_id, course.id)]

    courses = [course for course in course_manager.list_courses()
               if course not in enrolled_courses]

    if current_user.role == 'teacher':
        courses = [course for course in courses
                   if course_manager.check_in_course(current_user.user_id, course.id)]

    edit_user = user_manager.get(user_id)
    if 'students' in [group.name for group in group_manager.list(user=edit_user.id)]:
        user_role = 'student'
    elif 'teachers' in [group.name for group in group_manager.list(user=edit_user.id)]:
        user_role = 'teacher'
    else:
        user_role = 'admin'

    return flask.render_template('edit/user.html',
                                 enrolled_courses=enrolled_courses,
                                 courses=courses,
                                 edit_user=edit_user,
                                 user_role=user_role)


# TODO(jiah): Combine this with simply edit user
@edit.route('/user/save', methods=['POST'])
@login_required
@requires_roles('admin', 'teacher', 'student')
@error_handling
def user_save():
    """Apply input settings to a user's account.

    flask.request input:
        * **firstname**: The new first name.
        * **surname**: The new surname.
        * **user_id**: User id of the user to edit.
        * **old_password**: The current password.
        * **repeat_password**: The new password.
        * **new_password**: The new password, repeated.
    Resulting states:
        * **Success**: The password is changed for the user with `user_id`. \
            Forward to the index page.
        * **Special** (*Admin*): Change only the user's name. Forward to \
            the "edit user" page.
    """

    class MissingArguments(Exception):
        pass

    class PasswordsDoNotMatch(Exception):
        pass

    try:
        first_name = flask.request.form.get('firstname', None, type=str)
        surname = flask.request.form.get('surname', None, type=str)
        user_id = flask.request.form.get('user_id', None, type=str)

        old_pwd = flask.request.form.get('old_password', None, type=str)
        new_pwd = flask.request.form.get('new_password', None, type=str)
        repeat_pwd = flask.request.form.get('repeat_password', None, type=str)

        user_m = UserManager(session=current_user.session)

        if current_user.role == 'admin':
            if user_id and first_name and surname:
                user = user_m.get(user=user_id)
                user_m.update(user, first_name=first_name, last_name=surname)
                flask.flash('Successfully updated username.', 'success')
                return flask.jsonify(success=True)

        if not (old_pwd and new_pwd and repeat_pwd):
            raise MissingArguments('Missing mandatory arguments.')

        old_credentials = {
            'username': current_user.email,
            'password': old_pwd
        }

        # Test the "old" credentials. Will throw an exception upon fail.
        user_authenticate(old_credentials)

        if new_pwd != repeat_pwd:
            raise PasswordsDoNotMatch('The new and repeated passwords are not equal.')

        mikrotik_m = MikrotikManager()
        # TODO(Kaese) check wether this succeeds or not.
        mikrotik_m.update_password(new_pwd, current_user.email)
        user_m.update(user=current_user.user_id, password=new_pwd)

        # must wait for openstack...
        sleep(1)

        credentials = {
            'username': current_user.email,
            'password': new_pwd
        }

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

        return flask.jsonify(success=True)

    except MissingArguments as error:
        LOG.debug(str(error))
        return flask.jsonify(success=False, feedback=str(error))
    except PasswordsDoNotMatch as error:
        LOG.debug(str(error))
        return flask.jsonify(success=False, feedback=str(error))
    except ksa_exceptions.http.Unauthorized:
        msg = 'The current password is incorrect!'
        LOG.debug(msg)
        return flask.jsonify(success=False, feedback=msg)
