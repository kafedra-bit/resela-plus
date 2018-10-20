"""
ImageManager.py
***************
"""

from glanceclient.client import Client as GlanceClient
from glanceclient.v2.images import Controller
from resela.backend.managers.ManagerException import ImageManagerCreationFail


class ImageManager(Controller):
    """Represents a openstack image manager"""
    def __init__(self, session=None, client=None):
        if session:
            client = GlanceClient(version='2', session=session)
        if client:
            super().__init__(client.http_client, client.schemas)
        else:
            raise ImageManagerCreationFail("Neither session or client provided.")

        self._client = client
