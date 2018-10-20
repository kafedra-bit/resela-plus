
General
=======

.. contents::
    :local:

ReSeLa+ is an application built for students and teachers at universities who study or teach
IT security. As front end it is a web interface that uses the flask framework and the back end is
based on the open source project OpenStack. The whole project is based on Python3.

The project can be split into four different parts:

    - Networking with Mikrotik
    - OpenStack installation
    - OpenStack management and configuration
    - Python3 application and web server

The following technologies are used to set up ReSeLa+:

    - Ubuntu server 16.04 LTS as operating system for the nodes
    - Ubuntu server 16.04 LTS for the web server virtual machine
    - OpenStack version Mitaka
    - OpenStack services Glance, Keystone, Nova and Neutron
    - Python3 with the Flask framework

OpenStack is installed with the official Mitaka installation guide on openstack.org for Ubuntu.
This can be done manually or the installation scripts can be used. For a more detailed
installation guide, see the installation part.

The developer environment the project has been set up with a Mikrotik containing the operating
system Router OS 6.3.

Development environment
~~~~~~~~~~~~~~~~~~~~~~~

Use any IDE you like. Preferably an IDE with support for git. If you do not have a
favorite editor *PyCharm* works very well. It has multiple useful plugins.

GitLab
~~~~~~

The ReSeLa+ project can be found on the project's GitLab. To become collaborator one needs to
create an
account on
GitLab. This will be your identifier when you contribute.

Always clone the project from the branch called 'master' to be sure you have the latest version of
ReSeLa+. Before something new is added to the master branch it will be run trough some tests to
check for security flaws and make sure that the code follows the code standard. More information
about
the code standard can be found on the wiki pages.

Unit tests will be run every time a branch is pushed to GitLab. If a pipeline fails it can not be
merged with master. It is possible to run the unit tests locally by installing nose2. As a
developer you need to add a new unit test for every new function that is added to the code.

A review of the new code will be done as well by the git masters. This means a manually control
for bugs, structure and security before a merge is done. Make sure the code is well tested and
that the pipeline does not fail before making a merge request.

When branches are merged there will probably be some conflicts with the new branch. The developer
needs to resolve these and make sure everything is working properly. The branch will not be merged
if any conflicts exist.

When a merge request is made, remember to check the 'remove this branch after merge'. This will
remove the remote branch but the developers local branch will still be there.


Set up SSH
~~~~~~~~~~

To be able to interact with GitLab from your computer a SSH key is needed. This will make the
workflow more simple.

Generate the private key (linux assumed):

.. code-block:: sh

    $ ssh-keygen -t rsa


If a pass phrase is added, it needs to be entered every time a you commit. Using a pass phrase
is optional.

Copy your public key to you account on GitLab.

.. code-block:: sh

    $ less ~/.ssh/id_rsa.pub


Issues
~~~~~~

ReSeLa+ uses an agile workflow., which means that issues are created, planned and then worked on
during a set interval. The issues needs
to be small and very specific. When a bug is found or someone has a suggestion to the project, add
an issue. It is possible to take an already existing issue to work with.

All branches must be created from issues. To fetch new branches with git use:

.. code-block:: sh

    $ git fetch --all

