# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import datetime
import re
import string
import time
import os
try:
    from urlparse import parse_qs
except ImportError:
    from urllib.parse import parse_qs

import pytest
import pytz
from betamax import Betamax, BaseMatcher
from requests.compat import urlparse
from shams import primitives

from salesforce.rest.exceptions import InvalidCallException
from ..conftest import (
    domain,
    access_token,
    auth_user_id,
    client_id,
    client_secret,
)


class SalesforceRestMatcher(BaseMatcher):
    name = 'salesforce_rest'
    excluded_query_keys = ('start', 'end')

    def to_dict(self, query):
        query_dict = parse_qs(query or '')  # Protect against None
        return dict(filter(lambda i: i[0] not in self.excluded_query_keys,
                           query_dict.items()))

    def match(self, request, recorded_request):
        request_query = self.to_dict(urlparse(request.url).query)
        recorded_query = self.to_dict(
            urlparse(recorded_request['uri']).query
        )

        return request_query == recorded_query

Betamax.register_request_matcher(SalesforceRestMatcher)

custom_object_name = primitives.capital_word(charset=string.lowercase)

with Betamax.configure() as config:
    config.define_cassette_placeholder('__CUSTOM_OBJECT_NAME__',
                                       custom_object_name)

#### Fixtures ####


@pytest.yield_fixture(scope='module')
def metadata_client(request):
    Client = getattr(request.module, "metadata_client_class")
    client = Client(domain, access_token)

    cassette_name = '.'.join((
        request.module.__name__,
        'metadata',
    ))
    matchers = [
        'method',
        'path',
        'body',
    ]
    session = client.client.options.transport.session
    session.headers['Accept-Encoding'] = ''  # don't gzip responses
    with Betamax(session).use_cassette(cassette_name, match_requests_on=matchers):
        yield client


@pytest.fixture(scope='module')
def object_name(request, metadata_client):
    label = 'Custom object'
    plural_label = 'Custom objects'
    name_field = 'Name__c'
    name_field_label = 'Custom object name'
    object_name = '{0}__c'.format(custom_object_name)
    custom_object = metadata_client.custom_object(object_name, label,
                                                  plural_label, name_field,
                                                  name_field_label)
    metadata_client.create(custom_object)

    def delete_object():
        metadata_client.delete('CustomObject', object_name)
    request.addfinalizer(delete_object)

    return object_name


@pytest.fixture(scope='module')
def external_id_field(request, metadata_client, object_name):
    field_name = 'ExternalId__c'

    custom_field = metadata_client.custom_field(object_name, field_name,
                                                'External id', external_id=True)
    metadata_client.create(custom_field)

    # Create a permission set which makes the field editable/readable
    permission_set_name = '{0}_{1}_PermissionSet'.format(
        object_name.replace('__c', ''),
        field_name.replace('__c', ''),
    )
    permission_set_label = '{0} {1} Permission Set'.format(object_name,
                                                           field_name)
    permission_set = metadata_client.field_permission_set(object_name,
                                                          field_name, permission_set_name, permission_set_label)
    response = metadata_client.create(permission_set)

    # Now assign that permission set to the user
    # HACK: We need a module-level rest client here, but our normal rest client
    # fixture is function-level. So we have to recreate the client instead of
    # using the fixture. :(
    Client = getattr(request.module, "client_class")
    client = Client(client_id, client_secret, domain, access_token=access_token,
                    user_id=auth_user_id)

    cassette_name = '.'.join((
        request.module.__name__,
        'rest_client',
    ))
    matchers = [
        'salesforce_rest',
        'method',
        'path',
        'body',
    ]
    session = client.session
    session.headers['Accept-Encoding'] = ''  # don't gzip responses
    with Betamax(session).use_cassette(cassette_name, match_requests_on=matchers):
        soql = "SELECT Id FROM PermissionSet WHERE Name = '{0}'".format(
            permission_set_name)
        permission_set_id = client.query(soql)['records'][0]['Id']
        client.create('PermissionSetAssignment', {
            'AssigneeId': auth_user_id,
            'PermissionSetId': permission_set_id,
        })

    def delete_permission_set():
        metadata_client.delete('PermissionSet', permission_set_name)
    request.addfinalizer(delete_permission_set)

    return field_name


@pytest.yield_fixture
def client(request):
    Client = getattr(request.module, "client_class")
    client = Client(client_id, client_secret, domain, access_token=access_token,
                    user_id=auth_user_id)

    cassette_name = '.'.join((
        request.module.__name__,
        request.function.__name__,
    ))
    matchers = [
        'salesforce_rest',
        'method',
        'path',
        'body',
    ]
    session = client.session
    session.headers['Accept-Encoding'] = ''  # don't gzip responses
    with Betamax(session).use_cassette(cassette_name, match_requests_on=matchers):
        yield client


@pytest.fixture
def object_id(request, client, object_name, external_id_field):
    response = client.create(object_name, {
        'Name': 'New object name',
        external_id_field: 'external_id',
    })
    object_id = response['id']

    def delete_object():
        try:
            client.delete(object_name, object_id)
        except InvalidCallException as e:
            # If the test itself deleted the object, ignore.
            if e.error_code != 'ENTITY_IS_DELETED':
                raise
    request.addfinalizer(delete_object)

    return object_id


@pytest.fixture
def external_id(client, object_name, object_id, external_id_field):
    return client.get(object_name, object_id)[external_id_field]


@pytest.fixture
def deleted_object_id(client, object_name, object_id):
    client.delete(object_name, object_id)
    return object_id


@pytest.fixture
def updated_object_id(client, object_name, object_id):
    client.update(object_name, object_id, {'Name': 'Updated object name'})
    return object_id


@pytest.fixture
def datetime_range():
    now = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
    one_minute_from_now = now + datetime.timedelta(seconds=60)
    one_minute_ago = now - datetime.timedelta(seconds=60)
    return (one_minute_ago, one_minute_from_now)
