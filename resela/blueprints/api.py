"""
api.py
******

This blueprint defines api functions

note: api calls only responds with jsonify, never render_template
"""

import datetime
import logging
import tempfile
import time
from functools import partial
from random import choice
from string import ascii_lowercase, ascii_uppercase, digits

import flask
from flask_login import current_user
from keystoneauth1 import exceptions as ksa_exceptions
from glanceclient.exc import HTTPException
from werkzeug.utils import secure_filename

from resela.app import DATABASE, APP, after_this_request
from resela.backend.SqlOrm.OsModel import OS
from resela.backend.SqlOrm.VersionModel import Version
from resela.backend.classes.FileHandler import FileHandler
from resela.backend.managers.CourseManager import CourseManager
from resela.backend.managers.FlavorManager import FlavorManager
from resela.backend.managers.GroupManager import GroupManager
from resela.backend.managers.ImageManager import ImageManager
from resela.backend.managers.InstanceManager import InstanceManager
from resela.backend.managers.LabManager import LabManager
from resela.backend.managers.RoleManager import requires_roles
from resela.backend.managers.ManagerException import InstanceManagerTooManyLabs, \
    InstanceManagerAnotherActiveLab, InstanceManagerParameter, \
    InstanceManagerTooManyActiveInstancesInLab, InstanceManager404, \
    InstanceManagerUnknownFault
from resela.backend.managers.ErrorManager import error_handling, \
    MD5Match, ExceedsUploadLimit, DefaultNotAuthorized, ImageIsUsed, \
    UnpermittedLabName, NoBaseImage, NoInstanceFound, InstanceExists, NoVNCLink
from resela.backend.managers.UserManager import UserManager
from resela.model.User import authenticate

api = flask.Blueprint('api', __name__, url_prefix='/api')
LOG = logging.getLogger(__name__)
error_handling = partial(error_handling, log=LOG, api_call=True)

# Overwrite the `api_call` argument for all `require_role` decorators in this
# file, as all of them decorate api functions.
requires_roles = partial(requires_roles, api_call=True)


class TeacherNotInCourse(Exception):
    pass


@api.route('/user/delete', methods=['POST'])
@requires_roles('admin')
@error_handling
def user_delete():
    """Delete a specified user.

    flask.request input:
        * **user_id** (*form*): User id of the user to be deleted.
    """

    # TODO remove VPN for the user

    user_id = flask.request.values['user_id']

    user_m = UserManager(current_user.session)
    instance_m = InstanceManager(current_user.session)

    user = user_m.get(user_id)
    user_m.delete_user(user, instance_m)

    return flask.jsonify(success=True, feedback='User removed!')


@api.route('/course/create', methods=['POST'])
@requires_roles('admin')
@error_handling
def course_create():
    """Create a course and forward to a page for the new course.

    flask.request input:
        * **course_code**: The name (course code) of the course to \
            be created.
        * **course_title**: The readable title of the course, to be \
            added in the course's description.
    """

    course_title = flask.request.form['course_title']
    course_code = flask.request.form['course_code']

    course_m = CourseManager(session=current_user.session)

    course_id = course_m.create_course(
        course_name=course_code,
        course_description=course_title
    )

    flask.flash('Course successfully created!', 'success')
    return flask.jsonify(
        success=True,
        feedback='',
        redirect=flask.url_for('edit.course', course_id=course_id)
    )


@api.route('/course/delete', methods=['POST'])
@requires_roles('admin')
@error_handling
def course_delete():
    """Delete a specified course.

    flask.request input:
        * **course_id**: Course id of the course to be deleted.
    """

    course_id = flask.request.values['course_id']

    course_m = CourseManager(session=current_user.session)
    lab_m = LabManager(session=current_user.session)

    for lab in lab_m.list(domain=course_id):
        session = authenticate(
            credentials=current_user.token,
            project_domain_name=lab.name.split('|')[0],
            project_name=lab.name
        )

        instance_m = InstanceManager(session=session)
        for instance in instance_m.list():
            user_m = UserManager(session=session)
            instance_m.delete_instance(user_m, session, lab, instance.id)

    course_m.update(domain=course_id, enabled=False)
    course_m.delete(domain=course_id)

    return flask.jsonify(
        success=True,
        feedback='Success.',
        redirect=''
    )


# TODO(jiah): Move this to edit blueprint
@api.route('/course/save', methods=['POST'])
@requires_roles('admin')
@error_handling
def course_save():
    """Save an edited course.

    flask.request input:
        * **title**: The new title for the course.
        * **description**: The new description for the course.
        * **course_id**: Course id of the course whose information is to be \
            saved.
    """

    # TODO: rewrite to use post instead!
    title = flask.request.values['title']
    description = flask.request.values['description']
    course_id = flask.request.values['course_id']

    # TODO(vph): change instance names!
    # TODO(vph): change name on labs!

    course_m = CourseManager(session=current_user.session)
    group_m = GroupManager(session=current_user.session)

    course = course_m.get(domain=course_id)

    # Name can not presently be changed since we need to alter some names.
    # TODO(vph): Is this why the `title` argument is unused?
    title = course.name.replace('|', '')
    course_m.update(domain=course, name=title, description=description)

    for role_str in ('students', 'teachers'):
        group = group_m.find(name='{}|{}'.format(course.name, role_str))
        group_m.update(
            group=group,
            name='{}|{}'.format(title, role_str),
            description='{} of course {}.'.format(role_str.title(),
                                                  course.name)
        )

    return flask.jsonify(
        success=True,
        feedback='Success.',
        redirect=''
    )


