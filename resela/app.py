"""Resela application bootstrap.

Starts and configs the flask application.
"""

import logging
import logging.config
import warnings
import flask

from configparser import ConfigParser, Error as configparser_error
from os import access, R_OK
from os.path import join, dirname, abspath, isfile
from sys import exit

from urllib.parse import quote_plus
from flask_ini import FlaskIni
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

from resela.backend.managers.ErrorManager import error_page


APP = flask.Flask(__name__)
# Disables track modifications feature in SQL Alchemy
APP.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Add a Jinja filter that encodes the url so that is safe.
APP.jinja_env.filters['url_encode'] = lambda u: quote_plus(u)

# Setup a login manager to be used by Flask-Login.
LOGIN_MANAGER = LoginManager()
LOGIN_MANAGER.init_app(APP)
# Set the login page to which one is redirected when not authenticated.
LOGIN_MANAGER.login_view = 'account.login'

# Uses to ignore the warning about not having set the URI needed by SQL
# Alchemy, this is done later in this file.
with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    DATABASE = SQLAlchemy(APP)

CONFIG_PATH = join(abspath(dirname(__file__)), 'config', 'application.ini')
COMMENT_SIGN = ';'
SHADOW_CONFIG = """
[flask]
secret_key =
security_password_salt =
debug = on
testing = off
session_cookie_httponly = on
session_cookie_secure = off
permament_session_lifetime = 3600
# smtp settings
mail_server = localhost
mail_port = 25
; mail_use_* options do not take values; their mere presence indicate "True".
;mail_use_tls # Uncomment to enable.
;mail_use_ssl # Uncomment to enable.
mail_username = no-reply@lviv.resela.eu
mail_password =
mail_debug = 0

[database]
name = resela
host = localhost
port = 3306
user = root
pass =

[resela]
domain = http://lviv.resela.eu
upload_limit = 25
allowed_extensions = ami,ari,aki,vhd,vmdk,raw,qcow2,vdi,iso,img
instance_limit = 5

[pru]
user = no-reply@lviv.resela.eu
pass =

[captcha]
captcha_secret_key =
captcha_public_key =

[mikrotik]
host = mikrotik
user = admin
pass =
port = 22

[network]
basenetwork = 10.1.0.0

[openstack]
cert_path =
keystone = http://controller:5000/v3
userhandler = http://controller:35357/v3
region = RegionOne
pwdsalt = ReSeLa

[loggers]
keys = root

[handlers]
keys = hand01

[formatters]
keys = form01

[logger_root]
handlers = hand01
level = INFO

[handler_hand01]
class = FileHandler
formatter=form01
args = ('log/resela.log', 'a')

[formatter_form01]
format = %(asctime)s %(levelname)-8s %(name)-15s: %(message)s
datefmt = %Y-%m-%d %H:%M:%S
class = logging.Formatter
"""

# NOTE: Sections that have a single option that must be checked must end with a
# comma to force the tuple type.
MANDATORY_SETTINGS = {
    'flask': ('secret_key', 'security_password_salt',),
    'database': ('pass',),
    'pru': ('pass',),
    'mikrotik': ('pass',),
    'network': ('basenetwork',),
    'captcha': ('captcha_secret_key', 'captcha_public_key',)
}


def write_default_config(dest=CONFIG_PATH):
    """Write the default configuration to an ini styled file at CONFIG_PATH.

    The options are loaded from SHADOW_CONFIG, which contains all default
    settings. Prior to writing the file, all default options are commented
    out using the COMMENT_SIGN constant, enabling a user to see which settings
    in the configuration file deviate from the default settings.

    :param dest: The path of the file to which to write the configuration.
    :type dest: str

    :raises configparser.Error: Problem using the configurations.
    :raises OSError: Problem writing the config file to `dest`.
    """

    # Special options required to read comments from SHADOW_CONFIG.
    cp_kwargs = {'allow_no_value': True, 'comment_prefixes': None}

    default_config = ConfigParser(**cp_kwargs)
    # Special option required so that the case of the comments is not changed.
    default_config.optionxform = str
    shadow_config = ConfigParser(**cp_kwargs)
    shadow_config.optionxform = default_config.optionxform
    shadow_config.read_string(SHADOW_CONFIG)

    # Copy all options and corresponding values from SHADOW_CONFIG.
    for section in shadow_config.sections():
        default_config.add_section(section)
        for option in shadow_config.options(section):
            if option.startswith(COMMENT_SIGN):
                # Do not add an extra comment sign on already commented lines.
                write_line = option
            else:
                # Comment out all assignment lines, as they are the default.
                write_line = COMMENT_SIGN + option

            default_config.set(section, write_line,
                               shadow_config.get(section, option))

    with open(dest, 'w') as configfile:
        default_config.write(configfile)


