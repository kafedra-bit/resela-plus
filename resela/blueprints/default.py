"""
default.py
**********

This serves as the main route-file, or controller, for the flask application.
It also imports the blueprints and handles some of the general routes.
"""

import logging


from functools import partial

import flask
from flask import render_template, abort
from flask_login import login_required, current_user

from resela.backend.managers.CourseManager import CourseManager
from resela.backend.managers.ErrorManager import error_handling
from resela.backend.managers.FlavorManager import FlavorManager
from resela.backend.managers.GroupManager import GroupManager
from resela.backend.managers.ImageManager import ImageManager
from resela.backend.managers.InstanceManager import InstanceManager
from resela.backend.managers.LabManager import LabManager
from resela.backend.managers.RoleManager import requires_roles
from resela.backend.managers.UserManager import UserManager
from resela.model.SystemStats import SystemStatus
from resela.model.User import authenticate

default = flask.Blueprint('default', __name__)
LOG = logging.getLogger(__name__)
error_handling = partial(error_handling, log=LOG)


@default.route('/')
@error_handling
def index():
    """Render the index page.

    Un-authenticated users are redirected to the login page.
    """

    # If user is not logged in, redirect to login
    if not current_user.is_authenticated:
        return flask.redirect(flask.url_for('account.login'))

    if current_user.role == 'admin':
        kwargs = SystemStatus.get_for_admin()
    elif current_user.role == 'teacher':
        kwargs = SystemStatus.get_for_teacher()
    else:
        kwargs = SystemStatus.get_for_student()

    return render_template('default/index.html', **kwargs)


@default.route('/courses')
@login_required
@requires_roles('admin', 'teacher', 'student')
@error_handling
def courses():
    """Render a course overview page.

    Information about the user's courses and labs is
    retrieved and passed to the template rendering function. Admin can view
    all courses while teacher and student get courses they a part of.
    """

    course_manager = CourseManager(current_user.session)
    lab_manager = LabManager(current_user.session)

    # TODO(vph): Put this somewhere else.
    ignore_course = ['imageLibrary', 'default', 'Default', 'heat', 'snapshotFactory']

    # Admin should see all courses
    if current_user.role == 'admin':
        course_list = [course for course in course_manager.list()
                       if course.name not in ignore_course]
    else:
        course_list = [course_manager.find(name=name) for name in
                       course_manager.get_course_names(current_user.user_id)
                       if name not in ignore_course]

    for course in course_list:
        course.labs = lab_manager.list(domain=course)

    return flask.render_template('default/courses.html', courses=course_list)


@default.route('/user/<string:user_id>')
@login_required
@requires_roles('admin', 'teacher')
@error_handling
def user(user_id):
    """Render an overview page for a specified user.

    Information about the user and the user's courses and labs is retrieved and
    passed to the template rendering function.
    """

    course_manager = CourseManager(session=current_user.session)
    group_manager = GroupManager(session=current_user.session)
    user_manager = UserManager(session=current_user.session)

    course_list = []

    for item in group_manager.list(user=user_id):
        result = item.name.split('|')[0]
        if result not in ('students', 'teachers'):
            course_list.append(course_manager.get(item.domain_id))

    student_object = user_manager.get(user_id)

    return render_template('default/user.html',
                           student=student_object,
                           courses=course_list,
                           user_id=user_id)


