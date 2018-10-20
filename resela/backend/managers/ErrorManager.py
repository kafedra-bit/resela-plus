import logging
from functools import wraps, partial

from flask import render_template, jsonify, abort
from jinja2.exceptions import TemplateError
from keystoneauth1.exceptions.base import ClientException as ksc_exception
from keystoneauth1.exceptions.http import NotFound, Conflict, Forbidden
from novaclient.exceptions import ClientException as nc_exception

from resela.backend.managers.ManagerException import ManagerException


def error_page(error):
    """
    Error handler.
    :param error: Error message.
    :return:
    """

    return render_template('static_pages/error.html', error=error), error.code


class BossException(BaseException):
    """
    Base class of `GeneralSpecificException` and `APISpecificException` that
    implements a default `handle` function.
    """

    level = 'DEBUG'

    @classmethod
    def handle(cls, msg, log, respond, respond_arguments, msg_key):
        """Log and respond to a caught exception.

        :param msg: Message to be logged and passed as feedback.
        :type msg: `str`
        :param log: Logger to be used for logging.
        :type log: `logging.Logger`
        :param respond: Function to be call as response to the error.
        :type respond: `function`
        :param respond_arguments: Arguments to be passed to `respond`.
        :type respond_arguments: `dict`
        :param msg_key: Key (argument) that maps `msg`.
        :type msg_key: `str`

        :return: Whatever is returned by `respond`.
        """

        respond_arguments[msg_key] = msg

        if cls.level == 'ERROR_TRACE':
            log.exception(msg)
        elif cls.level in ('CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTSET'):
            log.log(msg=msg, level=getattr(logging, cls.level))
        else:
            log.exception('(Bad log level) %s' % msg)

        return respond(**respond_arguments)


class GeneralSpecificException(BossException):
    """
    Base class of special exceptions that are handled if the wrapped function
    is a general function (not an API function).
    """
    pass


class APISpecificException(BossException):
    """
    Base class of special exceptions that are handled if the wrapped function
    is an API function (not a general function).
    """
    pass


def error_handling(func, log, api_call=False):
    """Wrap a function around a general error handler.

    :param func: Function to be wrapped.
    :type func: `function`
    :param log: Logger to be used for reporting errors.
    :type log: `logging.Logger`
    :param api_call: Boolean indicating whether or not the handled function \
        is an API function.
    :type api_call: `bool`
    :return: A general error handler-wrapped function.
    :rtype: `function`
    """

    if api_call:
        respond = partial(jsonify, success=False)
        specific_exceptions = (APISpecificException,)
        msg_key = 'feedback'
    else:
        respond = partial(abort, 500)
        specific_exceptions = (GeneralSpecificException,)
        msg_key = 'description'

    respond_arguments = {}

    @wraps(func)
    def wrapped(*args, **kwargs):
        """Run a function in try-environment that excepts broad errors.

        To except a specific exception, make an if-case under the `except`
        block for `specific_exception`:

        ```
        if type(e).__name__ == 'KeyError' and api_call:
            msg = 'Required input parameter not provided.'
            respond_arguments[msg_key] = msg
            log.exception(msg)
            return respond(**respond_arguments)
        ```

        Note that you must add the exception in `specific_exception`, otherwise
        that `except` won't trigger.

        :param args: Arguments to be passed to the wrapped function.
        :param kwargs: Keyword arguments to be passed to the wrapped function.
        :return: Whatever is returned by the wrapped function.
        """

        try:
            return func(*args, **kwargs)
        except ManagerException as error:
            msg = 'Error in manager creation'
            respond_arguments[msg_key] = msg
            log.exception(msg)
            return respond(**respond_arguments)
        except TemplateError as error:
            msg = 'Error in template rendering'
            respond_arguments[msg_key] = msg
            log.exception(msg)
            return respond(**respond_arguments)

        except Forbidden as error:
            msg = 'Forbidden.'
            respond_arguments[msg_key] = msg
            log.debug(msg, exc_info=True)
            if not api_call:
                abort(403)
            return respond(**respond_arguments)
        except NotFound as error:
            msg = 'Page not found.'
            respond_arguments[msg_key] = msg
            log.debug(msg, exc_info=True)
            if not api_call:
                abort(404)
            return respond(**respond_arguments)
        except Conflict as error:
            msg = 'Duplicate entry.'
            respond_arguments[msg_key] = msg
            log.debug(msg, exc_info=True)
            if not api_call:
                abort(409)
            return respond(**respond_arguments)
        except (ksc_exception, nc_exception) as error:
            msg = 'Unsuccessful OpenStack call.'
            respond_arguments[msg_key] = msg
            log.exception(msg)
            return respond(**respond_arguments)
        except specific_exceptions as error:
            return error.handle(str(error), log, respond, respond_arguments, msg_key)
        except Exception as error:
            msg = 'Unexpected error.'
            respond_arguments[msg_key] = msg
            log.exception(msg)
            return respond(**respond_arguments)

    return wrapped


# Custom exceptions
###############################################################################

# To use a logging level other than that set in `BossException`, declare a
# class variable named `level` and set the level accordingly.

class ExceedsUploadLimit(APISpecificException):
    pass

class MD5Match(APISpecificException):
    pass

class DefaultNotAuthorized(APISpecificException):
    pass

class ImageIsUsed(APISpecificException):
    pass

class UnpermittedLabName(APISpecificException):
    pass

class NoBaseImage(APISpecificException):
    pass

class NoInstanceFound(APISpecificException):
    pass

class InstanceExists(APISpecificException):
    pass

class NoVNCLink(APISpecificException):
    pass