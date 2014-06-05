# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import pytest

from salesforce.rest.v29 import SalesforceRestClient
from salesforce.metadata import SalesforceMetadataClient
from salesforce.rest.exceptions import InvalidCallException

client_class = SalesforceRestClient
metadata_client_class = SalesforceMetadataClient

def test_resources(client):
    resources = client.resources()
    assert isinstance(resources, dict)
    for k,v in resources.items():
        if k in ('identity',):
            continue

        assert v == '/services/data/v{0}/{1}'.format(client.version, k)

def test_limits(client):
    with pytest.raises(InvalidCallException):
        client.limits()

def test_objects(client, object_name):
    objects = client.objects()
    assert object_name in [o['name'] for o in objects['sobjects']]

def test_object(client, object_name):
    obj = client.object(object_name)
    assert obj['name'] == object_name
    assert 'fields' not in obj

def test_object_full_description(client, object_name, external_id_field):
    obj = client.object(object_name, full_description=True)
    assert obj['name'] == object_name

    field_names = [f['name'] for f in obj['fields']]
    assert external_id_field in field_names

def test_get_deleted(client, object_name, deleted_object_id, datetime_range):
    deleted = client.get_deleted(object_name, *datetime_range)
    deleted_object_ids = set([d['id'] for d in deleted['deletedRecords']])
    assert deleted_object_ids == set([deleted_object_id])

def test_get_updated(client, object_name, updated_object_id, datetime_range):
    updated = client.get_updated(object_name, *datetime_range)
    assert set(updated['ids']) == set([updated_object_id])

def test_get(client, object_name, object_id):
    instance = client.get(object_name, object_id)
    assert instance['Id'] == object_id
    assert 'Name' in instance

def test_get_fields(client, object_name, object_id, external_id_field):
    instance = client.get(object_name, object_id, fields=[external_id_field,])
    assert 'Name' not in instance
    assert external_id_field in instance

def test_delete(client, object_name, object_id):
    client.delete(object_name, object_id)
    with pytest.raises(InvalidCallException):
        client.get(object_name, object_id)

def test_create(client, object_name):
    name = 'Test Create Name'
    object_id = client.create(object_name, {'Name': name})['id']
    assert name == client.get(object_name, object_id)['Name']

def test_update(client, object_name, object_id):
    new_name = 'Test Update Name'
    client.update(object_name, object_id, {'Name': new_name})
    assert new_name == client.get(object_name, object_id)['Name']

def test_get_external(client, object_name, external_id_field, external_id):
    instance = client.get_external(object_name, external_id_field, external_id)
    assert instance[external_id_field] == external_id
    assert 'Name' in instance

def test_get_external_fields(client, object_name, external_id_field,
        external_id):
    instance = client.get_external(object_name, external_id_field, external_id,
                                   fields=[external_id_field])
    assert external_id_field in instance
    assert 'Name' not in instance

def test_delete_external(client, object_name, external_id_field, external_id):
    client.delete_external(object_name, external_id_field, external_id)
    with pytest.raises(InvalidCallException):
        client.get_external(object_name, external_id_field, external_id)

def test_upsert_external_insert(client, object_name, external_id_field):
    new_name = 'Test External Upsert (Insert) Name'
    external_id = 'upsert_external_insert'
    object_id = client.upsert_external(object_name, external_id_field,
                                       external_id, {'Name': new_name})['id']
    assert object_id == client.get_external(object_name, external_id_field,
                                            external_id)['Id']

def test_upsert_external_update(client, object_name, external_id_field,
        external_id):
    new_name = 'Test External Upsert (Update) Name'
    client.upsert_external(object_name, external_id_field, external_id,
                           {'Name': new_name})
    assert new_name == client.get_external(object_name, external_id_field,
                                            external_id)['Name']

def test_query(client, object_name, object_id):
    soql = "SELECT Id FROM {0} WHERE Id = '{1}'".format(object_name, object_id)
    assert client.query(soql)['records'][0]['Id'] == object_id

def test_query_deleted(client, object_name, deleted_object_id):
    soql = "SELECT Id FROM {0} WHERE Id = '{1}'".format(object_name,
                                                        deleted_object_id)
    assert len(client.query(soql)['records']) == 0

def test_query_all_deleted(client, object_name, deleted_object_id):
    soql = "SELECT Id FROM {0} WHERE Id = '{1}'".format(object_name,
                                                        deleted_object_id)
    results = client.query(soql, include_all=True)['records']
    assert results[0]['Id'] == deleted_object_id
