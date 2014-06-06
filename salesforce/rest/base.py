# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import logging
import os.path
import urllib
import urlparse
from xml.etree import ElementTree

import pytz
import requests
import wrapt
from requests_oauthlib import OAuth2Session

from .exceptions import (
    SalesforceRestException,
    AuthenticationMissingException,
    InvalidSessionException,
    get_exception,
)

logger = logging.getLogger(__name__)


@wrapt.decorator
def auth_required(wrapped, instance, args, kwargs):
    if getattr(instance.session, 'token', None) is None:
        raise AuthenticationMissingException()
    return wrapped(*args, **kwargs)

METHOD_STATUS_CODES = {
    'GET': (200, 300),
    'POST': (201, 204),
    'PATCH': (201, 204, 300),
    'DELETE': (200, 204),
}


class SalesforceRestClientBase(object):
    RESPONSE_FORMAT_JSON = 'json'
    RESPONSE_FORMAT_XML = 'xml'

    @property
    def version(self):
        raise NotImplementedError('Subclasses must specify a version.')

    def __init__(self, client_id, client_secret, domain, user_id=None,
                 access_token=None, refresh_token=None, token_updater=None,
                 response_format=RESPONSE_FORMAT_JSON):
        '''
        domain: The domain name of the organization's Salesforce instance (e.g.
                "na1.salesforce.com")
        '''
        self.domain = domain
        self.user_id = user_id
        self.response_format = response_format

        if access_token:
            token = {
                'access_token': access_token,
                'token_type': 'Bearer',
            }
            if refresh_token:
                token['refresh_token'] = refresh_token
                auto_refresh_url = 'https://login.salesforce.com/services/oauth2/token'
                auto_refresh_kwargs = {
                    'client_id': client_id,
                    'client_secret': client_secret,
                }
            else:
                auto_refresh_url = None
                auto_refresh_kwargs = None
            self.session = OAuth2Session(client_id, token=token,
                                         auto_refresh_url=auto_refresh_url,
                                         auto_refresh_kwargs=auto_refresh_kwargs,
                                         token_updater=token_updater)
        else:
            session = requests.Session()
        self.session.headers['Accept'] = 'application/{0}'.format(
            response_format
        )

    def _url(self, path, params=None, versioned=True):
        path_parts = ['services/data']
        if versioned:
            path_parts.append('v{0}'.format(self.version))
        path_parts.append(path)

        url = urlparse.urljoin('https://{0}'.format(self.domain),
                               os.path.join(*path_parts))

        if params:
            url += '?{0}'.format(urllib.urlencode(params))
        return url

    def _extract_response(self, response):
        error_code = error_message = content = None
        if self.response_format == SalesforceRestClientBase.RESPONSE_FORMAT_JSON:
            if response.text:
                content = response.json()

            if 400 <= response.status_code < 500:
                error = content[0]
                error_code = error['errorCode']
                error_message = error['message']
        elif self.response_format == SalesforceRestClientBase.RESPONSE_FORMAT_XML:
            # TODO: create ElementTree that supports unicode!
            content = ElementTree.fromstring(response.text.encode('utf-8'))

            if 400 <= response.status_code < 500:
                error = content.getchildren()[0]
                error_code, error_message = [e.text.decode('utf-8') for e in error]

        if response.status_code in METHOD_STATUS_CODES[response.request.method]:
            return content
        elif error_code or error_message:
            # 4xx response
            raise get_exception(response.status_code,
                                error_code,
                                error_message)
        else:
            # 5xx or unexpected response
            raise SalesforceRestException(response.status_code,
                                          response.text)

    def _format_datetime(self, value):
        return value.astimezone(pytz.utc).strftime('%Y-%m-%dT%H:%M:%S+00:00')

    def _refresh_token(self):
        if self.session.token.get('refresh_token'):
            token = self.session.refresh_token(
                self.session.auto_refresh_url,
            )
            if self.session.token_updater:
                self.session.token_updater(token)
            return token

    def _call(self, url, method='get', body=None, headers=None):
        logger.debug(url)
        response = getattr(self.session, method)(url, data=body,
                                                 headers=headers)
        try:
            return self._extract_response(response)
        except InvalidSessionException as e:
            if self._refresh_token():
                # Try again with the refreshed access token
                response = getattr(self.session, method)(url, data=body,
                                                         headers=headers)
                return self._extract_response(response)

            raise

    def call(self, path, method='get', params=None, body=None, headers=None,
             versioned=True):
        url = self._url(path, params=params, versioned=versioned)
        return self._call(url, method=method, body=body, headers=headers)

    def versions(self):
        """
        Lists summary information about each Salesforce version currently
        available, including the version, label, and a link to each version's
        root.
        """
        return self.call('', versioned=False)

    @staticmethod
    def validate_field(value, field, new_record=True):
        """
        Validates a field value against a field metadata dictionary. Note: this
        is not yet intended to be a full validation. There are sure to be
        missing validation cases. Returns a list of validation errors.
        """
        errors = []

        if new_record:
            if not field['createable'] and value is not None:
                errors.append('Cannot create this field')
        else:
            if not field['updateable'] and value is not None:
                errors.append('Cannot update this field')

        if value is not None and field.get('restrictedPicklist'):
            values = [i['value']
                      for i in field['picklistValues'] if i['active']]
            if value not in values:
                errors.append('Bad value for restricted picklist field')

        if (new_record and value is None and not field['nillable'] and
                not field['defaultedOnCreate'] and field['type'] != 'boolean'):
            errors.append('This field is required')
        return errors

    @staticmethod
    def validate_object(data, object_description, new_record=True):
        """
        Validates a dictionary of object data against an object's full
        description dictionary. Returns a 2-tuple (is_valid, errors) where
        errors is a dictionary keyed by field name.
        """
        errors = {}
        field_map = {f['name']: f for f in object_description['fields']}
        for field_name, field in field_map.items():
            field_errors = SalesforceRestClientBase.validate_field(
                data.get(field_name), field, new_record=new_record)
            if field_errors:
                errors[field_name] = field_errors

        for field_name in set(data.keys()) - set(field_map.keys()):
            errors[field_name] = ['Field name not found']
        return not errors, errors