@api.route('/course/add_user', methods=['POST'])
@requires_roles('admin', 'teacher')
@error_handling
def course_add_user():
    """Add a specified user to a specified course.

    flask.request input:
        * **email_address**: The e-mail address identifying the user to be \
            added.
        * **course_id**: Course id of the course to which the user is to be \
            added.
        * **role**: Role of the user to be added.
    """

    try:
        # TODO(vph, jiah!): No longer a course id!
        course_id = flask.request.values['course_id']
        # TODO(jiah): Terribly insecure
        role = flask.request.values['role']
        get_address = flask.request.values['email_address']

        group_m = GroupManager(current_user.session)
        course_m = CourseManager(current_user.session)
        user_m = UserManager(current_user.session)

        if current_user.role == 'teacher':
            if not course_m.check_in_course(user_id=current_user.user_id,
                                            course_id=course_id):
                raise TeacherNotInCourse('Teacher not in course.')

        if get_address:
            get_address = get_address.replace('\n', '').replace('\r', '').replace(' ', '')
            email_address = [email.lower() for email in get_address.split(";")]

            possible_users = []
            for usr in user_m.list():
                if hasattr(usr, 'email') and usr.email in email_address:
                    possible_users.append(usr)

            student_group = group_m.find(name='students')
            teacher_group = group_m.find(name='teachers')

            for possible_user in possible_users:

                user_groups = group_m.list(possible_user)
                if role == 'student' and student_group in user_groups:
                    course_group = group_m.find(name=course_m.get(
                        course_id).name + '|students')
                    user_m.add_to_group(possible_user, course_group)
                elif role == 'teacher' and teacher_group in user_groups:
                    course_group = group_m.find(name=course_m.get(
                        course_id).name + '|teachers')
                    user_m.add_to_group(possible_user, course_group)
                else:
                    return flask.jsonify({
                        'success': False,
                        'feedback': 'Could not add user to course'})

        # TODO (Annika): No message is displayed to the user.
        return flask.jsonify(
            success=True,
            feedback='Success.'
        )

    except TeacherNotInCourse as error:
        LOG.error('%s UID: %s, CID: %s' % (str(error), current_user.user_id, course_id))
        return flask.jsonify(
            success=False,
            feedback=str(error)
        )
    except ksa_exceptions.NotFound as error:
        LOG.exception('Probable missing group.')
        return flask.jsonify(
            success=False,
            feedback='Unsuccessful.'
        )


@api.route('/course/remove_user', methods=['POST'])
@requires_roles('admin', 'teacher')
@error_handling
def course_remove_user():
    """Remove a specified user in a specified course.

    flask.request input:
        * **user_id**: User id of the user to be deleted.
        * **course_id**: Course id of the course in which user is to be located.
    """

    try:
        user_id = flask.request.values['user_id']
        course_id = flask.request.values['course_id']

        course_m = CourseManager(session=current_user.session)

        if current_user.role == 'teacher':
            if not course_m.check_in_course(user_id=current_user.user_id,
                                            course_id=course_id):
                raise TeacherNotInCourse('Teacher not in course.')

        if course_m.remove_user(user_id, course_id, current_user.role):
            return flask.jsonify(success=True)
        else:
            return flask.jsonify(success=False,
                                 feedback='Unable to remove the user.')

    except TeacherNotInCourse as error:
        LOG.error('%s UID: %s, CID: %s' % (str(error), current_user.user_id, course_id))
        return flask.jsonify(
            success=False,
            feedback=str(error)
        )


@api.route('/lab/create', methods=['POST'])
@requires_roles('admin', 'teacher')
@error_handling
def lab_create():
    """Create a lab.

    flask.request input:
        * **course_id**: Course id of the course to which a lab is to be added.
        * **lab_title**: The title of the lab to be created.
        * **lab_internet**: If the lab should have internet access.
    """

    try:
        course_id = flask.request.form['course_id']
        lab_title = flask.request.form['lab_title']
        lab_description = flask.request.form['description']
        lab_internet = True if flask.request.form.get('lab_internet') else False

        course_m = CourseManager(session=current_user.session)
        lab_m = LabManager(session=current_user.session)

        if current_user.role == 'teacher':
            if not course_m.check_in_course(user_id=current_user.user_id,
                                            course_id=course_id):
                raise TeacherNotInCourse('Teacher not in course.')

        lab_id = lab_m.create_lab(course_id, lab_title, lab_internet, lab_description)

        flask.flash('Successfully created lab!', 'success')
        return flask.jsonify({
            'success': True,
            'feedback': 'The lab was successfully created',
            'redirect': flask.url_for('default.lab', lab_id=lab_id)
        })

    except TeacherNotInCourse as error:
        LOG.error('%s UID: %s, CID: %s' % (str(error), current_user.user_id, course_id))
        return flask.jsonify(
            success=False,
            feedback=str(error)
        )


@api.route('/lab/delete', methods=['POST'])
@requires_roles('admin', 'teacher')
@error_handling
def lab_delete():
    """Delete a specified lab.

    flask.request input:
        * **lab_id**: Lab id of the lab to be deleted.
        * **course_id**: Course id of the course to which the lab is to be \
            found. Needed to verify a teacher's access.
    """

    try:
        lab_id = flask.request.values['lab_id']
        course_id = flask.request.values['course_id']

        course_m = CourseManager(session=current_user.session)
        lab_m = LabManager(session=current_user.session)

        if current_user.role == 'teacher':
            if not course_m.check_in_course(user_id=current_user.user_id,
                                            course_id=course_id):
                raise TeacherNotInCourse('Teacher not in course.')

        user_m = UserManager(session=current_user.session)
        lab_m.delete_lab(lab_id=lab_id, user_m=user_m)
        return flask.jsonify({'success': True})

    except TeacherNotInCourse as error:
        LOG.error('%s UID: %s, CID: %s' % (str(error), current_user.user_id, course_id))
        return flask.jsonify(
            success=False,
            feedback=str(error)
        )


