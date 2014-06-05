# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import logging
import os

from ..base import SalesforceSoapClientBase

logger = logging.getLogger(__name__)

class SalesforceSoapClient(SalesforceSoapClientBase):
    version = '29.0'
    wsdl_path = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                             'partner.wsdl'))

    @classmethod
    def login(cls, username, password, token):
        return SalesforceSoapClientBase.login(cls.wsdl_path, username, password,
                                              token)
