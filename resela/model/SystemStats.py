"""

SystemStats.py
**************

"""

from flask_login import current_user
from novaclient.client import Client

from resela.backend.managers.CourseManager import CourseManager
from resela.backend.managers.InstanceManager import InstanceManager
from resela.backend.managers.ImageManager import ImageManager
from resela.backend.managers.LabManager import LabManager


class SystemStatus:
    """
    Class used for retrieving system stats for admins and teachers
    """

    @staticmethod
    def get_for_admin():
        """
        Retrieves system information that is shown by the admin on the index page.
        :param current_user: The current user(admin) that wants to get system information.
        :return: Dict containing the various variables used on the index page.
        """

        client = Client(session=current_user.session, version='2')
        hypervisors = client.hypervisors.list()
        system_wide_stats = {
            'ram': {
                'total': 0,
                'used': 0
            },
            'vcpu': {
                'total': 0,
                'used': 0
            },
            'disk': {
                'total': 0,
                'used': 0
            },
            'vms': 0
        }

        for hypervisor in hypervisors:
            system_wide_stats['ram']['total'] += hypervisor.memory_mb
            system_wide_stats['ram']['used'] += hypervisor.memory_mb_used
            system_wide_stats['vcpu']['total'] += hypervisor.vcpus
            system_wide_stats['vcpu']['used'] += hypervisor.vcpus_used
            system_wide_stats['disk']['total'] += hypervisor.local_gb
            system_wide_stats['disk']['used'] += hypervisor.local_gb_used
            system_wide_stats['vms'] += hypervisor.running_vms

        system_wide_stats['ram']['total'] /= 1024
        system_wide_stats['ram']['total'] = round(system_wide_stats['ram']['total'], 2)
        system_wide_stats['ram']['used'] /= 1024
        system_wide_stats['ram']['used'] = round(system_wide_stats['ram']['used'], 2)

        image_m = ImageManager(session=current_user.session)
        lab_m = LabManager(session=current_user.session)
        default_lib = lab_m.find(name='imageLibrary|default')
        snapshot_lib = lab_m.find(name='imageLibrary|snapshots')

        libraries = {'default': {'number': 0},
                     'snapshots': {'number': 0},
                     'images': {'number': 0}}

        for image in image_m.list():
            if image.owner == default_lib.id:
                libraries['default']['number'] += 1
            elif image.owner == snapshot_lib.id:
                libraries['snapshots']['number'] += 1
            else:
                libraries['images']['number'] += 1

        system_stats = {'system_wide_stats': system_wide_stats, 'hypervisors': hypervisors,
                        'libraries': libraries}

        return system_stats

    @staticmethod
    def get_for_teacher():

        def instance_filter(instance):
            return instance.tenant_id == lab.id

        # get courses and labs students and instances
        course_manager = CourseManager(current_user.session)
        lab_m = LabManager(current_user.session)
        instance_m = InstanceManager(current_user.session)

        ignore_course = ['imageLibrary', 'default', 'Default', 'heat', 'snapshotFactory']

        course_list = [course_manager.find(name=name) for name in
                       course_manager.get_course_names(current_user.user_id)
                       if name not in ignore_course]

        labs_total = 0
        labs_active = 0

        inst_total = 0
        inst_active = 0

        courses = []
        for course in course_list:
            course.labs = lab_m.list(domain=course)
            course.inst_active = 0
            course.inst_suspended = 0
            course.inst_shutdown = 0
            course.labs_active = 0
            for lab in course.labs:
                search_opts = {'all_tenants': True}
                lab.instances = 0
                for instance in filter(instance_filter, instance_m.list(search_opts=search_opts)):
                    lab.instances += 1
                    inst_total += 1
                    if instance.status == 'ACTIVE':
                        course.inst_active += 1
                        inst_active += 1
                    elif instance.status == 'SUSPENDED':
                        course.inst_suspended += 1
                    elif instance.status == 'SHUTOFF':
                        course.inst_shutdown += 1
                if lab.instances > 0:
                    course.labs_active += 1
                    labs_active += 1
                labs_total += 1

            courses.append(course)

        system_status = {'courses': courses, 'labs_active': labs_active, 'labs_total':
                         labs_total, 'inst_total': inst_total, 'inst_active': inst_active}
        return system_status

    @staticmethod
    def get_for_student():
        lab_m = LabManager(session=current_user.session)
        course_m = CourseManager(session=current_user.session)
        instance_m = InstanceManager(session=current_user.session)

        courses = course_m.list_my_courses()
        instances = instance_m.list_my_instances()

        for course in courses:
            course.labs = lab_m.list(domain=course)
            course.qty_active = 0
            course.qty_suspended = 0
            course.qty_shutoff = 0
            course.qty_error = 0

            for lab in course.labs:
                lab.instances = []
                for instance in instances:
                    instance_parent = instance.name.rsplit('|', 1)[0]
                    if instance_parent == lab.name:
                        lab.instances.append(instance)

                course.qty_active += len([i for i in lab.instances if i.status == 'ACTIVE'])
                course.qty_suspended += len([i for i in lab.instances if i.status == 'SUSPENDED'])
                course.qty_shutoff += len([i for i in lab.instances if i.status == 'SHUTOFF'])
                course.qty_error += len([i for i in lab.instances if i.status == 'ERROR'])

        student_info = {'courses': courses}
        return student_info



