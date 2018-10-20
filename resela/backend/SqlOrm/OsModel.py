"""
OsModel.py
**********
"""

from resela.app import DATABASE


class OS(DATABASE.Model):
    """
    Database model for operating systems.
    """

    __tablename__ = 'operating_system'
    id = DATABASE.Column(DATABASE.Integer, autoincrement=True, primary_key=True)
    name = DATABASE.Column(DATABASE.String(50), unique=True)

    def __init__(self, name=None):
        self.name = name