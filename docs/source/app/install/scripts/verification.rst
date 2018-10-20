Verification
============

.. contents::
    :local:

To verify that the OpenStack installation works properly there are a few steps to go through. It
is recommended to do these verification steps before setting up the web application since it will
be easier to  resolve any future issues.

The steps here are the same as for the official OpenStack installation guide. If you followed the
guide instead of using the installation scripts, you have probably already done this verification.

**1. Verify network configuration.** This you can do with the *ping* command. Once from all nodes,
ping all other nodes. If you get a response, everything is working otherwise there is a problem
with the network topology or the network configuration most likely.

**2. Verify Chrony service.**

On the controller node, run the command:

.. code-block:: sh

    $ sudo su
    $ chronyc sources

On all other nodes, run the command:

.. code-block:: sh

    $ sudo su
    $ chronyc sources

**2. Verify the Keystone service.** This step is only done on the controller node. If the commands
fail, check the log files and configuration files for keystone.

Unset the temporary OS_TOKEN and OS_URL environments variables (*this is done by the script but
it is safe to do again*):

.. code-block:: sh

    $ sudo su
    $ unset OS_TOKEN OS_URL

Request an authentication token for admin:

.. code-block:: sh

    $ openstack --os-auth-url http://controller:35357/v3 \
    --os-project-domain-name default --os-user-domain-name default \
    --os-project-name admin --os-username admin token issue

.. Note::

    If the hostname or ports changed in the configuration, make sure the URLs is changed to
    suit the system.

**3. Verify the Glance service.** This should be done on the controller node.

Source the admin-openrc script to gain access to admin only CLI commands:

.. code-block:: sh

    $ . admin-openrc

.. Note::

    There should be a space between . and admin-openrc.

Download a test image:

.. code-block:: sh

    $ wget http://download.cirros-cloud.net/0.3.4/cirros-0.3.4-x86_64-disk.img

Upload to OpenStack and give access to all projects:

.. code-block:: sh

    $ openstack image create "cirros" \
    --file cirros-0.3.4-x86_64-disk.img \
    --disk-format qcow2 --container-format bare \
    --public

List all images available in OpenStack:

.. code-block:: sh

    $ openstack image list

.. Note::

    Status should be set to active.

**4. Verify the Nova service.** This should be done on the controller node.

Source the admin-openrc script to gain access to admin only CLI commands:

.. code-block:: sh

    $ . admin-openrc

List the Nova services that the controller has contact with:

.. code-block:: sh

    $ openstack compute service list

.. Note::

    Make sure the host column contains all compute nodes in your network, that status is enabled
    and that the state is up. Zone should be set to Nova for compute nodes.

**5. Verify the Neutron service.** This should be done on the controller node.

Source the admin-openrc script to gain access to admin only CLI commands:

.. code-block:: sh

    $ . admin-openrc

List extentions for the successful launch of the neutron-service:

.. code-block:: sh

    $ neutron ext-list

.. Note::

    An example of this list can be found in the installation guide from OpenStack. The lists will
    most likely differ depending on Service versions and number of nodes etc.