# TODO(jiah): Move this to edit blueprint
@api.route('/lab/save', methods=['POST'])
@requires_roles('admin', 'teacher')
@error_handling
def lab_save():
    """Save an edited lab.

    flask.request input:
        * **lab_title**: The new title for the lab.
        * **lab_description**: The new description for the lab.
        * **lab_id**: Lab id of the lab whose information is to be saved.
        * **lab_internet**: The wanted status for the current lab (True/False).
    """

    # TODO: if the title of the lab need to be cahnged to it by cli.
    # Remember to change image names, instance name and
    # instance property image_name! Otherwise nothing connected to this lab will work.

    try:
        # TODO: rewrite to use post instead!
        lab_title = flask.request.form['lab_title']
        lab_description = flask.request.form['lab_description']
        lab_id = flask.request.form['lab_id']

        lab_m = LabManager(session=current_user.session)
        course_m = CourseManager(session=current_user.session)
        lab = lab_m.get(project=lab_id)

        if current_user.role == 'teacher':
            if not course_m.check_in_course(user_id=current_user.user_id,
                                            course_id=lab.domain_id):
                raise TeacherNotInCourse('Teacher not in course.')

        lab_m.update(
            project=lab_id,
            description=lab_description
        )

        return flask.jsonify(success=True)

    except TeacherNotInCourse as error:
        LOG.error(
            '%s UID: %s, CID: %s' % (str(error), current_user.user_id, lab.domain_id))
        return flask.jsonify(
            success=False,
            feedback=str(error)
        )


@api.route('/lab/launch', methods=['POST'])
@requires_roles('teacher', 'student')
@error_handling
def lab_launch():
    """Create an instance in a specified lab.

    flask.request input:
        **lab_id**: Lab id of the lab to which the specified instance is to \
            belong.
    """

    class NotInCourse(Exception):
        pass

    try:
        lab_id = flask.request.values['lab_id']

        course_m = CourseManager(session=current_user.session)
        lab_m = LabManager(session=current_user.session)

        lab = lab_m.get(lab_id)
        if not course_m.check_in_course(current_user.user_id, lab.domain_id):
            raise NotInCourse('User not in course.')

        lab_m.launch_lab(lab_id=lab_id)
        return flask.jsonify(success=True)

    except (InstanceManagerTooManyActiveInstancesInLab,
            InstanceManagerTooManyLabs,
            InstanceManagerAnotherActiveLab) as error:
        return flask.jsonify(success=False, feedback=str(error))
    except NotInCourse as error:
        LOG.debug(
            '%s UID: %s, CID: %s' %
            (str(error), current_user.user_id, lab.domain_id)
        )


@api.route('/lab/remove_image', methods=['POST'])
@requires_roles('admin', 'teacher')
@error_handling
def lab_remove_image():
    """Delete a specified image from a specified lab.

    flask.request input:
        * **lab_id**: Lab id of the lab where the image should be removed.
        * **image_id**: The image id of the image that should be removed form \
            the lab.
    """

    try:
        lab_id = flask.request.values['lab_id']
        image_id = flask.request.values['image_id']

        lab_m = LabManager(session=current_user.session)
        course_m = CourseManager(session=current_user.session)
        lab = lab_m.get(project=lab_id)

        if current_user.role == 'teacher':
            # TODO(vph): Should be "check_in_lab".
            if not course_m.check_in_course(user_id=current_user.user_id,
                                            course_id=lab.domain_id):
                raise TeacherNotInCourse('Teacher not in course.')

        # Searh images in lab and remove one instance
        for descriptor in lab.img_list:
            id = descriptor[0]
            quantity = int(descriptor[1])

            if id == image_id:
                descriptor[1] = quantity - 1
                if descriptor[1] <= 0:
                    lab.img_list.remove(descriptor)
                break

        lab_m.update(lab, img_list=lab.img_list)

        return flask.jsonify({'success': True})

    except TeacherNotInCourse as error:
        LOG.error(
            '%s UID: %s, CID: %s' % (str(error), current_user.user_id, lab.domain_id))
        return flask.jsonify(
            success=False,
            feedback=str(error)
        )


@api.route('/instance/delete', methods=['POST'])
@requires_roles('admin', 'teacher', 'student')
@error_handling
def instance_delete():
    """Delete a specified instance.

    flask.request input:
        * **instance_id**: Instance id of the instance to be deleted.
        * **lab_id**: Lab id of the lab to which the instance belongs.
    """

    lab_id = flask.request.values['lab_id']
    instance_id = flask.request.values['instance_id']

    lab_m = LabManager(session=current_user.session)

    lab = lab_m.get(lab_id)
    session = current_user.session
    if current_user.role != 'admin':
        session = authenticate(
            credentials=current_user.token,
            project_domain_name=lab.name.split('|')[0],
            project_name=lab.name
        )

    instance_m = InstanceManager(session=session)
    user_m = UserManager(session=current_user.session)

    instance_m.delete_instance(user_m=user_m,
                               session=current_user.session,
                               lab=lab,
                               instance_id=instance_id)

    return flask.jsonify({
        'success': True,
        'feedback': 'The instance was deleted.',
        'redirect': ''})


# TODO: Fix this poorly written function.
@api.route('/instance/shutdown', methods=['POST'])
@requires_roles('admin', 'teacher', 'student')
@error_handling
def instance_shutdown():
    """Shut down a specified instance.

    flask.request input:
        * **lab_id**: Lab id of the lab to which the instance belongs.
        * **instance_id**: Instance id of the instance to be shut down.
    """

    lab_id = flask.request.values['lab_id']
    instance_id = flask.request.values['instance_id']

    lab_m = LabManager(session=current_user.session)

    lab = lab_m.get(project=lab_id)
    session = current_user.session
    if current_user.role != 'admin':
        session = authenticate(
            credentials=current_user.token,
            project_domain_name=lab.name.split('|')[0],
            project_name=lab.name
        )

    instance_m = InstanceManager(session=session)
    user_m = UserManager(session=current_user.session)

    if instance_m.change_instance_state(user_m=user_m,
                                        lab_id=lab_id,
                                        instance_id=instance_id,
                                        expected_status='SHUTOFF') == 'SHUTOFF':
        return flask.jsonify({
            'success': True,
            'feedback': 'The instance has been shut down.',
            'redirect': ''})
    else:
        return flask.jsonify({
            'success': False,
            'feedback': 'The instance has not been shut down.',
            'redirect': ''})


