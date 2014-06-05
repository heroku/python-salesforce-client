# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
import os

import betamax

domain = os.environ['SF_DOMAIN'].encode()
access_token = os.environ['SF_ACCESS_TOKEN'].encode()
auth_user_id = os.environ['SF_USER_ID'].encode()
org_id = access_token.split('!', 1)[0]

with betamax.Betamax.configure() as config:
    config.cassette_library_dir = 'tests/cassettes'
    config.default_cassette_options['record_mode'] = 'once'
    config.define_cassette_placeholder('__DOMAIN__', domain)
    config.define_cassette_placeholder('__ACCESS_TOKEN__', access_token)
    config.define_cassette_placeholder('__USER_ID__', auth_user_id)
    config.define_cassette_placeholder('__ORG_ID__', org_id)
