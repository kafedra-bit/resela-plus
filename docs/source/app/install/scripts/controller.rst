Controller Node
===============

.. contents::
    :local:

Copy the git repository for the project as explained on the `Preparations` page to your Ubuntu 16.04
node on which you want to run the controller and
run it as root. The script installs and configures all required services to run
the ReSeLa+
web server.

The OpenStack services that will be installed is:

 | Keystone - Identity service
 | Glance - Image service
 | Nova - Compute service
 | Neutron - Network service

Other services that is installed and will work with OpenStack:

 | Chrony - Network Time Protocol
 | MariaDB - Database
 | PyMySQL
 | MongoDB - Database
 | Rabbit MQ - Communication between nodes
 | Memcahed - Memory object caching system
 | Apache2 - Web server

Repositories for python and OpenStack are also enabled.

Running the script
~~~~~~~~~~~~~~~~~~

Navigate into the install folder where the *setupController.sh* script can be found with the
command:

.. code-block:: sh

    $ cd resela/install

Then run:

.. code-block:: sh

     $ sudo ./setupController.sh

to install the controller node with OpenStack.

.. error::

    One of the first lines of the script is ``apt-get update && apt-get dist-upgrade``.
    This command is infamous for causing problems since it upgrades your operating system to the
    latest version.
    Consider backing up data if your installation is not fresh.

.. warning::

    The script must be run as root. To become root use the **sudo su** command.

The script will then be prompt the user for information about the network infrastructure and
the desired configuration. Make sure there is a plan for the structure before installation.

.. code-block:: sh

    Enter interface name of the management network: <management_interface_name>
    Enter interface name of the provider network: <provider_interface_name>
    Enter the password for rabbit: RABBIT_PASS
    Enter the password for the keystone database: KEYSTONE_DBPASS
    Enter the password for the glance database: GLANCE_DBPASS
    Enter the password for the glance user: GLANCE_PASS
    Enter the password for the neutron database: NEUTRON_DBPASS
    Enter the password for the neutron user: NEUTRON_PASS
    Enter the password for the nova database: NOVA_DBPASS
    Enter the password for the nova user: NOVA_PASS
    Enter the password for the mysql root user: ADMIN_DBPASS
    Enter the email for the password recovery user: <email_recovery_user>
    Enter the password for the password recovery user: <password_recovery_user>
    Enter the password for the OpenStack admin user: ADMIN_PASS
    Enter the management network (/24 network): <management_network>
    Enter the ip number for the gateway: <gateway ip address>
    Enter the ip number for the controller: <controller_ip_address>
    Enter the number of compute nodes: <number_of_compute_nodes>
    Enter the ip number for compute1: <compute1_ip_address>
    Enter the ip number for compute2: <compute2_ip_address>
    Enter the ip number for compute3: <compute3_ip_address>
    Enter the ip number for compute4: <compute4_ip_address>
    :


.. Warning::

    <text> means that *text* is dependent on the physical environment and should be decided by the
    installer. UNEXPECTED capitalized text means that it is a reference to the previous password
    table.

.. Note::

    The <management_interface_name> and the <provider_interface_name> can be found by running
    ``ifconfig -a``. The <compute_number> should be obvious.

.. Note::

    The example topology uses the following network configuration:

    +---------------------------+-------------+
    | <management_network>      | 10.0.2.0    |
    +---------------------------+-------------+
    | <gateway_ip_address>      | 10.0.2.1    |
    +---------------------------+-------------+
    | <controller_ip_address>   | 10.0.2.11   |
    +---------------------------+-------------+
    | <number_of_compute_nodes> | 4           |
    +---------------------------+-------------+
    | <compute1_ip_address>     | 10.0.2.21   |
    +---------------------------+-------------+
    | <compute2_ip_address>     | 10.0.2.22   |
    +---------------------------+-------------+
    | <compute3_ip_address>     | 10.0.2.23   |
    +---------------------------+-------------+
    | <compute4_ip_address>     | 10.0.2.24   |
    +---------------------------+-------------+

    The management network is assumed to be a /24 network. The network mask should not be entered.

Add as many nodes as desired and give them each a unique IP address within the
management network range. Once done, confirm the configuration.