@api.route('/instance/reboot', methods=['POST'])
@api.route('/instance/resume', methods=['POST'])
@api.route('/instance/start', methods=['POST'])
@requires_roles('teacher', 'student')
@error_handling
def instance_start_resume_reboot():
    """Start or resume a specified instance as a logged in user.

    flask.request input:
        * **instance_id**: Instance id of the instance which to start or resume.
        * **lab_id**: Lab id of the lab to which the specified instance belongs.
    """

    try:
        lab_id = flask.request.values['lab_id']
        instance_id = flask.request.values['instance_id']

        lab_m = LabManager(session=current_user.session)

        lab = lab_m.get(lab_id)
        course_name = lab.name.split('|')[0]
        lab_session = authenticate(
            credentials=current_user.token,
            project_domain_name=course_name,
            project_name=lab.name
        )

        instance_m = InstanceManager(session=lab_session)
        user_m = UserManager(session=current_user.session)

        new_state = instance_m.change_instance_state(user_m=user_m,
                                                     lab_id=lab_id,
                                                     instance_id=instance_id,
                                                     expected_status="ACTIVE")
        if new_state == "ACTIVE":
            #TODO(aber): We need more success/fail cases (suspend, resume, launch, stop...)
            return flask.jsonify({'success': True, 'feedback': 'Successfully started instance.'})
        else:
            return flask.jsonify({'success': False, 'feedback': 'Could not start instance'})

    except (InstanceManager404, InstanceManagerUnknownFault,
            InstanceManagerParameter) as error:
        LOG.exception(str(error))
        return flask.jsonify(result=False)


@api.route('/instance/suspend', methods=['POST'])
@requires_roles('admin', 'teacher', 'student')
@error_handling
def instance_suspend():
    """Suspend a specified instance.

    flask.request input:
        * **instance_id**: Instance id of the instance to be suspended.
        * **lab_id**: Lab id of the lab to which the specified instance belongs.
    """

    try:
        lab_id = flask.request.values['lab_id']
        instance_id = flask.request.values['instance_id']

        lab_manager = LabManager(session=current_user.session)
        lab = lab_manager.get(lab_id)

        session = current_user.session
        if current_user.role != 'admin':
            session = authenticate(
                credentials=current_user.token,
                project_domain_name=lab.name.split('|')[0],
                project_name=lab.name
            )

        instance_m = InstanceManager(session=session)
        user_m = UserManager(session=current_user.session)

        if instance_m.change_instance_state(user_m=user_m,
                                            lab_id=lab_id,
                                            instance_id=instance_id,
                                            expected_status="SUSPENDED") == "SUSPENDED":
            return flask.jsonify({
                'success': True,
                'feedback': 'Instance has been suspended'})
        else:
            return flask.jsonify({
                'success': False,
                'feedback': 'Could not suspend instance'})

    except (InstanceManager404, InstanceManagerUnknownFault) as error:
        LOG.exception(str(error))
        return flask.jsonify(result=False)


@api.route('/instance/get_vnc', methods=['POST'])
@requires_roles('admin', 'student', 'teacher')
@error_handling
def instance_get_vnc():
    """Retrieve a link to a vnc session for a specified instance.

    flask.request input:
        * **instance_id**: Instance id of the instance for which a VNC \
            session url is to be retrieved.
        * **lab_id**: Lab id of the lab to which the specified instance belongs.
    """

    lab_id = flask.request.values['lab_id']
    instance_id = flask.request.values['instance_id']

    lab_m = LabManager(session=current_user.session)

    lab = lab_m.get(lab_id)
    session = current_user.session
    if current_user.role != 'admin':
        session = authenticate(
            credentials=current_user.token,
            project_domain_name=lab.name.split('|')[0],
            project_name=lab.name
        )

    instance_m = InstanceManager(session=session)
    instance = instance_m.get(server=instance_id)

    # TODO(vph): Why doesn't this work? No `remote`, only `console`.
    vnc_url = instance.get_vnc_console('novnc')['console']['url']

    if not vnc_url:
        raise NoVNCLink('Found no VNC link')
    else:
        return flask.jsonify(
            success=True,
            feedback='Found a VNC link.',
            vnc=vnc_url
        )


@api.route('/instance/update', methods=['POST'])
@requires_roles('admin', 'student', 'teacher')
@error_handling
def instance_update():
    """Render an instance box upon an update.

    flask.request input:
        * **course_id**: Course id of the course where the lab with lab id can be found.
        * **lab_id**: Lab id e lab where the instance is to be retrieved from.
        * **instance_id**: Instance id of the instance to be edited.
    """

    lab_id = flask.request.form['lab_id']
    instance_id = flask.request.form['instance_id']

    lab_m = LabManager(session=current_user.session)
    user_m = UserManager(session=current_user.session)

    lab = lab_m.get(lab_id)
    session = current_user.session
    if current_user.role != 'admin':
        session = authenticate(
            credentials=current_user.token,
            project_domain_name=lab.name.split('|')[0],
            project_name=lab.name
        )

    instance_m = InstanceManager(session=session)
    instance = instance_m.get(server=instance_id)
    instance.owner = user_m.get(user=instance.user_id)
    # `instance.networks` is a dictionary of network name-ip
    # addresses pairs. There is only one IP address --
    # (key, [ip,]) -- which is indexed with [1][0].
    instance.ip = instance.networks.popitem()[1][0]

    return flask.render_template('update_instance.html', instance=instance)


