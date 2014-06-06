# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

"""
Full list of status codes and their meanings:
https://www.salesforce.com/us/developer/docs/api_rest/Content/errorcodes.htm
"""


class SalesforceRestException(Exception):

    def __init__(self, status_code, message):
        self.status_code = status_code
        super(SalesforceRestException, self).__init__(message)


class AuthenticationMissingException(SalesforceRestException):

    def __init__(self):
        super(AuthenticationMissingException, self).__init__(None,
                                                             'An access token is required for this endpoint')


class InvalidCallException(SalesforceRestException):

    def __init__(self, status_code, error_code, message):
        self.error_code = error_code
        super(InvalidCallException, self).__init__(status_code, message)


class InvalidSessionException(InvalidCallException):
    pass


class NotFoundException(InvalidCallException):
    pass


def get_exception(status_code, error_code, error_message):
    error_code_map = {
        (401, 'INVALID_SESSION_ID'): InvalidSessionException,
        (404, 'NOT_FOUND'): NotFoundException,
    }
    klass = error_code_map.get((status_code, error_code), InvalidCallException)
    return klass(status_code, error_code, error_message)
