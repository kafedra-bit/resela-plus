"""
DefaultOS.py
************
"""

from resela.app import DATABASE
from resela.backend.SqlOrm.OsModel import OS
from resela.backend.SqlOrm.VersionModel import Version


def fill_database_default():
    """
    This function fills the database tables for operating systems and version with some
    default values that one could use.
    """

    os_list = [
        'Windows',
        'Ubuntu',
        'Fedora',
        'Kali Linux',
        'OpenBSD',
        'Linux Mint',
        'Debian',
        'Other'
    ]

    version_list = [
        ['XP', 'Vista', '7', '8/8.1', '10'],
        ['16.04 LTS', '14.04 LTS', '12.04 LTS'],
        ['25', '24'],
        ['2.0', '1.0'],
        ['6.0', '5.9', '5.8', '5.7'],
        ['18', '17'],
        ['8', '7', '6']
    ]

    other = 'Other'

    for os in os_list:
        DATABASE.session.add(OS(os))
    DATABASE.session.commit()

    for os_index in range(0, len(os_list) - 1):
        for version in version_list[os_index]:
            DATABASE.session.add(Version(version, os_index + 1))
        DATABASE.session.add(Version(other, os_index + 1))
    DATABASE.session.commit()