.. Note::
    The script will reboot your machine after configuring the network settings. This is to
    reload network settings on the machine. **Once the machine is rebooted, you need to start the
    script once more the same way as the first time, navigate to the script with:**

     .. code-block:: sh

        $ cd resela/install
        $ sudo ./setupController.sh

    There will be no need to enter the passwords again to continue the
    installation. The information is stored in a temporary file which is removed when the
    installation is complete. How ever the password for MariaDB will be entered again to
    configure the *mysql_secure_installation*.

When MariaDB is installed, the root password needs to be entered again regarding the
*mysql_secure_installation*. Follow these instructions:

.. code-block:: sh

    Enter current password for the root user (enter for none): [ENTER]
    Change the root password [Y/n]: y
    Set root password: MYSQL_DBPASS
    Confirm root password: MYSQL_DBPASS
    Remove anonymous users [Y/n]: y
    Disallow root login remotely [Y/n]: y
    Remove test database and access to it? [Y/n]: y
    Reload privilege tables now? [Y/n]: y

The machine is rebooted a second time to finalize the installation.

Abstract service information
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The installation scripts basically follows the installation guide for OpenStack version Mitaka on
Ubuntu 14.04 LTS, but there are some changes to make it work for Ubuntu 16.04 LTS. The documentation
can be found here: https://docs.openstack.org/mitaka/install-guide-ubuntu/.

The services installed explained in more detail:

Chrony
------

Chrony is a Network Time Protocol which is used in OpenStack used to synchronize the different
services on the different nodes. If the nodes are not synchronized properly the nodes will not
work together and OpenStack will not work. Chrony should be among the first thing installed on
the nodes, both controller and compute nodes.

.. Note::
    If Mitaka is installed manually the OpenStack repository needs to be enabled:

        .. code-block:: sh

            $ apt-get install software-properties-common
            $ add-apt-repository cloud-archive:mitaka

    and update/upgrade the system:

        .. code-block:: sh

            $ apt-get update && apt-get dist-upgrade
            $ apt-get install python-openstackclient

MariaDB
-------

MariaDB is the database of choice for the OpenStack community and is also used by the ReSeLa+
project. To secure the database the *mysql_secure_script* should be run.

MongoDB
-------

MongoDB is a document database. It is mainly used for easing development and scaling and it is
open-source.

RabbitMQ
--------

Rabbit MQ is used in OpenStack for communication between the nodes. This is to coordinate
operations and status information. If another message queue service is chosen, consult the
documentation for that service and OpenStack. However, the scripts will install RabbitMQ for
ReSeLa+.

Memcached
---------

The memcached service it used to cache tokens for authentication mechanism. This service is run
on the controller node for ReSeLa.

Keystone
--------

Keystone is the identity service. Keystone handles authentication and sessions. Keystone is mounted
on apache2 with WSGI and listens on port 35357 and 5000. Port 35357 is used for administrative
access but ReSeLa+ rarely cares.

Apache
------

Apache is a web server will handle requests and is installed on the Controller node.

.. Note::

    Scripts are now created to be able to authenticate an admin with certain token. This is
    because it takes certain permissions to create domains, groups and projects in OpenStack.

Glance
------

Glance is the image service. Glance keeps track of the images you upload to OpenStack which can
then be launched and run as a VM. The glance API uses port 9292 and is NOT mounted on apache.

Nova
----

Nova is the compute service. Although no VMs run on the controller, nova must be installed for the
APIs and control of compute nodes to function. Nova on the controller distributes VMs on the
compute nodes so that VMs can run smoothly.

Neutron
-------

Neutron is the network service. Neutron handles VLANs and what is allowed to communicate with what.
Neutron has the power to assign VLANs to specific VMs or users, which is used in ReSeLa to make sure
that each user is isolated from other students. The neutron API uses port 9696.

.. Note::

    Consider opening the mentioned ports so that they are accessible from the outside. This is
    NOT necessary since the web server which will host ReSeLa is on the inside of the router
    (normally) and can access the APIs at will.

    For a developer environment where ReSeLa+ is hosted locally these ports cold be left open and
    make sure the local instance knows the IP address of the router.

Common errors
~~~~~~~~~~~~~

OpenStack is in a state of flux, being constantly updated and sometimes things stop working.
The most efficient way of solving problems is to check the logs and search on the web to find
answers for similar problems.

.. Hint::

    If error messages are displayed when verifying the OpenStack installation, check that the
    Keystone service is shut down and restart all the nodes.