@api.route('/image/upload', methods=['POST'])
@requires_roles('admin', 'teacher')
@error_handling
def image_upload():
    """
    When a teacher/admin tries to upload an image this function is called. It
    checks that the image the user tries to upload doesn't already exist. If
    it doesn't exist then it tries to create a new image on OpenStack and
    upload the image to the selected image library project (default, snapshots,
    images). This function will first upload the image to the web server
    and from there to OpenStack, the folder /tmp/ is used on the web server.

    flask.request input:
       * **file**: The file that the user wants to upload.
       * **flavor**:  The flavor that the user wants to use with the image.
       * **image_description**: Description of the image uploaded.
       * **image_keywords**: Keywords assigned to the image to ease the \
        search for the image.
       * **image_os**: The operating system this image uses.
       * **image_version**: The version of the operating system the image uses.
       * **image_type**: If the image is a default image, a snapshot or \
        another non-default image.
       * **image_internet**: If the image uploaded should have internet \
        access or not.
       * **image_name** (*form*): The name for the image.
    """

    file = flask.request.files['file']
    flavor = flask.request.form['flavor']
    image_description = flask.request.form['description']
    image_keywords = flask.request.form['keywords']
    image_os = flask.request.form['image_os']
    image_version = flask.request.form.get('image_version', '')
    image_type = flask.request.form['image_type']
    image_internet = 'True' if flask.request.form.get('internet') else 'False'
    username = flask.request.form['username']
    password = flask.request.form['password']
    image_name = flask.request.form['name']

    image_m = ImageManager(session=current_user.session)
    lab_m = LabManager(session=current_user.session)

    extension_check = file.filename.rsplit(sep='.', maxsplit=1)
    has_extension = len(extension_check) > 1
    allowed_extentions = [extension.strip() for extension in
                          APP.iniconfig.get('resela', 'allowed_extensions').split(',')]

    if not has_extension or extension_check[-1] not in allowed_extentions:
        return flask.jsonify({'success': False, 'feedback': 'Invalid file extension'})

    image_hash, image_size = FileHandler.hash_file(file.stream)
    # TODO(vph): This is not nice.
    image_size /= (1024 * 1024 * 1024)

    # Error conditions.
    if image_size > APP.iniconfig.getfloat('resela', 'upload_limit'):
        raise ExceedsUploadLimit('The image size exceeds the upload limit.')

    if any(image.checksum == image_hash for image in image_m.list()):
        raise MD5Match('The file is already present in the library.')

    if image_type == 'Default' and current_user.role != 'admin':
        raise DefaultNotAuthorized('Not authorized to create default image.')

    # Create a new image in OpenStack.
    if image_type == 'Default':
        image_type = 'imageLibrary|default'
    elif image_type == 'Snapshot':
        image_type = 'imageLibrary|snapshots'
    else:
        image_type = 'imageLibrary|images'
    # TODO(vph): Should have an else-case that raises an exception.

    lab = lab_m.find(name=image_type)

    new_image = image_m.create(
        name='{}|{}'.format(lab.name, image_name),
        flavor_name=str(flavor),
        img_format='qcow2',
        disk_format='qcow2',
        container_format='bare',
        owner=lab.id,
        description=image_description,
        keywords=image_keywords.lower(),
        os=DATABASE.session.query(OS).filter(OS.id == image_os).first().name,
        version=image_version,
        internet=image_internet,
        password=password if password else '<No password>',
        username=username if username else '<No username>'
    )

    # Upload the image file, assigning it to the newly created image.

    file.stream.seek(0)
    image_m.upload(image_id=new_image.id, image_data=file.stream)

    lab.img_list.append(new_image.id)
    lab_m.update(lab, img_list=lab.img_list)

    return flask.jsonify({
        'success': True,
        'feedback': ''
    })


@api.route('/library/add_image', methods=['POST'])
@requires_roles('teacher')
@error_handling
def library_add_image():
    """Bind an image to a specified lab by adding the image id to the lab.

    Flask input:
        * **selected_lab_id**: The id of the lab the user wants to bind the \
            image to.
        * **selected_image_id**: The id of the image the user wants to bind \
            to a lab.
    """

    class NotInCourse(Exception):
        pass

    try:
        selected_lab_id = flask.request.form['lab_id']
        selected_image_id = flask.request.form['image_id']

        lab_m = LabManager(session=current_user.session)
        course_m = CourseManager(session=current_user.session)
        image_m = ImageManager(session=current_user.session)

        lab = lab_m.get(project=selected_lab_id)

        if not course_m.check_in_course(current_user.user_id, lab.domain_id):
            raise NotInCourse("Not in course.")

        bumped = False
        for image_descriptor in lab.img_list:
            if image_descriptor[0] == selected_image_id:
                bumped = True
                image_descriptor[1] = str(int(image_descriptor[1]) + 1)
                break

        if not bumped:
            lab.img_list.append([selected_image_id, '1'])

        image = image_m.get(selected_image_id)

        if image.internet == 'False' and lab.internet:
            lab.internet = False

        lab_m.update(
            project=selected_lab_id,
            img_list=lab.img_list,
            internet=lab.internet
        )

        return flask.jsonify({
            'success': True,
            'redirect': flask.url_for('default.lab',
                                      lab_id=selected_lab_id,
                                      course_id=lab.domain_id)
        })

    except NotInCourse as error:
        LOG.exception(msg=str(error))
        return flask.jsonify(success=False, feedback=str(error))


