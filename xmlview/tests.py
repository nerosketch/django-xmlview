from collections import OrderedDict

from django import http
from django.core.exceptions import PermissionDenied
from django.test.utils import override_settings
from django.views.decorators.http import require_POST
import mock
from xmltodict import parse
from django.test import TestCase, RequestFactory

from decorators import xml_view

rf = RequestFactory()
XML_TYPE = 'text/xml'


def eq_(a, b, msg=None):
    """From nose.tools.eq_."""
    assert a == b, msg or '%r != %r' % (a, b)


class JsonViewTests(TestCase):
    def test_object(self):
        data = {
            'foo': 'bar',
            'baz': 'qux',
            'quz': [{'foo': 'bar'}],
        }

        @xml_view
        def temp(_):
            return data

        res = temp(rf.get('/'))
        eq_(200, res.status_code)
        eq_(OrderedDict(data), parse(res.content.decode('utf-8')))
        eq_(XML_TYPE, res['content-type'])

    def test_404(self):
        @xml_view
        def temp(_):
            raise http.Http404('foo')

        res = temp(rf.get('/'))
        eq_(404, res.status_code)
        eq_(XML_TYPE, res['content-type'])
        data = parse(res.content.decode('utf-8'))
        eq_(404, data['error'])
        eq_('foo', data['message'])

    def test_permission(self):
        @xml_view
        def temp(_):
            raise PermissionDenied('bar')

        res = temp(rf.get('/'))
        eq_(403, res.status_code)
        eq_(XML_TYPE, res['content-type'])
        data = parse(res.content.decode('utf-8'))
        eq_(403, data['error'])
        eq_('bar', data['message'])

    def test_not_allowed(self):
        @xml_view
        @require_POST
        def temp(_):
            return {}

        res = temp(rf.get('/'))
        eq_(405, res.status_code)
        eq_(XML_TYPE, res['content-type'])
        data = parse(res.content.decode('utf-8'))
        eq_(405, data['error'])

        res = temp(rf.post('/'))
        eq_(200, res.status_code)

    @override_settings(DEBUG=True)
    def test_server_error_debug(self):
        @xml_view
        def temp(_):
            raise TypeError('fail')

        res = temp(rf.get('/'))
        eq_(500, res.status_code)
        eq_(XML_TYPE, res['content-type'])
        data = parse(res.content.decode('utf-8'))
        eq_(500, data['error'])
        eq_('fail', data['message'])
        assert 'traceback' in data

    @override_settings(DEBUG=False)
    def test_server_error_no_debug(self):
        @xml_view
        def temp(_):
            raise TypeError('fail')

        res = temp(rf.get('/'))
        eq_(500, res.status_code)
        eq_(XML_TYPE, res['content-type'])
        data = parse(res.content.decode('utf-8'))
        eq_(500, data['error'])
        eq_('An error occurred', data['message'])

    def test_http_status(self):
        @xml_view
        def temp(_):
            return {}, 402
        res = temp(rf.get('/'))
        eq_(402, res.status_code)
        eq_(XML_TYPE, res['content-type'])
        data = parse(res.content.decode('utf-8'))
        eq_({}, data)

    def test_headers(self):
        @xml_view
        def temp(_):
            return {}, 302, {'X-Foo': 'Bar'}
        res = temp(rf.get('/'))
        eq_(302, res.status_code)
        eq_(XML_TYPE, res['content-type'])
        eq_('Bar', res['X-Foo'])
        data = parse(res.content.decode('utf-8'))
        eq_({}, data)

    def test_signal_sent(self):
        from . import decorators

        @xml_view
        def temp(_):
            [][0]  # sic.

        with mock.patch.object(decorators, 'got_request_exception') as s:
            res = temp(rf.get('/'))

        assert s.send.called
        eq_(XML_TYPE, res['content-type'])

    def test_unicode_error(self):
        @xml_view
        def temp(_):
            raise http.Http404('page \xe7\xe9 not found')

        res = temp(rf.get('/\xe7\xe9'))
        eq_(404, res.status_code)
        data = parse(res.content.decode('utf-8'))
        assert '\xe7\xe9' in data['message']

    def test_override_content_type(self):
        testtype = 'application/vnd.helloworld+json'
        data = {'foo': 'bar'}

        @xml_view(content_type=testtype)
        def temp(_):
            return data

        res = temp(rf.get('/'))
        eq_(200, res.status_code)
        eq_(data, parse(res.content.decode('utf-8')))
        eq_(testtype, res['content-type'])

    def test_passthrough_response(self):
        """Allow HttpResponse objects through untouched."""
        payload = parse({'foo': 'bar'}).encode('utf-8')

        @xml_view
        def temp(_):
            return http.HttpResponse(payload, content_type='text/plain')

        res = temp(rf.get('/'))
        eq_(200, res.status_code)
        eq_(payload, res.content)
        eq_('text/plain', res['content-type'])

