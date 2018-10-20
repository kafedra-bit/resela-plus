"""
GroupManager.py
***************
"""

from keystoneclient.v3.client import Client as KeystoneClient
from keystoneclient.v3.groups import GroupManager as OSGroupManager
from resela.backend.managers.ManagerException import GroupManagerCreationFail


class GroupManager(OSGroupManager):
    """Represents a openstack group manager"""
    def __init__(self, session=None, client=None):
        if session:
            client = KeystoneClient(session=session)
        if client:
            super().__init__(client)
        else:
            raise GroupManagerCreationFail("Neither session nor client provided")

        self._client = client
