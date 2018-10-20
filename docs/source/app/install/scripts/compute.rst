Compute Nodes
=============

.. contents::
    :local:

Copy the git repository for the project as explained on the `Preparations` page to the node on which
you want to install a compute node. The script will install and configure services which are
required to run a OpenStack compute node.

These services will be installed:

 | Chrony   - Network Time Protocol
 | Nova     - Compute service
 | Neutron  - Network service

OpenStack repositories will also be enabled.

Running the script
~~~~~~~~~~~~~~~~~~

Navigate into the install folder where the *setupCompute.sh* script is with the command:

.. code-block:: sh

    $ cd resela/install

Then start the installation with:

.. code-block:: sh

    $ sudo ./setupController.sh

.. warning::

    The script must be run as root. To become root use the **sudo su** command.

The script will then be prompt the user for information about the network infrastructure and
the desired configuration. Make sure there is a plan for the structure before installation.

.. code-block:: sh

    Enter interface name of the management network: <management_interface_name>
    Enter interface name of the provider network: <provider_interface_name>
    Enter the password for rabbit: RABBIT_PASS
    Enter the password for the neutron user: NEUTRON_PASS
    Enter the password for the nova user: NOVA_PASS
    Enter the ip number for the gateway: <gateway_ip_address>
    Enter the ip number for the controller: <controller_ip_address>
    Enter the number of compute nodes: <number_of compute nodes>
    Enter the ip number for compute1: <compute1_ip_address>
    Enter the ip number for compute2: <compute2_ip_address>
    Enter the ip number for compute3: <compute3_ip_address>
    Enter the ip number for compute4: <compute4_ip_address>
    :
    Which compute node is this? [1-<number_of_compute_nodes>]: <compute_number>

.. Warning::

    <text> means that *text* is dependent on the physical environment and should be decided by the
    installer. UNEXPECTED capitalized text means that it's a reference to the previous password
    table.

.. Note::

    The <management_interface_name> and the <provider_interface_name> can be found by running
    ifconfig --all. The <compute_number> should be obvious.

.. Note::

    The example topology gives the following network configuration:

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

Add as many nodes as you need and give them each a unique IP address within the management
network range. Once done, confirm the configuration.

.. Note::
    The script will reboot your machine after configuring the network settings. This is to
    reload network settings on the machine. **Once the machine is rebooted, you need to start the
    script once more the same way as the first time, navigate to the script with:**

     .. code-block:: sh

        $ cd resela/install
        $ sudo ./setupCompute.sh

    There will be no need to enter the passwords again to continue the
    installation. The information is stored in a temporary file which is removed when the
    installation is complete.

The machine is rebooted a second time to finalize the installation.

This will be installed
~~~~~~~~~~~~~~~~~~~~~~

This list contains more information about each service or property that will be installed on the
compute node and in which order.

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

Detailed information
~~~~~~~~~~~~~~~~~~~~

The installation scripts basically follows the installation guide for OpenStack version Mitaka on
Ubuntu 14, but makes some changes to make it work for Ubuntu 16. The documentation can be found
here: https://docs.openstack.org/mitaka/install-guide-ubuntu/.

