# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import logging
import os

from ...soap.base import SalesforceSoapClientBase
from ...soap.exceptions import SalesforceSoapException

logger = logging.getLogger(__name__)


class SalesforceMetadataClient(SalesforceSoapClientBase):
    version = '33.0'
    wsdl_path = os.path.join(os.path.dirname(__file__), 'metadata.wsdl')

    ############# Factory Helpers ############

    def _ensure_custom_name(self, name):
        if not name.endswith('__c'):
            name = '{0}__c'.format(name)
        return name

    def custom_object(self, object_name, label, plural_label, name_field,
                      name_field_label, name_field_type='Text',
                      deployment_status='Deployed', sharing_model='ReadWrite'):
        """Generate a salesforce custom object.
        This method populates all of the required fields for custom objects and
        returns a SOAP object which can be passed to CRUD methods.
        """
        object_name = self._ensure_custom_name(object_name)
        name_field = self._ensure_custom_name(name_field)
        custom_object = self.client.factory.create('CustomObject')
        custom_object.fullName = object_name
        custom_object.label = label
        custom_object.pluralLabel = plural_label
        custom_object.deploymentStatus = deployment_status
        custom_object.sharingModel = sharing_model
        custom_object.nameField.fullName = name_field
        custom_object.nameField.type = name_field_type
        custom_object.nameField.label = name_field_label

        return custom_object

    def custom_field(self, object_name, field_name, field_label,
                     field_type='Text', length=255, external_id=False):
        field_name = self._ensure_custom_name(field_name)
        name = '.'.join((object_name, field_name))
        custom_field = self.client.factory.create('CustomField')
        custom_field.fullName = name
        custom_field.label = field_label
        custom_field.type = field_type
        if field_type == 'Text' and length:
            custom_field.length = length
        custom_field.externalId = external_id

        return custom_field

    def field_permission_set(self, object_name, field_name, permission_set_name,
                             label, editable=True, readable=True):
        permission_set = self.client.factory.create('PermissionSet')
        field_permission = self.client.factory.create(
            'PermissionSetFieldPermissions')
        field_permission.field = '{0}.{1}'.format(object_name, field_name)
        field_permission.editable = editable
        field_permission.readable = readable
        permission_set.fieldPermissions.append(field_permission)
        permission_set.fullName = permission_set_name
        permission_set.label = label
        return permission_set

    ############# CRUD Methods ############

    def create_many(self, metadata_objects):
        return self._call('createMetadata', args=[metadata_objects])

    def create(self, metadata_object):
        result = self.create_many([metadata_object])[0]
        if not result.success:
            raise SalesforceSoapException(result.errors)

        return result.fullName

    def get_many(self, metadata_type, object_names):
        return self._call('readMetadata', args=[metadata_type, object_names])

    def get(self, metadata_type, object_name):
        return self.get_many(metadata_type, [object_name])

    def update_many(self, metadata_objects):
        return self._call('updateMetadata', args=[metadata_objects])

    def update(self, metadata_object):
        return self.update_many([metadata_object])

    def delete_many(self, metadata_type, object_names):
        return self._call('deleteMetadata', args=[metadata_type, object_names])

    def delete(self, metadata_type, object_name):
        return self.delete_many(metadata_type, [object_name])

    def rename(self, metadata_type, old_object_name, new_object_name):
        return self._call('renameMetadata', args=[metadata_type,
                                                  old_object_name,
                                                  new_object_name])

    def list(self, metadata_type):
        query = self.client.factory.create('ListMetadataQuery')
        query.type = metadata_type
        return self._call('listMetadata', args=[[query], self.version])
