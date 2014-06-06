# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import logging
import urlparse

logger = logging.getLogger(__name__)

try:
    import suds.client
    if suds.__version__ < '0.6':
        raise ImportError
except ImportError:
    logger.error("The metadata API requires suds-jurko >= 0.6")
    exit()

from requests import Session
from requests.adapters import BaseAdapter
from requests.auth import HTTPBasicAuth
from requests.models import Response
from suds import WebFault
from suds.client import Client
from suds.plugin import MessagePlugin
from suds.properties import Unskin
from suds.transport import Transport, TransportError, Reply


class FileAdapter(BaseAdapter):

    def send(self, request, **kwargs):
        response = Response()
        response.headers = {}
        response.encoding = 'utf-8'  # FIXME: this is a complete guess
        response.url = request.url
        response.request = request
        response.connection = self

        try:
            response.raw = open(request.url.replace('file://', ''), 'r')
        except IOError as e:
            response.status_code = 404
            return response

        response.status_code = 200
        return response

    def close(self):
        pass


class RequestsHttpTransport(Transport):

    def __init__(self, session=None, **kwargs):
        Transport.__init__(self)
        Unskin(self.options).update(kwargs)
        self.session = session or Session()
        # Suds expects support for local files URIs.
        self.session.mount('file://', FileAdapter())

    def _call(self, request, method):
        headers = dict(self.options.headers)
        headers.update(request.headers)
        if self.options.username and self.options.password:
            auth = HTTPBasicAuth(self.options.username, self.options.password)
        else:
            auth = None

        response = getattr(self.session, method)(request.url,
                                                 auth=auth,
                                                 data=request.message,
                                                 headers=headers,
                                                 timeout=self.options.timeout,
                                                 proxies=self.options.proxy,
                                                 stream=True)

        return response

    def open(self, request):
        return self._call(request, 'get').raw

    def send(self, request):
        response = self._call(request, 'post')
        return Reply(response.status_code, response.headers, response.content)


class SalesforceSoapClientBase(object):

    @property
    def version(self):
        raise NotImplementedError('Subclasses must specify a version.')

    @property
    def wsdl_path(self):
        raise NotImplementedError('Subclasses must specify a wsdl path.')

    def __init__(self, client_id, client_secret, domain, access_token,
                 refresh_token=None, token_updater=None):
        # This plugin is needed in order to keep empty complex objects from
        # getting sent in the soap paylaod.
        class PrunePlugin(MessagePlugin):

            def marshalled(self, context):
                context.envelope[1].prune()

        wsdl = 'file://{0}'.format(self.wsdl_path)
        self.client = Client(wsdl, transport=RequestsHttpTransport(),
                             plugins=[PrunePlugin()])

        self._set_session_header(access_token)

        endpoint = 'https://{0}/services/Soap/m/{1}/{2}'.format(
            domain,
            self.version,
            access_token.split('!', 1)[0],  # Salesforce org ID
        )
        self.client.set_options(location=endpoint)

        if refresh_token is not None:
            from ..rest import SalesforceRestClient
            self.rest_client = SalesforceRestClient(client_id, client_secret,
                                                    domain,
                                                    access_token=access_token,
                                                    refresh_token=refresh_token,
                                                    token_updater=token_updater)
        else:
            self.rest_client = None

    @staticmethod
    def login(wsdl_path, username, password, token):
        client = Client('file://{0}'.format(wsdl_path))
        response = client.service.login(username, password + token)
        return (
            response.sessionId,
            urlparse.urlparse(response.serverUrl).netloc,
        )

    def _set_session_header(self, access_token):
        session_header = self.client.factory.create('SessionHeader')
        session_header.sessionId = access_token
        headers = {
            'SessionHeader': session_header
        }
        self.client.set_options(soapheaders=headers)

    def _call(self, function_name, args=None, kwargs=None):
        args = args or []
        kwargs = kwargs or {}
        func = getattr(self.client.service, function_name)
        # TODO: parse response, return something actually useful
        try:
            return func(*args, **kwargs)
        except WebFault as e:
            # Detect whether the failure is due to an invalid session, and if
            # possible, try to refresh the access token.
            if (hasattr(e, 'fault') and
                    e.fault.faultcode == 'sf:INVALID_SESSION_ID' and
                    self.rest_client):
                token = self.rest_client._refresh_token()
                if token:
                    self._set_session_header(token['access_token'])
                    return func(*args, **kwargs)
            raise
