"""
VersionModel.py
***************
"""

from resela.app import DATABASE


class Version(DATABASE.Model):
    """
    Database model for operating system versions.
    """

    __tablename__ = 'version'
    id = DATABASE.Column(DATABASE.Integer, autoincrement=True, primary_key=True)
    os = DATABASE.Column(DATABASE.Integer, DATABASE.ForeignKey('operating_system.id'))
    version = DATABASE.Column(DATABASE.String(50))

    def __init__(self, version=None, os=None):
        self.version = version
        self.os = os
