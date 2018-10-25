
Web server Installation
=======================

.. contents::
    :local:

This guide will setup the necessary dependencies and services required to run the ReSeLa+ web
application. Either install the web application manually or with docker. With docker,
the web application will run isolated in a container. This is the recommended setup when installing
ReSeLa+ directly on the controller as the container will not conflict with the OpenStack
installation. If you choose the manual install it is recommended to run ReSeLa+ on either a
dedicated server or a virtual machine.

Environment
-----------
ReSeLa+ is developed in python3 for ubuntu 16.04 and requires Apache2, postfix and MySQL to run.
Before beginning the installation of ReSeLa+ you need to download the ReSeLa+ repository and setup
MySQL.

Downloading ReSeLa+
~~~~~~~~~~~~~~~~~~~
To download ReSeLa+ either visit our https://github.com/kafedra-bit/resela-plus and download the
zipfile or download the repository directly with git

.. code-block:: sh

    $ git clone -b production https://github.com/kafedra-bit/resela-plus.git

To download the latest (unstable) version use

.. code-block:: sh

    $ git clone https://github.com/kafedra-bit/resela-plus.git


MySQL setup
~~~~~~~~~~~
Resela requires a MySQL database to store data. Because OpenStack already has an installed MariaDB
it is recommended to use it for ReSeLa+ as well. However any MySQL database will work. To use the
database installed by OpenStack you need to configure it to allow connections from the internet.

Edit the mysql config file ``/etc/mysql/mariadb.conf.d/50-server.cnf`` and change the bind-address
to the controller address.

.. code-block:: ini
    :caption: /etc/mysql/mariadb.conf.d/50-server.cnf

    bind-address = 10.0.2.11

After you have edited the config file it's neccessary to restart the mysql service

.. code-block:: sh

    $ sudo service mysql restart

You also need a MySQL user for ReSeLa+. First connect to the MySQL database

.. code-block:: sh

    $ sudo mysql

Then create the database and add the ReSeLa+ user

.. code-block:: sql
   :linenos:

    CREATE DATABASE IF NOT EXISTS resela;
    CREATE USER 'resela'@'%' IDENTIFIED BY '<DATABASE_PASSWORD>';
    GRANT ALL PRIVILEGES ON resela.* TO 'resela'@'%';

Docker Container (recommended)
------------------------------

.. warning::

    Choose **one** install, i.e either Docker or manual

.. warning::

    Docker is installed automaticly by the script if not already installed, if you need to install
    docker manually follow the official instructions, https://docs.docker.com/engine/installation/linux/ubuntu/

reCAPTCHA
~~~~~~~~~
In order to be able to login and use ReSeLa you will have to register a captcha with Google.
This is done by going to https://www.google.com/recaptcha/intro/invisible.html
Once here navigate to **Get reCAPTCHA**. Make sure you select **reCAPTCHA V2**, enter your domain
and follow the instructions. Once completed you will get one public key and one secret key which
you need to paste into the ``application.ini``.

Config ReSeLa+
~~~~~~~~~~~~~~
Navigate to the ReSeLa+ repository that was downloaded in the earlier stage.
To build the docker container we first need to configure the ReSeLa+ configuration file.
The config file is located at ``install/application.ini``.
Modify the following parameters to match your environment

.. code-block:: ini
    :linenos:
    :caption: application.ini
    :name: docker-config

    [flask]
    secret_key = <RANDOM_STRING>
    security_password_salt = <RANDOM_STRING>

    [database]
    name = resela
    host = 10.0.2.11
    user = resela
    pass = <DATABASE_PASSWORD>

    [resela]
    domain = http://lviv.resela.eu

    [pru]
    user = no-reply@lviv.resela.eu
    pass = <PRU_PASSWORD>

    [captcha]
    captcha_secret_key = <SECRET_KEY>
    captcha_public_key = <PUBLIC_KEY>

    [mikrotik]
    pass = <MIKROTIK_PASSWORD>

.. note::

    Remember to **uncomment**, i.e. removing the semicolons at the start of each line, when
    modifying the config file.

Build the Container
~~~~~~~~~~~~~~~~~~~
Before we can build the container we need to verify that the dockerfile has the correct
variables. This is done by editing the file ``install/Docker/Prod-env/Dockerfile``. Verify that
webhost, controller and mikrotik ip is correct.
Now it is time to build the docker container. Simply run the setup script as root

.. code-block:: sh

    $ sudo ./install/setupDocker.sh

This will take some time as docker builds the container and installs all requirements. When the
build is complete you can start the container service with the start script

.. code-block:: sh

    $ sudo ./install/Docker/start.sh

.. note::

    If you get an error that port 80 is already in use, it might be apache. Edit
    ``/etc/apache2/ports.conf`` and comment out both ``Listen 80`` and ``Listen 443``.
    Then restart apache2 to unbind the ports

    .. code-block:: ini
        :caption: /etc/apache2/ports.conf

        # Listen 80
        # Listen 443

    .. code-block:: sh

        $ sudo service apache2 restart

.. note::

    To list the running docker containers use the command

    .. code-block:: sh

        $ sudo docker ps

