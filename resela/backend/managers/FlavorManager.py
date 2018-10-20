"""
FlavorManager.py
****************
"""

from novaclient.client import Client as NovaClient
from novaclient.v2.flavors import FlavorManager as OSFlavorManager
from resela.backend.managers.ManagerException import FlavorManagerCreationFail


class FlavorManager(OSFlavorManager):
    """Represents a openstack flavor manager"""
    def __init__(self, session=None, client=None):
        if session:
            client = NovaClient(version='2', session=session)
        if client:
            super().__init__(client)
        else:
            raise FlavorManagerCreationFail("Neither session nor client provided")

        self._client = client