@api.route('/library/remove_image', methods=['POST'])
@requires_roles('admin', 'teacher')
@error_handling
def library_remove_image():
    """Delete a specified image.

    flask.request input:
        * **image_id**: The id of the image to delete.
    """

    image_id = flask.request.values['image_id']

    lab_m = LabManager(session=current_user.session)
    image_m = ImageManager(session=current_user.session)
    image_is_used = False

    for lab in lab_m.list():
        if '|' in lab.name:
            if lab.name.split('|')[0] not in ('imageLibrary', 'snapshotFactory'):
                for tmp_image in lab.img_list:
                    image_is_used = (image_id == tmp_image[0])
                    if image_is_used:
                        break
            elif 'snapshotFactory' in lab.name:
                image_is_used = (lab.base_img == image_id)

    if image_is_used:
        raise ImageIsUsed('Image is used.')

    image = image_m.get(image_id=image_id)
    tmp_lab = lab_m.get(project=image.owner)

    permitted_lab_names = [
        'imageLibrary|{}'.format(sub)
        for sub in ('default', 'snapshots', 'images')
        ]

    if tmp_lab.name not in permitted_lab_names:
        raise UnpermittedLabName('Lab name not in permitted labs.')

    if tmp_lab.name == 'imageLibrary|default' and current_user.role != 'admin':
        raise DefaultNotAuthorized('Must be admin to remove from default.')

    tmp_lab.img_list.remove(image_id)
    lab_m.update(tmp_lab, img_list=tmp_lab.img_list)
    image_m.delete(image_id)

    return flask.jsonify(result=True)


@api.route('/database/add_user', methods=['POST'])
@error_handling
def database_add_user():
    """Add users to Resela.

    Creates a network together with a subnet on a separate VLAN for each
    added user. A password will be generated and sent to the user by email.
    A VPN for the user is also created.

    The `users` string separate users by semi-colon and user attributes by
    comma.

    flask.request input:
        * **role**: The role of the new users.
        * **users**: A semi-colon separated string with users.
    """

    # TODO(vph): Add docstring.

    users = flask.request.values['users']
    role = flask.request.values['role']

    user_m = UserManager(current_user.session)
    lab_m = LabManager(current_user.session)

    # Check given role is correct
    if role not in ('student', 'teacher'):
        return flask.jsonify({'success': False, 'feedback': 'Invalid user role'})

    # Data formatting, remove whitespace and split users on semicolon
    users = users.replace(' ', '').replace('\r', '').replace('\n', '')
    for user_to_add in users.split(';'):
        user_email, user_first_name, user_last_name = user_to_add.split(',', 2)
        user_email = user_email.lower()

        # Generate random password
        password = ''.join(
            choice(ascii_uppercase + digits + ascii_lowercase)
            for _ in range(10)
        )

        # add user
        user = user_m.add_user(user_email, user_first_name.title(),
                               user_last_name.title(), password, role)
        if role == 'teacher':
            lab_m.create_snapshot_factory_project(user)

        # Send email to user
        UserManager.email_user(to_email=user_email, password=password)

    flask.flash('Users successfully created!', 'success')
    return flask.jsonify({'success': True, 'feedback': ''})


@api.route('/version/<string:os>')
@requires_roles('admin', 'teacher')
@error_handling
def get_version(os):
    """Retrieve a list of the OS versions of a specified OS.

    flask.request input:
        * **os**: Name of the OS.

    """

    selected_os = OS.query.filter(OS.id == os).one()
    available_versions = [
        version.version
        for version in Version.query.all()
        if version.os == selected_os.id
        ]

    return flask.jsonify({
        'success': True,
        'version': available_versions
    })


@api.route('/library/search-for-images', methods=['POST'])
@requires_roles('admin', 'teacher')
@error_handling
def search_for_images():
    """Retrieve a list of image ids that a specified set of search critera.

    Flask session input:
        * **search_keyword**: String containing the keywords used in the \
            search.
        * **search_internet**: String ('True'/'False') indicating if the \
            images searched for should have internet access.
        * **search_os**: Integer that identifies which os is used in the \
            search.
        * **search_version**: String with the version of the selected os that \
            the search is using.
        * **search_flavor**: String with the flavor that the search is using.
    """

    image_m = ImageManager(session=current_user.session)
    search_keyword = flask.request.form['keywords']
    search_internet = flask.request.form['internet']
    search_os = flask.request.form['os']
    search_version = flask.request.form['version']
    search_flavor = flask.request.form['flavor']
    search_library = flask.request.form['library']
    selected_os = DATABASE.session.query(OS).filter(OS.id == search_os).first()
    lowercase_keyword = search_keyword.lower()
    all_images = image_m.list()
    matched_images = []
    for image in all_images:
        if (lowercase_keyword == '' or any(
                    keyword in image.keywords.split(',') for keyword in
                    lowercase_keyword.split(','))) \
                and (search_internet == '' or search_internet == image.internet) \
                and (search_os == '' or selected_os.name == image.os) \
                and (search_version == '' or search_version == image.version) \
                and (search_flavor == '' or search_flavor == image.flavor_name) \
                and (search_library == '' or search_library.lower() ==
                    image.name.split('|')[1]):
            matched_images.append(image.id)
    return flask.jsonify({'success': True, 'images': matched_images})


@api.route('/library/download_image/<string:image_id>')
@requires_roles('admin', 'teacher')
@error_handling
def download_image(image_id):
    """Download a specified image.

    Flask input:
        * **image_id**: Image id of the image to be downloaded.

    """

    # TODO(vph): Add docstring arguments.

    image_m = ImageManager(session=current_user.session)
    image = image_m.get(image_id=image_id)
    download_filename = '{name}_{os}_{version}.img'.format(
        name=image.name.split('|')[2],
        os=image.os,
        version=image.version
    )

    tmp_file = tempfile.NamedTemporaryFile()
    for chunk in image_m.data(image_id):
        tmp_file.write(chunk)

    @after_this_request
    def tmp_cleanup(response):
        tmp_file.close()
        return response

    return flask.send_from_directory(
        directory=tempfile.tempdir,
        filename=tmp_file.name.split('/')[2],
        attachment_filename=download_filename,
        as_attachment=True
    )


