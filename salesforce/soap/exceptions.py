# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

class SalesforceSoapException(Exception):
    def __init__(self, errors):
        self.errors = errors
        message = ', '.join(['{0}: {1}'.format(e['statusCode'],
                                               e['message']) for e in errors])
        super(SalesforceSoapException, self).__init__(message)
