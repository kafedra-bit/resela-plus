Set up
======

.. contents::
    :local:

To set up the environment, the following is recommended as minimum requirement. One can always
customize the topology after resources but the installation and configuration will be a bit
different and can not be found in this guide.

Hardware
~~~~~~~~

For OpenStack a minimum of two nodes needs to be installed. Preferably these nodes are two
different physical machines to increase performance but can be virtual machines on one physical.
A router is also needed. Any kind of router will do but for the original development environment a
Mikrotik
router with a minimum of seven ethernet ports are used.

Documentation
~~~~~~~~~~~~~

Everything new needs to be documented. Functions are documented automatically with the docstrings.
The docstrings needs to have a certain structure which is specified in the GitLab wiki. Without
proper documentation for new or changed functions they should not be allowed to merge into the
project.

User manuals can be found in the ``docs`` folder in the repository. To build the manual, use the
Makefile:

.. code-block:: sh

    $ make html

If a new section is added to the documentation run the following command:

.. code-block:: sh

    $ make buildapi html

The built version of the documentation can be found in the ``docs/build/html`` folder. Open the
index.html in a web browser.

Testing
~~~~~~~

**Unit tests**

Unit tests are run with ``nose2`` and are very simple to write. There is a guide for the structure of
the tests on the GitLab wiki.

All unit tests should be placed in the ``test`` folder and the files should be named the same as
the file containing functions that are tested.

Install nose2:

.. code-block:: sh

    $ pip install nose2 cov-core

To run the test locally navigate to the project root folder ``resela`` and run the following command:

.. code-block:: sh

    $ nose2


**Code standard**

To test the code standard the program ``pylint`` is used. To get started make sure ``pylint`` is
installed on your machine.

Install ``pylint``:

.. code-block:: sh

    $ pip install pylint

Run the test with the following command:

.. code-block:: sh

    $ pylint --rcfile=pylint.rc resela


``resela`` represents the root folder of the project. It is possible to specify a certain folder or
file in the project by simply designate the search path.


**Security**

Security testing is done with a tool called ``bandit``. It is easy to use and can be integrated
with GitLab as well as run locally.

Install ``bandit`` on your machine:

.. code-block:: sh

    $ pip install bandit

Run ``bandit`` on your project:

.. code-block:: sh

    $ bandit -r resela

``resela`` represents the root folder of the project. It is possible to specify a certain folder or
file in the project by simply designate the search path.