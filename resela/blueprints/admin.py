"""
admin.py
********

This blueprint defines routes and functions exclusive to the admin.
Checks are performed to see if the user is an admin
since only admins are allowed on these pages.
"""

import flask
import logging

from flask_login import login_required, current_user
from functools import partial

from resela.app import APP
from resela.backend.managers.LabManager import LabManager
from resela.backend.managers.GroupManager import GroupManager
from resela.backend.managers.UserManager import UserManager
from resela.backend.managers.CourseManager import CourseManager
from resela.backend.managers.FlavorManager import FlavorManager
from resela.backend.managers.ImageManager import ImageManager
from resela.backend.managers.RoleManager import requires_roles
from resela.backend.managers.ErrorManager import error_handling
from resela.backend.SqlOrm.OsModel import OS
from resela.backend.SqlOrm.VersionModel import Version


admin = flask.Blueprint('admin', __name__, url_prefix='/admin')
LOG = logging.getLogger(__name__)
error_handling = partial(error_handling, log=LOG)


@admin.route('/students')
@login_required
@requires_roles('admin', 'teacher')
@error_handling
def students():
    """Render a student overview page.

    Information about all students is retrieved and passed to the template
    rendering function.
    """

    group_manager = GroupManager(current_user.session)
    student_group = group_manager.find(name='students')

    user_manager = UserManager(current_user.session)
    students_object_list = user_manager.list(group=student_group.id)

    return flask.render_template('admin/students.html',
                                 students=students_object_list)


@admin.route('/teachers')
@login_required
@requires_roles('admin')
@error_handling
def teachers():
    """Render a teacher overview page.

    Information about all teachers is retrieved and passed to the template
    rendering function.
    """

    group_manager = GroupManager(current_user.session)
    teacher_group = group_manager.find(name='teachers')

    user_manager = UserManager(current_user.session)
    teacher_object_list = user_manager.list(group=teacher_group.id)

    return flask.render_template('admin/teachers.html',
                                 teachers=teacher_object_list)


@admin.route('/image_library')
@login_required
@requires_roles('admin', 'teacher')
@error_handling
def image_library():
    """Render an overview page for virtual machine images.

    Information about all virtual machine images is retrieved and passed
    to the template rendering function.
    """

    flavor_manager = FlavorManager(session=current_user.session)
    image_manager = ImageManager(session=current_user.session)
    lab_manager = LabManager(session=current_user.session)
    course_m = CourseManager(session=current_user.session)

    flavors = flavor_manager.list()
    images = [image for image in image_manager.list() if image.status == 'active']
    course_w_labs = []
    version = Version.query.all()
    os = OS.query.all()
    if current_user.role == 'teacher':
        courses = [course for course in course_m.list_courses()
                   if course_m.check_in_course(current_user.user_id, course.id)]

        course_w_labs = {}
        for course in courses:
            labs = lab_manager.list(domain=course)
            course_w_labs[course.name] = {'labs': labs}

    extensions_list = APP.iniconfig.get('resela', 'allowed_extensions').split(',')
    extensions = ','.join(['.{}'.format(extension.strip()) for extension in extensions_list])

    return flask.render_template('admin/image_library.html',
                                 images=images,
                                 flavors=flavors,
                                 course_w_labs=course_w_labs,
                                 version=version,
                                 os=os,
                                 extensions=extensions)