@api.route('/snapshot_factory/assign/<string:image_id>', methods=['POST'])
@requires_roles('teacher')
@error_handling
def snapshot_factory_assign(image_id):
    """Assign an image from the image library to the snapshot factory.

    Flask input:
        * **image_id**: Image id of the image to be assigned.
    """

    # TODO(vph): Add docstring arguments.

    lab_m = LabManager(current_user.session)
    image_m = ImageManager(current_user.session)

    factory_name = 'snapshotFactory|{}'.format(current_user.email)
    snapshot_lab = lab_m.find(name=factory_name)

    if snapshot_lab.base_img != '':
        raise NoBaseImage("There's already an image assigned in the snapshot factory")

    base_image = image_m.get(image_id)
    lab_m.update(snapshot_lab,
                 base_img=image_id,
                 img_name=base_image.name.split('|')[2],
                 description=base_image.description,
                 keywords=base_image.keywords,
                 internet=base_image.internet,
                 os=base_image.os,
                 version=base_image.version,
                 flavor=base_image.flavor_name,
                 username=base_image.username,
                 password=base_image.password)

    return flask.jsonify({
        'success': True,
        'feedback': 'Successfully assigned image to snapshot factory',
        'redirect': flask.url_for('default.snapshot_factory')
    })


@api.route('/snapshot_factory/save', methods=['POST'])
@requires_roles('teacher')
@error_handling
def snapshot_factory_save():
    """Save metadata about a snapshot factory lab.

    Flask input:
        * **description**: The current description for the snapshot.
        * **keywords**: The current keywords for the snapshot.
        * **internet**: The current internet status for the snapshot.
        * **username**: The current username for the snapshot.
        * **password**: The current password for the snapshot.
    """

    description = flask.request.form['description']
    keywords = flask.request.form['keywords']
    internet = 'True' if flask.request.form.get('internet') == 'true' else 'False'
    username = flask.request.form.get('username')
    password = flask.request.form.get('password')
    flavor = flask.request.form['flavor']
    name = flask.request.form['name']

    if flavor == '':
        flavor = None

    lab_m = LabManager(current_user.session)
    factory_name = 'snapshotFactory|{}'.format(current_user.email)
    snapshot_lab = lab_m.find(name=factory_name)

    if snapshot_lab.base_img == '':
        raise NoBaseImage('No base image assigned to the snapshot factory.')

    image_m = ImageManager(current_user.session)
    base_image = image_m.get(snapshot_lab.base_img)

    # If the base image can't use internet the snapshot can't use internet as well
    # due to security reasons
    can_use_internet = internet
    if base_image.internet == 'False' and can_use_internet == 'True':
        can_use_internet = base_image.internet

    lab_m.update(snapshot_lab,
                 img_name=name,
                 description=description,
                 keywords=keywords,
                 internet=can_use_internet,
                 flavor=flavor,
                 username=username if username != '' else '<No username>',
                 password=password if password != '' else '<No password>')

    if can_use_internet == internet:
        return flask.jsonify({
            'success': True,
            'feedback': 'Successfully saved the info for the snapshot',
            'internet': True
        })
    else:
        return flask.jsonify({
            'success': True,
            'feedback': 'Successfully saved the info for the snapshot. However could'
                        ' not enable internet since the base image shall not have '
                        'internet access',
            'internet': False
        })


@api.route('/snapshot_factory/revert', methods=['POST'])
@requires_roles('teacher')
@error_handling
def snapshot_factory_revert():
    """Revert information set about a snapshot.

    The original information stored in the base image.
    """

    lab_m = LabManager(current_user.session)
    image_m = ImageManager(current_user.session)
    factory_name = 'snapshotFactory|{}'.format(current_user.email)
    snapshot_lab = lab_m.find(name=factory_name)

    if snapshot_lab.base_img == '':
        raise NoBaseImage('No base image assigned to the snapshot factory.')

    base_image = image_m.get(snapshot_lab.base_img)

    lab_m.update(snapshot_lab,
                 img_name=base_image.name.split('|')[2],
                 description=base_image.description,
                 keywords=base_image.keywords,
                 internet=base_image.internet,
                 flavor=base_image.flavor_name,
                 username=base_image.username,
                 password=base_image.password)

    return flask.jsonify({
        'success': True,
        'feedback': 'Successfully reverted the info to the original info'
    })


@api.route('/snapshot_factory/delete', methods=['POST'])
@requires_roles('teacher')
@error_handling
def snapshot_factory_delete():
    """Delete the current snapshot from the snapshot factory."""

    lab_m = LabManager(session=current_user.session)
    factory_name = 'snapshotFactory|{}'.format(current_user.email)
    snapshot_lab = lab_m.find(name=factory_name)

    if snapshot_lab.base_img == '':
        raise NoBaseImage('No base image assigned to the snapshot factory.')

    session = authenticate(
        credentials=current_user.token,
        project_domain_name='snapshotFactory',
        project_name=factory_name
    )

    instance_m = InstanceManager(session=session)

    if len(instance_m.list()) != 0:
        instance_m.delete(instance_m.list()[0])

    lab_m.update(snapshot_lab,
                 base_img='',
                 img_name='',
                 description='',
                 keywords='',
                 internet='',
                 flavor='',
                 os='',
                 version='',
                 username='',
                 password='')

    return flask.jsonify({
        'success': True,
        'feedback': 'Successfully deleted the snapshot'
    })


