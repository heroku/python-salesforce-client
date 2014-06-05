# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import logging
import anyjson as json

from .base import auth_required, SalesforceRestClientBase

logger = logging.getLogger(__name__)


class SalesforceRestClient(SalesforceRestClientBase):

    """
    https://www.salesforce.com/us/developer/docs/api_rest/Content/resources_list.htm
    """
    version = '29.0'

    ### Organization attributes ####

    @auth_required
    def resources(self):
        """
        Lists available resources for the specified API version, including
        resource name and URI.
        """
        return self.call('')

    @auth_required
    def limits(self):
        "Lists information about limits in your organization."
        return self.call('limits')

    #### Objects ####

    @auth_required
    def objects(self):
        """
        Lists the available objects and their metadata for your organization's
        data.
        """
        return self.call('sobjects')

    @auth_required
    def object(self, object_name, full_description=False):
        """
        Describes the individual metadata for the specified object. If
        full_description is True, it completely describes the metadata at all
        levels.
        """
        path = 'sobjects/{0}'.format(object_name)
        if full_description:
            path += '/describe'
        obj = self.call(path)
        if not full_description:
            obj = obj['objectDescribe']
        return obj

    #### Replication ####

    @auth_required
    def get_deleted(self, object_name, start, end):
        """
        Retrieves the list of individual records that have been deleted within
        the given timespan for the specified object.
        """
        params = {
            'start': self._format_datetime(start),
            'end': self._format_datetime(end),
        }
        return self.call('sobjects/{0}/deleted'.format(object_name),
                         params=params)

    @auth_required
    def get_updated(self, object_name, start, end):
        """
        Retrieves the list of individual records that have been updated (added
        or changed) within the given timespan for the specified object.
        """
        params = {
            'start': self._format_datetime(start),
            'end': self._format_datetime(end),
        }
        return self.call('sobjects/{0}/updated'.format(object_name),
                         params=params)

    def get_recently_viewed(self, limit=None):
        """
        Gets the most recently accessed items that were viewed or referenced by
        the current user.
        """
        if limit is not None:
            params = {'limit': limit}
        else:
            params = {}
        return self.call('recent', params=params)

    #### Basic CRUD ####

    @auth_required
    def get(self, object_name, object_id, fields=None):
        """
        Retrieves a record based on the specified object_id. Optionally returns
        only the fields specified.
        """
        params = {'fields': ','.join(fields)} if fields else None
        return self.call('sobjects/{0}/{1}'.format(object_name, object_id),
                         params=params)

    @auth_required
    def get_blob(self, object_name, object_id, blob_field):
        return self.call('sobjects/{0}/{1}/{2}'.format(object_name, object_id,
                                                       blob_field))

    @auth_required
    def delete(self, object_name, object_id):
        "Deletes a record based on the specified object_id."
        return self.call('sobjects/{0}/{1}'.format(object_name, object_id),
                         method='delete')

    @auth_required
    def create(self, object_name, data):
        "Creates a new record of the specified type given a dictionary of data."
        body = json.dumps(data)
        headers = {'Content-Type': 'application/json'}
        return self.call('sobjects/{0}'.format(object_name), method='post',
                         headers=headers, body=body)

    @auth_required
    def update(self, object_name, object_id, data):
        """
        Updates a record based on the specified object_id with a dictionary of
        data.
        """
        body = json.dumps(data)
        headers = {'Content-Type': 'application/json'}
        return self.call('sobjects/{0}/{1}'.format(object_name, object_id),
                         method='patch', headers=headers, body=body)

    #### External ID CRUD ####

    @auth_required
    def get_external(self, object_name, external_id_field, external_id,
                     fields=None):
        """
        Retrieves a record based on the value of a specified external ID field.
        """
        params = {'fields': ','.join(fields)} if fields else None
        path = 'sobjects/{0}/{1}/{2}'.format(object_name, external_id_field,
                                             external_id)
        return self.call(path, params=params)

    @auth_required
    def delete_external(self, object_name, external_id_field, external_id):
        """
        Deletes a record based on the value of a specified external ID field.
        """
        path = 'sobjects/{0}/{1}/{2}'.format(object_name, external_id_field,
                                             external_id)
        return self.call(path, method='delete')

    @auth_required
    def upsert_external(self, object_name, external_id_field, external_id,
                        data):
        """
        Creates new records or updates existing records (upserts records) based
        on the value of a specified external ID field.

        * If the specified value doesn't exist, a new record is created.
        * If a record does exist with that value, the field values specified in
          the request body are updated.
        * If the value is not unique, the REST API returns a 300 response with
          the list of matching records.
        """
        body = json.dumps(data)
        headers = {'Content-Type': 'application/json'}
        path = 'sobjects/{0}/{1}/{2}'.format(object_name, external_id_field,
                                             external_id)
        return self.call(path, method='patch', headers=headers, body=body)

    #### Layouts ####

    @auth_required
    def approval_layouts(self, object_name):
        "Returns a list of approval layouts for a specified object."
        return self.call('sobjects/{0}/describe/approvalLayouts'.format(
            object_name))

    @auth_required
    def compact_layouts(self, object_name):
        "Returns a list of compact layouts for a specific object."
        return self.call('sobjects/{0}/describe/compactLayouts'.format(
            object_name))

    @auth_required
    def layouts(self, object_name=None):
        """
        Returns a list of layouts and descriptions, including for publisher
        actions.
        """
        object_name = object_name or 'global'
        return self.call('sobjects/{0}/describe/layouts'.format(object_name))

    #### Quick actions ####

    @auth_required
    def quick_actions(self, object_name=None):
        """
        Returns a list of publisher actions and details. If an object name is
        specified, returns that object's actions as well as global actions.
        """
        if object_name:
            path = 'sobjects/{0}/quickActions'.format(object_name)
        else:
            path = 'quickActions'
        return self.call(path)

    @auth_required
    def quick_action(self, object_name, action_name, full_description=False):
        "Returns a specific action for the specified object and action name."
        path = 'sobjects/{0}/quickActions/{1}'.format(object_name, action_name)
        if full_description:
            path += '/describe'
        return self.call(path)

    @auth_required
    def quick_action_default_values(self, object_name, action_name,
                                    object_id=None):
        "Returns an action's default values, including default field values."
        path = 'sobjects/{0}/quickActions/{1}/defaultValues'.format(object_name,
                                                                    action_name)
        if object_id:
            path += '/{0}'.format(object_id)
        return self.call(path)

    #### User password management ####

    @auth_required
    def get_password_info(self, user_id=None):
        "Gets information about a user password"
        user_id = user_id or self.user_id
        if not user_id:
            raise ValueError('user_id must be given or set on the instance')

        path = 'sobjects/User/{0}/password'.format(user_id)
        return self.call(path)

    @auth_required
    def set_password(self, password, user_id=None):
        "Sets a users's password"
        user_id = user_id or self.user_id
        if not user_id:
            raise ValueError('user_id must be given or set on the instance')

        path = 'sobjects/User/{0}/password'.format(user_id)
        body = json.dumps({'NewPassword': password})
        headers = {'Content-Type': 'application/json'}
        return self.call(path, method='post', headers=headers, body=body)

    @auth_required
    def reset_password(self, user_id=None):
        "Resets a user's password"
        user_id = user_id or self.user_id
        if not user_id:
            raise ValueError('user_id must be given or set on the instance')

        path = 'sobjects/User/{0}/password'.format(user_id)
        return self.call(path, method='delete')

    #### Salesforce application info ####

    @auth_required
    def app_menu(self, salesforce1=False):
        """
        Returns a list of items in either the Salesforce app drop-down menu or
        the Salesforce1 navigation menu.
        """
        path = '/appMenu/' + ('Salesforce1' if salesforce1 else 'AppSwitcher')
        return self.call(path)

    @auth_required
    def flexi_path(self, flexi_page_id):
        """
        Returns a list of Flexible Pages and their details. Information returned
        includes Flexible Page regions, the components within each region, and
        each component’s properties, as well as any associated QuickActions.
        """
        return self.call('flexiPage/{0}'.format(flexi_page_id))

    #### Queries ####

    @auth_required
    def query(self, soql, include_all=False):
        """
        Executes the specified SOQL query. If include_all is True, results can
        include deleted, merged and archived records.
        """
        path = 'queryAll' if include_all else 'query'
        return self.call(path, params={'q': soql})

    #### Search ####

    def search(self, sosl):
        "Executes the specified SOSL search."
        return self.call('search', params={'q': sosl})

    def search_scope_order(self):
        """
        Returns an ordered list of objects in the default global search scope of
        a logged-in user. Global search keeps track of which objects the user
        interacts with and how often and arranges the search results
        accordingly. Objects used most frequently appear at the top of the list.
        """
        return self.call('search/scopeOrder')

    @auth_required
    def search_result_layouts(self, object_names):
        """
        Returns search result layout information for the objects in the query
        string. For each object, this call returns the list of fields displayed
        on the search results page as columns, the number of rows displayed on
        the first page, and the label used on the search results page.
        """
        return self.call('searchlayout', params={'q': ','.join(object_names)})
