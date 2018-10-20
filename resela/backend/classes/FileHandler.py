"""
FileHandler.py
**************

File Handler class. Used to create, modify and delete labs. Also used for starting,\
    stopping and suspending labs.
"""

import hashlib


class FileHandler:
    """ File Handler """

    @staticmethod
    def hash_file(file):
        """
        A function that calculates the MD5 hash for an entire file by reading 4096 bytes chunks and
        updating the hash function.

        :param file: The file that the hash and size will be calculated for.
        :type file: str

        :return: Returns the hash of the entire file, MD5, and the file size in bytes as well.
        """

        file_size = 0
        hash_md5 = hashlib.md5()
        for chunk in iter(lambda: file.read(4096), b""):
            hash_md5.update(chunk)
            file_size += 4096

        return hash_md5.hexdigest(), file_size

    @staticmethod
    def allowed_file(filename):
        """
        Checks for allowed extensions.

        :param filename: FIlename to check
        :return: file ending if it is in ALLOWED_EXTENSIONS
        """

        allowed_extentions = (None, 'ami', 'ari', 'aki', 'vhd',
                              'vmdk', 'raw', 'qcow2', 'vdi', 'iso', 'img')

        return '.' in filename and filename.rsplit('.', 1)[1] in allowed_extentions
