Openstack installation
======================

.. contents::
    :local:

Here you can find documentation for the installation procedure with the provided scripts.
The whole folder should be downloaded to each machine that are going to be used.

Downloading ReSeLa+
~~~~~~~~~~~~~~~~~~~
To download ReSeLa+ either visit our `gitlab:` http://gitlab.resela.eu/resela/ and download the
zipfile or download the
repository
directly with git

.. code-block:: sh

    $ git clone -b production http://gitlab.resela.eu/resela/resela.git

To download the latest (unstable) version use

.. code-block:: sh

    $ git clone http://gitlab.resela.eu/resela/resela.git


**Relevant scripts**

- setupCompute.sh
- setupController.sh

Preparations
~~~~~~~~~~~~
The installation scripts will attempt to install OpenStack version Mitaka for Ubuntu server 16.04
LTS.
This is because Ubuntu offers support for Mitaka until 2021. Normally a fresh installation of
Ubuntu server 16.04 is optimal for the installation scripts but
it should work unless you have a previous installation of OpenStack on your machine.

The installation scripts assumes certain hostnames on your nodes. The controller's hostname
must be ``controller`` and the compute nodes must be named ``compute1``, ``compute2`` and so on.
This is because
OpenStack refers to different nodes by hostname rather than ip addresses. This will be
configured in the /etc/hosts file.

Security
~~~~~~~~
The ReSeLa+ implementation of OpenStack uses passwords. Naturally this dictates that passwords match
on the controller node and each compute node. Therefore the following table will be used (derived
from the documentation).

+----------------------+---------------------------------------------+
| Password name        | Description                                 |
+----------------------+---------------------------------------------+
| RABBIT_PASS          | Password for Rabbit message queue service   |
+----------------------+---------------------------------------------+
| KEYSTONE_PASS        | Password for Keystone database              |
+----------------------+---------------------------------------------+
| GLANCE_DBPASS        | Database password for the image service     |
+----------------------+---------------------------------------------+
| GLANCE_PASS          | Password for the service user glance        |
+----------------------+---------------------------------------------+
| NEUTRON_DBPASS       | Database password for the network service   |
+----------------------+---------------------------------------------+
| NEUTRON_PASS         | Password for the service user neutron       |
+----------------------+---------------------------------------------+
| NOVA_DBPASS          | Database password for the compute service   |
+----------------------+---------------------------------------------+
| NOVA_PASS            | Password for the service user nova          |
+----------------------+---------------------------------------------+
| MYSQL_DBPASS         | Password for the MySQL database             |
+----------------------+---------------------------------------------+
| PRU_PASS             | Password for recovering user passwords      |
+----------------------+---------------------------------------------+
| OPENSTACK_ADMIN_PASS | Password of admin user in OpenStack         |
+----------------------+---------------------------------------------+

You have to decide passwords on your own, but these are names will be used to reference each password
in the following instructions. It is recommended to use a length of minimum 10 characters and to
use both upper and lower case letters mixed with numbers and other characters (!,#,&,%...).

