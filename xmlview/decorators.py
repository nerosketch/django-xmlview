import logging
import traceback
from functools import wraps
from importlib import import_module

from django.conf import settings
from django import http
from django.core.exceptions import PermissionDenied
from django.core.handlers.base import BaseHandler
from django.core.signals import got_request_exception
from django.utils import six

VERSION = (0, 0, 1)
__version__ = '.'.join(map(str, VERSION))


XML_TYPE = getattr(settings, 'XML_DEFAULT_CONTENT_TYPE', 'text/xml')
xml_lib = import_module(getattr(settings, 'XML_MODULE', 'dicttoxml'))
logger = logging.getLogger('django.request')
ROOT_NODE = getattr(settings, 'XML_DEFAULT_ROOT_NODE', 'xml')


def _dump_xml(data, root=ROOT_NODE):
    options = {
        'custom_root': root,
        'attr_type': False
    }
    options.update(getattr(settings, 'XML_OPTIONS', {}))
    return xml_lib.dicttoxml(data, **options)


def xml_view(*args, **kwargs):
    """Ensure the response content is well-formed XML.

    Views wrapped in @xml_view can return XML-serializable Python dicts,
    and the decorator will serialize the output and set
    the correct Content-type.

    >>> @xml_view(content_type='application/xhtml+xml', root_node='xml_root_node')
        ... def example(request):
        ...     return {'foo': 'bar'}
    """

    content_type = kwargs.get('content_type', XML_TYPE)
    root_node = kwargs.get('root_node', ROOT_NODE)

    def decorator(f):
        @wraps(f)
        def _wrapped(request, *a, **kw):
            try:
                status = 200
                headers = {}
                ret = f(request, *a, **kw)

                if isinstance(ret, tuple):
                    if len(ret) == 3:
                        ret, status, headers = ret
                    else:
                        ret, status = ret

                if not isinstance(ret, dict):
                    raise TypeError('View must return a dict')

                # Some errors are not exceptions. :\
                if isinstance(ret, http.HttpResponseNotAllowed):
                    blob = _dump_xml({
                        'error': 405,
                        'message': 'HTTP method not allowed.'
                    }, root=root_node)
                    return http.HttpResponse(
                        blob, status=405, content_type=XML_TYPE)
                # Allow HttpResponses to go straight through.
                if isinstance(ret, http.HttpResponse):
                    return ret
                blob = _dump_xml(ret, root=root_node)
                response = http.HttpResponse(blob, status=status, content_type=content_type)

                for k in headers:
                    response[k] = headers[k]
                return response

            except http.Http404 as e:
                blob = _dump_xml({
                    'error': 404,
                    'message': six.text_type(e),
                }, root=root_node)
                logger.warning('Not found: %s', request.path,
                               extra={
                                   'status_code': 404,
                                   'request': request,
                               })
                return http.HttpResponseNotFound(blob, content_type=XML_TYPE)

            except PermissionDenied as e:
                logger.warning(
                    'Forbidden (Permission denied): %s', request.path,
                    extra={
                        'status_code': 403,
                        'request': request,
                    })
                blob = _dump_xml({
                    'error': 403,
                    'message': six.text_type(e),
                }, root=root_node)
                return http.HttpResponseForbidden(blob, content_type=XML_TYPE)

            except Exception as e:
                exc_data = {
                    'error': 500,
                    'message': 'An error occurred',
                }
                if settings.DEBUG:
                    exc_data['message'] = six.text_type(e)
                    exc_data['traceback'] = traceback.format_exc()

                blob = _dump_xml(exc_data, root=root_node)

                # Generate the usual 500 error email with stack trace and full
                # debugging information
                logger.error(
                    'Internal Server Error: %s', request.path,
                    exc_info=True,
                    extra={
                        'status_code': 500,
                        'request': request
                    }
                )

                # Here we lie a little bit. Because we swallow the exception,
                # the BaseHandler doesn't get to send this signal. It sets the
                # sender argument to self.__class__, in case the BaseHandler
                # is subclassed.
                got_request_exception.send(sender=BaseHandler, request=request)
                return http.HttpResponseServerError(blob, content_type=XML_TYPE)
        return _wrapped

    if len(args) == 1 and callable(args[0]):
        return decorator(args[0])
    else:
        return decorator