.. note::

    To enter a running docker service container use the command

    .. code-block:: sh

        $ sudo docker exec -ti <ID> /bin/bash

    where <ID> is the running containers id which can be obtained from `docker ps`

.. warning::

    If you make any changes to the docker container they **have to be commited** in order for the
    changes to be persistent. When the application is installed the script creates an docker image
    called `resela`. Any changes to the container are to be commited to that image. On the host use

    .. code-block:: sh

        $ sudo docker commit <CONTAINER_ID> resela

    This command will commit the current changes to the resela image and make them persistent.

Initialize database
~~~~~~~~~~~~~~~~~~~
Enter the container and use run.py to initialize the database

.. code-block:: sh

    $ sudo docker ps
    $ sudo docker exec -ti <ID> /bin/bash
    $ cd /var/www/resela
    $ python3 run.py -c resela/config/application.ini --fill-database

Where <ID> is the id of the container running.

HTTPS setup
~~~~~~~~~~~
Enabling https has to be done inside the docker container. First connect to the container
with ``docker ps`` and ``docker exec -ti <CONTAINER_ID> /bin/bash``. To enable HTTPS we recomment
using the automatic tool `Certbot` with *letsencrypt*. Follow their
instructions on how to install and configure HTTPS certificates on your environment.
https://letsencrypt.org/getting-started/

Next you should modify the ReSeLa+ configuration with following settings

.. code-block:: ini
    :linenos:
    :caption: /var/www/resela/resela/config/application.ini
    :name: docker-config-https

    [flask]
    session_cookie_secure = on

    [resela]
    domain = https://lviv.resela.eu

Next restart apache2 to enable https

.. code-block:: sh

    $ service apache2 restart

.. note::

    A LetsEncrypt certificate is only valid for 90 days, therefor it is recommended to setup a
    cronjob in the container that renews the certificate.

    .. code-block:: sh
        :name: cronjob-certbot

        0 0 * * * certbot renew && service apache2 reload

.. note::

    When https is configured and working remember to commit your changes.

Manual Installation
-------------------
If you do not want to install ReSeLa+ using docker there is the option to install ReSeLa+ manually.

.. warning::
    If you install ReSeLa+ manually remember that there may be conflicts with OpenStack. Therefore
    only install ReSeLa+ on a dedicated server or virtual machine.

Requirements
~~~~~~~~~~~~
First we need to install Apache2 and Postfix.

.. code-block:: sh

    $ sudo apt-get install apache2 postfix

Next we need to download the ReSeLa+ repository into our web directory.

.. code-block:: sh

    $ cd /var/www
    $ git clone http://github.com/kafedra-bit/resela-plus.git
    $ cd resela

Next we run the installation script located in the `install` folder.

Install Application
~~~~~~~~~~~~~~~~~~~

.. code-block:: sh

    $ sudo ./install/setupResela.sh


This will install all the requirements for ReSeLa+ and create the config file.

Config ReSeLa+
~~~~~~~~~~~~~~

Next we edit the
config file. Modify the following parameters to match your environment

.. code-block:: ini
    :linenos:
    :caption: application.ini
    :name: manual-config

    [database]
    name = resela
    host = 10.0.2.11
    user = resela
    pass = <PWD>

    [resela]
    domain = http://lviv.resela.eu

    [pru]
    user = no-reply@lviv.resela.eu
    pass = <PWD>

    [captcha]
    captcha_secret_key = <SECRET_KEY>
    captcha_public_key = <PUBLIC_KEY>

    [mikrotik]
    pass = <PWD>

reCAPTCHA
~~~~~~~~~
In order to be able to login and use ReSeLa you will have to register a captcha with Google.
This is done by going to https://www.google.com/recaptcha/intro/invisible.html
Once here navigate to **Get reCAPTCHA**. Make sure you select **reCAPTCHA V2**, enter your domain
and follow the instructions. Once completed you will get one public key and one secret key which
you need to paste into the ``application.ini``.

HTTPS setup
~~~~~~~~~~~
To enable HTTPS we recomment using the automatic tool `Certbot` with *letsencrypt*. Follow their
instructions on how to install and configure HTTPS certificates on your environment.
https://letsencrypt.org/getting-started/

Next you should modify the ReSeLa+ configuration with following settings

.. code-block:: ini
    :linenos:
    :caption: application.ini
    :name: manual-config-https

    [flask]
    session_cookie_secure = on

    [resela]
    domain = https://lviv.resela.eu

Initialize database
~~~~~~~~~~~~~~~~~~~
Use the following command to initialize the database.

.. code-block:: sh

    $ python3 run.py -c install/application.ini --fill-database

Restart
~~~~~~~

Next we restart the webserver to finalize the installation

.. code-block:: sh

    $ sudo service apache2 restart

Development Installation
------------------------
For development environments it's recommended to install the requirements manually and then use a
local IDE (e.g. pycharm) to run the application. To generate the configuration use the command

.. code-block:: sh

    $ python3 run-py --dump-config > resela/config/application.ini

Set the configuration according to your local development environment for MySQL and OpenStack.
Next install the requirements with

.. code-block:: sh

    $ apt-get -qq update
    $ apt-get -qy install $(cat install/apt_requirements.txt)

    $ pip3 install --upgrade pip
    $ pip3 install -r install/requirements.txt

