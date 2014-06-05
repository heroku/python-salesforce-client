import operator
from betamax import Betamax
from salesforce.rest.base import SalesforceRestClientBase

cassette_name = 'rest.base'
client_class = SalesforceRestClientBase


def test_versions(client):
    versions = client.versions()
    assert isinstance(versions, list)

    keys = reduce(operator.or_, [set(v.keys()) for v in versions])
    assert keys == {'label', 'url', 'version'}
