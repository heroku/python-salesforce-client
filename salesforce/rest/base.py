# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import logging
import os.path
import urllib
import urlparse
from xml.etree import ElementTree

import requests
import wrapt
import pytz

from .exceptions import (
    SalesforceRestException,
    AuthenticationMissingException,
    InvalidCallException,
)

logger = logging.getLogger(__name__)

@wrapt.decorator
def auth_required(wrapped, instance, args, kwargs):
    if instance.access_token is None:
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

    def __init__(self, domain, access_token=None, user_id=None,
            response_format=RESPONSE_FORMAT_JSON):
        '''
        domain: The domain name of the organization's Salesforce instance (e.g.
                "na1.salesforce.com")
        '''
        self.session = requests.session()
        self.domain = domain
        self.access_token = access_token
        self.user_id = user_id
        self.response_format = response_format

        # construct headers
        if response_format == SalesforceRestClientBase.RESPONSE_FORMAT_JSON:
            accept = 'application/json'
        elif response_format == SalesforceRestClientBase.RESPONSE_FORMAT_XML:
            accept = 'application/xml'

        self.base_headers = {'Accept': accept}
        if access_token:
            self.base_headers['Authorization'] = 'Bearer {0}'.format(access_token)

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
        if self.response_format == SalesforceRestClientBase.RESPONSE_FORMAT_JSON:
            if response.text:
                content = response.json()
            else:
                content = None

            expected_status_codes = METHOD_STATUS_CODES[response.request.method]
            if response.status_code in expected_status_codes:
                return content
            elif 400 <= response.status_code < 500:
                error = content[0]
                raise InvalidCallException(response.status_code,
                                           error['errorCode'],
                                           error['message'])
            else:
                raise SalesforceRestException(response.status_code,
                                              response.text)
        elif self.response_format == SalesforceRestClientBase.RESPONSE_FORMAT_XML:
            # TODO: create ElementTree that supports unicode!
            content = ElementTree.fromstring(response.text.encode('utf-8'))

            expected_status_codes = METHOD_STATUS_CODES[response.request.method]
            if response.status_code in expected_status_codes:
                return content
            elif 400 <= response.status_code < 500:
                error = content.getchildren()[0]
                error_code, message = [e.text.decode('utf-8') for e in error]
                raise InvalidCallException(response.status_code, error_code,
                                           message)
            else:
                raise SalesforceRestException(response.status_code,
                                              response.text)

    def _format_datetime(self, value):
        return value.astimezone(pytz.utc).strftime('%Y-%m-%dT%H:%M:%S+00:00')

    def _call(self, url, method='get', body=None, headers=None):
        full_headers = dict(headers) if headers else {}
        full_headers.update(self.base_headers)
        logger.debug(url)
        response = getattr(self.session, method)(url, data=body,
                           headers=full_headers)
        return self._extract_response(response)

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
            values = [i['value'] for i in field['picklistValues'] if i['active']]
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
