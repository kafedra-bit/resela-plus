
Front end
=========

.. contents::
    :local:

This is a description of the structure for the front end.


HTML
~~~~

Templates for the web application can be found in the 'resela/templates' folder. The templates
are structured after actions to make it easier to navigate.

All basic templates should include the *layout.html*. That includes everything needed to have a
working web site including all javascript and css.

.. code-block:: html

    {% extends "layout.html" %}
    {% block content %}
        <!-- Add HTML code here -->
    {% endblock %}

Contents of the templates are specified by which user is looking at the page. What a users sees
are decided from what roles the user has. If a user is an administrator he or she can see very
much information while a student only can see his or her courses and labs.

Javascript
~~~~~~~~~~

Javascript specific for the html pages are placed in the template inside a javascript block:

.. code-block:: html

    {% block javascripts %}
        # javascript code
    {% endblock%}

Javascript used on multiple web pages and javascript from third party plugins are placed in the
'resela/static/js' folder.


CSS
~~~~~~~~

To style the web site the open source project Bootstrap version 4 is used. This is to make sure the
site is
user friendly and dynamic. To style pages the default Bootstrap classes should be used.

If something extra needs to be adjusted it should be added in that html page between a new
stylesheet block. The new block should be placed under the include of *layout.html* but before
the start of the content block.

.. code-block:: html

    {% block stylesheets %}
        .new_class{ <attributes> }
    {% endblock %}

.. note::

    Read more about Bootstrap here: http://getbootstrap.com/


Icons
~~~~~

The icons used on in the web application comes from the open source project Font Awesome. The
project makes it possible to import good quality icons for a web site for free. They are scalable
as well and it is simple to customize the size of the icon.

.. note::

    Read more about Font Awesome here: http://fontawesome.io/


Python
~~~~~~

In the 'resela/blueprints' folder all functions are collected that communicates with the user.
That is where input parameters are handled and where responses to the user are sent back. The
file names are very describing to what kind of functions they contain but here are a little
description anyway.

The Flask web framework is used to generate and handle the access with the login sessions and
such. This open source project makes web development much easier and manageble.

.. note::

    Read more about Flask web framework here: http://flask.pocoo.org/

**account.py**

Contains functions that has to do with the users account. Log in and log out functions are placed
here as well as functions to reset a user's password. This are routes that you do not need to be
logged in to view.

**api.py**

Contains all routes that at logged in user can access. All pages that are rendered from this file
requires
the user to be logged in. This page responds with user feedback and makes redirects depending on
action.

**admin.py**

This file contains routes that are unique for the admin. For example, only an admin can add or
remove users from the system and list teachers and students. Admin also has privileged access in
the image library.

**default.py**

This serves as the main route-file, or controller, for the flask application.
It also imports the blueprints and handles some of the general routes.

**edit.py**

This file contains all the operations that modifies a project or a group in OpenStack,
such as create,save and edit labs and courses.

**static.py**

These functions renders pages that are accessible to all users, logged in or not. This is for
terms of use or contact pages. They do not rely on any backend functionality either.