@api.route('/snapshot_factory/create_snapshot', methods=['POST'])
@requires_roles('teacher')
@error_handling
def snapshot_factory_create_snapshot():
    """Create a snapshot from the currently running instance."""

    lab_m = LabManager(current_user.session)
    factory_name = 'snapshotFactory|{}'.format(current_user.email)
    snapshot_lab = lab_m.find(name=factory_name)

    if snapshot_lab.base_img == '':
        raise NoBaseImage('No base image assigned to the snapshot factory.')

    session = authenticate(
        credentials=current_user.token,
        project_domain_name='snapshotFactory',
        project_name=factory_name
    )

    instance_m = InstanceManager(session=session)

    if len(instance_m.list()) == 0:
        raise NoInstanceFound('No instance available.')

    snapshot_library = lab_m.find(name="imageLibrary|snapshots")
    meta = {'description': snapshot_lab.description,
            'keywords': snapshot_lab.keywords,
            'internet': snapshot_lab.internet,
            'flavor_name': snapshot_lab.flavor,
            'username': snapshot_lab.username,
            'password': snapshot_lab.password}
    image = instance_m.create_image(instance_m.list()[0],
                                    'imageLibrary|snapshots|{}'.format(
                                        snapshot_lab.img_name),
                                    metadata=meta)

    image_m = ImageManager(current_user.session)

    # Loop that waits for the image to be created from the instance.
    # Needs to be completely built before proceeding
    building = True
    snapshot = None
    while building:
        snapshot = image_m.get(image)
        if snapshot.status == 'active':
            building = False
        else:
            time.sleep(1)

    try:
        # Update the image owner from snapshot factory to image library snapshot project
        image_m.update(snapshot.id, owner=snapshot_library.id)
    except HTTPException:
        # Image cleanup upon owner change
        image_m.delete(snapshot.id)

        msg = 'Problem with unsupported media type.'
        LOG.exception(msg)
        return flask.jsonify(success=False, feedback=msg)

    snapshot_library.img_list.append(snapshot.id)
    lab_m.update(snapshot_library, img_list=snapshot_library.img_list)

    # Delete current instance
    instance_m.delete(instance_m.list()[0])

    # Snapshot factory clean up
    lab_m.update(snapshot_lab,
                 base_img='',
                 description='',
                 keywords='',
                 internet='',
                 flavor='',
                 os='',
                 version='',
                 username='',
                 password='')

    return flask.jsonify({
        'success': True,
        'feedback': "Successfully create an snapshot and added it to the snapshot "
                    "library",
        'redirect': flask.url_for('admin.image_library')
    })


@api.route('/snapshot_factory/create_instance', methods=['POST'])
@requires_roles('teacher')
@error_handling
def snapshot_factory_create_instance():
    """Create an instance for the snapshot factory based on the base image."""

    try:
        lab_m = LabManager(current_user.session)
        image_m = ImageManager(current_user.session)
        flavor_m = FlavorManager(current_user.session)
        user_m = UserManager(current_user.session)

        factory_name = 'snapshotFactory|{}'.format(current_user.email)
        snapshot_lab = lab_m.find(name=factory_name)

        if snapshot_lab.base_img == '':
            raise NoBaseImage('No base image assigned to the snapshot factory.')

        snapshot_lab_session = authenticate(
            credentials=current_user.token,
            project_domain_name='snapshotFactory',
            project_name=factory_name
        )

        instance_m = InstanceManager(session=snapshot_lab_session)

        if len(instance_m.list()) != 0:
            raise InstanceExists("Can't create an instance, one instance already exists!")

        instance_m.create_instance(
            lab=snapshot_lab,
            instance_name=factory_name,
            image=image_m.get(snapshot_lab.base_img),
            flavor=flavor_m.find(name=snapshot_lab.flavor),
            user_session=current_user.session,
            user_m=user_m
        )

        return flask.jsonify({
            'success': True,
            'feedback': 'Successfully created an instance'})

    except (InstanceManagerTooManyActiveInstancesInLab,
            InstanceManagerTooManyLabs,
            InstanceManagerAnotherActiveLab) as error:
        return flask.jsonify(success=False, feedback=str(error))


@api.route('/snapshot_factory/shutdown_instance', methods=['POST'])
@requires_roles('teacher')
@error_handling
def snapshot_factory_shutdown_instance():
    """Shut down the current instance in the snapshot factory."""

    lab_m = LabManager(current_user.session)
    factory_name = 'snapshotFactory|{}'.format(current_user.email)
    snapshot_lab = lab_m.find(name=factory_name)

    if snapshot_lab.base_img == '':
        raise NoBaseImage('No base image assigned to the snapshot factory.')

    session = authenticate(
        credentials=current_user.token,
        project_domain_name='snapshotFactory',
        project_name=factory_name
    )

    instance_m = InstanceManager(session=session)
    user_m = UserManager(session=session)

    if len(instance_m.list()) == 0:
        raise NoInstanceFound('No instance available.')

    instance = instance_m.list()[0]
    instance_m.change_instance_state(
        user_m=user_m,
        lab_id=snapshot_lab.id,
        instance_id=instance.id,
        expected_status='SHUTOFF'
    )


@api.route('/instance/show/<string:instance_id>')
@requires_roles('admin', 'teacher', 'student')
@error_handling
def instance_box(instance_id):

    instance_m = InstanceManager(session=current_user.session)
    image_m = ImageManager(session=current_user.session)

    instance = None
    # This is shit, but has to be
    for i in instance_m.list(search_opts={'all_tenants': True}):
        if i.id == instance_id:
            instance = i
            break

    if not instance:
        NoInstanceFound('No instance was found')

    if 'snapshotFactory' not in instance.name:
        instance.owner = instance.name.split('|')[2]
    else:
        instance.owner = instance.name.split('|')[1]

    instance.is_owner = instance.owner == current_user.email

    if instance.networks:
        instance.ip = instance.networks.popitem()[1][0]

    image = image_m.get(image_id=instance.image['id'])

    if hasattr(image, 'username'):
        username = image.username
    else:
        username = ''
        LOG.warning('Image %s has no username.' % image.id)

    if hasattr(image, 'password'):
        password = image.password
    else:
        password = ''
        LOG.warning('Image %s has no password.' % image.id)

    return flask.render_template(
        'instance_box.html',
        instance=instance,
        username=username,
        password=password
    )