@default.route('/lab/<string:lab_id>')
@login_required
@requires_roles('admin', 'teacher', 'student')
@error_handling
def lab(lab_id):
    """
    Render an overview page for a specified lab, adjusted according to the
    user's privileges.

    Information about the lab is retrieved, if the user has access to it.
    The information is then passed to a template rendering function.

    Flask input:
        * **lab_id**: Lab id of the lab whose information is to be displayed.
    """

    lab_m = LabManager(current_user.session)
    course_m = CourseManager(session=current_user.session)
    instance_m = InstanceManager(session=current_user.session)
    lab_object = lab_m.get(lab_id)

    if current_user.role == 'admin' or course_m.check_in_course(
            current_user.user_id, lab_object.domain_id):

        image_m = ImageManager(session=current_user.session)

        # TODO(aber): Only take instances in the lab and not all started by the user
        if current_user.role == 'admin':
            instances = instance_m.list(search_opts={'all_tenants': True})
        else:
            instances = instance_m.list_my_instances()
        lab_object.instances = [i for i in instances if i.tenant_id == lab_object.id]

        images = []
        image_amounts = []
        for image_descriptor in lab_object.img_list:
            images.append(image_m.get(image_descriptor[0]))
            image_amounts.append(image_descriptor[1])

        image_descriptors = zip(images, image_amounts)

        flavor_manager = FlavorManager(current_user.session)
        flavors = flavor_manager.list()
        return render_template('default/lab.html',
                               lab=lab_object,
                               flavor=flavors,
                               image_descriptors=image_descriptors)
    else:
        flask.flash('You are not in this course.', 'error')
        abort(403, description='You are not in this course.')


@default.route('/active_vm')
@requires_roles('admin', 'teacher', 'student')
@error_handling
def active_vm():
    """
    Render an overview page displaying a user's active virtual machine
    instances.

    Information about the user's virtual machine instances is retrieved and
    passed to the template rendering function.
    """

    lab_m = LabManager(session=current_user.session)
    course_m = CourseManager(session=current_user.session)

    # Get all courses
    if current_user.role == 'admin':
        courses = course_m.list_courses()
    else:
        courses = course_m.list_my_courses()

    courses_names = [c.name for c in courses]

    # Get all instances
    instance_m = InstanceManager(session=current_user.session)
    if current_user.role == 'admin':
        instances = instance_m.list(search_opts={'all_tenants': True})
    elif current_user.role == 'teacher':
        i_list = instance_m.list(search_opts={'all_tenants': True})
        instances = [i for i in i_list if i.name.split('|')[0] in courses_names]
    else:
        instances = instance_m.list_my_instances()

    # Students and teacher see only those courses to which they belong.
    # Admins see all courses.
    for course in courses:
        course.labs = lab_m.list(domain=course)

        for lab in course.labs:
            lab.instances = []
            for instance in instances:
                instance_parent = instance.name.rsplit('|', 1)[0]
                if instance_parent == lab.name:
                    lab.instances.append(instance)

            lab.qty_active = len([i for i in lab.instances if i.status == 'ACTIVE'])
            lab.qty_error = len([i for i in lab.instances if i.status == 'ERROR'])

    return flask.render_template('default/active_vm.html', courses=courses)


@default.route('/snapshot_factory')
@login_required
@requires_roles('teacher')
@error_handling
def snapshot_factory():
    """Render a snapshot creation page."""

    # TODO(vph): Add proper docstring.

    lab_m = LabManager(current_user.session)
    flavor_m = FlavorManager(current_user.session)

    factory_name = 'snapshotFactory|{}'.format(current_user.email)
    snapshot_lab = lab_m.find(name=factory_name)
    flavors = flavor_m.list()
    current_flavor = ''
    if snapshot_lab.flavor != '':
        current_flavor = list(filter(lambda x: x.name == snapshot_lab.flavor, flavors))[0]
        flavors = [flavor for flavor in flavors if flavor.disk >= current_flavor.disk]

    session = authenticate(
        credentials=current_user.token,
        project_domain_name='snapshotFactory',
        project_name=factory_name
    )

    instance_m = InstanceManager(session=session)
    instance = None

    if len(instance_m.list()) != 0:
        instance = instance_m.list()[0]

    return render_template('snapshot_factory.html',
                           user=user,
                           current_flavor=current_flavor,
                           flavors=flavors,
                           snapshot_factory=snapshot_lab,
                           instance=instance)