def app_init(config=None):
    """Initialize the Flask app.

    Loads options from a configuration file and registers error handlers. If
    the default configuration path is used and no file exists at that path,
    the default configuration is written there.

    :param config: The path of the config to be used by Resela.
    :type config: str
    """

    if config is not None:
        config_path = config
    else:
        config_path = CONFIG_PATH
        if not isfile(config_path):
            try:
                write_default_config()
            except (configparser_error, OSError):
                logging.exception('Unable to write the default configuration.')
                exit(1)
        if not access(config_path, R_OK):
            logging.error('Cannot read the default configuration file!',
                          config_path)
            exit(1)

    with APP.app_context():

        try:
            # Register error handlers.

            APP.errorhandler(400)(error_page)
            APP.errorhandler(401)(error_page)
            APP.errorhandler(403)(error_page)
            APP.errorhandler(404)(error_page)
            APP.errorhandler(405)(error_page)
            APP.errorhandler(409)(error_page)
            APP.errorhandler(500)(error_page)

            # Load config.

            # Set allow_no_value to support the use_mail_* options.
            APP.iniconfig = FlaskIni(allow_no_value=True,
                                     inline_comment_prefixes=(';', '#'))
            # Base the full config on SHADOW_CONFIG, so that fallback values
            # need not be specified throughout the code.
            APP.iniconfig.read_string(SHADOW_CONFIG)
            # Overwrite those settings that are specified in the config file.
            APP.iniconfig.read(config_path)

            #  Initialize the root logger.
            #
            # Doing this before checking the mandatory options is ok; if the
            # logging options are not set, it uses the default (stderr). If
            # they are set, the error messages end up in the specified
            # location.
            #
            # `disable_existing_loggers` is set to `False` so that the module
            # specific loggers (`LOG`s) already created remain enabled.

            logging.config.fileConfig(APP.iniconfig,
                                      disable_existing_loggers=False)

            # Check mandatory options.

            all_mandatory_options_set = True
            for section, options in MANDATORY_SETTINGS.items():
                for option in options:
                    if not APP.iniconfig.get(section, option):
                        all_mandatory_options_set = False
                        logging.error('Mandatory option not set in config '
                                      'file -- [%s]: %s' % (section, option))

            # Flask allows only one of the mail_use_* options to be set at the
            # same time. When set, the value retrieved is `None`.
            both_tls_and_ssl_set = False
            mail_tls_set = APP.iniconfig.get('flask', 'mail_use_tls',
                                             fallback='NOTSET') is None
            mail_ssl_set = APP.iniconfig.get('flask', 'mail_use_ssl',
                                             fallback='NOTSET') is None

            if mail_tls_set and mail_ssl_set:
                both_tls_and_ssl_set = True
                logging.error("[flask]:MAIL_USE_TLS and [flask]:MAIL_USE_SSL "
                              "are mutually exclusive.")

        except configparser_error:
            logging.exception('Problem handling the configuration.')
            exit(1)
        except OSError:
            logging.exception('Problem handling the logging file.')
            exit(1)
        except Exception:
            logging.exception('Unexpected error.')
            exit(1)
        else:
            if not all_mandatory_options_set or both_tls_and_ssl_set:
                exit(1)

        # Database
        # Creating uri that the SQL-ORM uses to access the sql database
        APP.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://' + \
                                                APP.iniconfig.get('database', 'user') + \
                                                ':' + APP.iniconfig.get('database', 'pass') + \
                                                '@' + APP.iniconfig.get('database', 'host') + \
                                                ':' + APP.iniconfig.get('database', 'port') + \
                                                '/' + APP.iniconfig.get('database', 'name')


def after_this_request(f):
    if not hasattr(flask.g, 'after_request_callbacks'):
        flask.g.after_request_callbacks = []
    flask.g.after_request_callbacks.append(f)
    return f


@APP.before_request
def do_before_req():
    # Check if cookies have been accepted
    flask.g.cookies_accepted = True if 'cookies' in flask.request.cookies else False


@APP.after_request
def call_after_request_callbacks(response):

    # Check for specific callbacks
    for callback in getattr(flask.g, 'after_request_callbacks', ()):
        callback(response)
    return response
