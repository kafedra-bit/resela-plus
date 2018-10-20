"""
static.py
*********

This blueprint defines static pages on the website.
"""

import logging
import flask
from functools import partial

from resela.backend.managers.ErrorManager import error_handling

static = flask.Blueprint('static', __name__, url_prefix='/static')
LOG = logging.getLogger(__name__)
error_handling = partial(error_handling, log=LOG)


@static.route('/terms_of_use')
@error_handling
def tos():
    """Render a terms of use page."""

    return flask.render_template('static_pages/terms_of_use.html')


@static.route('/contact')
@error_handling
def contact():
    """Render a contact page."""

    return flask.render_template('static_pages/contact.html')