"""
ManagerException.py
*******************
"""

class ManagerException(Exception):
    pass


class GroupManagerCreationFail(ManagerException):
    pass


class RoleManagerCreationFail(ManagerException):
    pass


class UserManagerCreationFail(ManagerException):
    pass


class LabManagerCreationFail(ManagerException):
    pass


class LabManagerLaunchFail(ManagerException):
    pass


class CourseManagerCreationFail(ManagerException):
    pass


class FlavorManagerCreationFail(ManagerException):
    pass


class ImageManagerCreationFail(ManagerException):
    pass


class InstanceManagerCreationFail(ManagerException):
    pass


class MikrotikManagerCreationFail(ManagerException):
    pass


class InstanceManagerAnotherActiveLab(ManagerException):
    pass


class InstanceManagerTooManyActiveInstancesInLab(ManagerException):
    pass


class InstanceManagerUnknownFault(ManagerException):
    pass


class InstanceManagerParameter(ManagerException):
    pass


class InstanceManagerInstanceActive(ManagerException):
    pass


class InstanceManagerTooManyLabs(ManagerException):
    pass


class InstanceManager404(ManagerException):
    pass

