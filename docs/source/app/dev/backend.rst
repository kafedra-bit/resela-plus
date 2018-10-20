Back end
========

.. contents::
    :local:

The ReSeLa+ back end is where the application and OpenStack communicates. OpenStack is built
with classes that handles the domains, projects and groups. These classes are inherited into
managers that are specific for ReSeLa+ but a lot of the original functions are used as well.

All back end functionality is placed in the 'resela/backend' folder. The managers are in the
managers folder and the SqlOrm folder contains the structure for the image library, VLANs and
user properties among other things.

ReSeLa+ uses the domains, groups and projects that OpenStack offers but are given different names
. The table below describes the name differences.


OpenStack layout in ReSeLa+
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. image:: ReSeLa-OpenStackLayout.png
   :scale: 50%

The bold names in the picture represent OpenStack components and the names
underneath are the ReSeLa+ translation. They can be named by application users.

The green arrows are access that a user has directly when assigned to a group in that domain. All
users are added to the default domain upon registration and can then be assigned to other
domains as well, for example when new courses are created. When assigned to a course, both
students and teachers are able to access the projects in that domain.

The orange dashed arrows are assigned privileges. An admin has to assign teachers in order for
them to be able to edit the course. Students can be added to a course by both admin and assigned
teachers.

In the table below are the short version of the translation used in the code:

+-----------------+----------------+
| **OpenStack**   | **ReSeLa+**    |
+-----------------+----------------+
| Domain          | Course         |
+-----------------+----------------+
| Project         | Labs           |
+-----------------+----------------+
| Group           | Group          |
+-----------------+----------------+


Domain
~~~~~~

When installing ReSeLa+ there are some domains that are created as default because they are
needed to get started.

**Default**

This domain contains all users that are added in OpenStack. This is to be able to access them and
add them as collaborators in other projects and domains. This is the only course that the admin
is in, otherwise admin is not a member of any other courses. Admin does have access to the
domains controlling the image library and snapshots and is able to create/edit/delete any course
in the system.

**Snapshot Factory**

There needs to be
one domain for the snapshot factory to be able to create new images from the web interface. This
domain will handle all the created snapshots.

**Image Library**

This domain contains all images that are uploaded to ReSeLa+. All users have access to the image
Library domain to be able to launch instances, download, upload and modify images depending on
what access they have in the system.

Projects
~~~~~~~~

Some default projects are also required to make the application work properly.

**Image library | Default**

Only admins can upload images to this project. These are accessible by teachers but teachers
can not upload new images.

**Image library | Snapshots**

The snapshot factory is accessible to admin and teachers. This allows those users to create
snapshots in the web application based on existing images in the Image Library.

**Image library | Images**

This project contains all images that are added to the system. Both admin and teachers can upload
and download images from this project.


Group
~~~~~

During installation some groups are installed. Theses are *students*, *teachers* and *admin*.
These are required for ReSeLa+ to work properly. A user can not be in more than one group out of
*admin*, *teachers* and *students* groups if using the application as intended. It is possible to
add a user to another group directly on the controller node.

**Admin**

Admin are in the *admin* group alone. No other user can be added to this group from the
application. To create more admins the user needs to be added to the *admin* group directly on
the controller node.

**Teachers**

All users that are added from the application as teachers will be added to this group in OpenStack.

**Students**

All users that are added from the application as students will be added to this group in OpenStack

For every new course or domain two groups are created. One of the groups are for students and one
of the groups are for teachers in the course. This is to keep them separated from each other
since they have different access within the system.


Security Groups
~~~~~~~~~~~~~~~

Security Groups are rules set for specific projects in OpenStack. All labs has Security Groups
that controls if they are allowed internet access or not for example. This is also created when a
Snapshot is created in the application.

Networks
~~~~~~~~

In ReSeLa+, networks are handled as resources. A user does not have a network as it is created.
Instead, as an user allocates resources for an instances in a lab it will also allocate a network
if there is no network connected to that lab already.

As a user starts a lab for the very first time and there are no instances started in that lab, then
a request to OpenStack is made and create an OpenStack network and subnet. With that information
the network is then created as a VLAN in the MikroTik and database. The VPN is then redirected to that
network. This makes it possible to use the same account for all labs.

If a user decides to put a lab on hold and suspend or shutoff all instances in that lab. Then as a
user starts another lab, then the VLAN is still on record in the database, but replaced in the MikroTik
and OpenStack.

When a lab is finished or removed, the MikroTik is cleaned from that VLAN and so is OpenStack.
In the database, the connection between a VLAN and a lab is removed and if the VLAN was the active VLAN
for the user and the VPN is set to default profile. The default profile does not allow connection to any
VLAN. In the database, the active VLAN is set to none, with other words, no VLAN is connected to the VPN.
When a user starts or resume an instance, the active VLAN and VPN is changed to connect to that VLAN.

As a course, lab or user is removed from ReSeLa+, all networks that is part of the object are
removed and database is updated. If all users were removed, all networks would be removed as well.

**VLANs**

VLANs are divided up one VLAN per lab. This is mainly to keep every lab as separated as possible. In this
way, each network can be seen as a resource rather than a part of a user. A user can at most allocate
3 VLANs as that is the maximum limit of started labs that can be active at the same time. Snapshot factory
is also seen as a lab and therefore allocates one of the maximum three VLANs.

**VNC**

Virtual Network Computing or VNC is the system currently used to remote control instances without connecting
via VPN and then SSH to a device. When a user press VNC a URL is created which creates a browser tab where
the input is sent to the virtual machine and the screen output is then shown in the browser. Using VNC is
quite a lot more secure when working with labs containing malicious code such as worms, compared to connecting
via VPN to that network.

**VPN**

Even if it's possible to use VNC to do labs, it might cause delay because of the protocol not being as fast
as SSH. Therefore it was made possible for a user to connect directly to the same VLAN as the virtual
machines. Once on the same network an SSH connection can be made to connect and work with the instance.
The VPN connection is encrypted using AES-128-CBC and uses MSCHAP2, MSCHAP1 or CHAP for the handshake
procedure.

