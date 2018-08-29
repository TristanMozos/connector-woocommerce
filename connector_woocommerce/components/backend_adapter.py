# © 2009 Tech-Receptives Solutions Pvt. Ltd.
# © 2018 FactorLibre
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import socket
import logging
import xmlrpc.client
import urllib
from odoo.addons.component.core import AbstractComponent
from odoo.addons.queue_job.exception import FailedJobError
from odoo.addons.connector.exception import (NetworkRetryableError,
                                             RetryableJobError)
from datetime import datetime
_logger = logging.getLogger(__name__)

try:
    from woocommerce import API
except ImportError:
    _logger.debug("cannot import 'woocommerce'")

recorder = {}

WOO_DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S'


def call_to_key(method, arguments):
    """ Used to 'freeze' the method and arguments of a call to WooCommerce
    so they can be hashable; they will be stored in a dict.

    Used in both the recorder and the tests.
    """
    def freeze(arg):
        if isinstance(arg, dict):
            items = dict((key, freeze(value)) for key, value
                         in arg.items())
            return frozenset(iter(items.items()))
        elif isinstance(arg, list):
            return tuple([freeze(item) for item in arg])
        else:
            return arg

    new_args = []
    for arg in arguments:
        new_args.append(freeze(arg))
    return (method, tuple(new_args))


def record(method, arguments, result):
    """ Utility function which can be used to record test data
    during synchronisations. Call it from WooCRUDAdapter._call

    Then ``output_recorder`` can be used to write the data recorded
    to a file.
    """
    recorder[call_to_key(method, arguments)] = result


def output_recorder(filename):
    import pprint
    with open(filename, 'w') as f:
        pprint.pprint(recorder, f)
    _logger.debug('recorder written to file %s', filename)


class WooLocation(object):

    def __init__(self, location, consumer_key, consumer_secret):
        self._location = location
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret

    @property
    def location(self):
        location = self._location
        return location


class WooAPI(object):

    def __init__(self, location):
        """
        :param location: Woocommerce Location
        :type location: :class:`WooLocation`
        """
        self._location = location
        self._api = None

    @property
    def api(self):
        is_https =\
            urllib.parse.urlparse(self._location.location).scheme == 'https'
        if self._api is None:
            api = API(
                url=self._location.location,
                consumer_key=self._location.consumer_key,
                consumer_secret=self._location.consumer_secret,
                wp_api=True,
                timeout=20,
                version="wc/v1",
                query_string_auth=is_https
            )
            self._api = api
        return self._api

    def call(self, endpoint, method='get', data=None):
        try:
            start = datetime.now()
            try:
                assert method in ['get', 'post', 'put', 'delete', 'options']
                endpoint_args = [endpoint]
                if method in ['post', 'put']:
                    if not data:
                        raise FailedJobError(
                            "Failed %s: %s. Data is required" % (
                                method, endpoint))
                    endpoint_args.append(data)
                response = getattr(self.api, method)(*endpoint_args)
                if not response.ok:
                    response_json = response.json()
                    if response_json.get('code') and \
                            response_json.get('message'):
                        raise FailedJobError(
                            "%s error: %s - %s" % (response.status_code,
                                                   response_json['code'],
                                                   response_json['message']))
                    else:
                        return response.raise_for_status()
            except:
                _logger.error("api.call(%s) failed with method %s" % (
                    endpoint, method))
                raise
            else:
                _logger.debug("api.call(%s, %s) returned in %s seconds",
                              method, endpoint,
                              (datetime.now() - start).seconds)
            return response
        except (socket.gaierror, socket.error, socket.timeout) as err:
            raise NetworkRetryableError(
                'A network error caused the failure of the job: '
                '%s' % err)
        except xmlrpc.client.ProtocolError as err:
            if err.errcode in [502,   # Bad gateway
                               503,   # Service unavailable
                               504]:  # Gateway timeout
                raise RetryableJobError(
                    'A protocol error caused the failure of the job:\n'
                    'URL: %s\n'
                    'HTTP/HTTPS headers: %s\n'
                    'Error code: %d\n'
                    'Error message: %s\n' %
                    (err.url, err.headers, err.errcode, err.errmsg))
            else:
                raise


class WooCRUDAdapter(AbstractComponent):
    """ External Records Adapter for woo """

    _name = 'woocommerce.crud.adapter'
    _inherit = ['base.backend.adapter', 'base.woocommerce.connector']
    _usage = 'backend.adapter'

    def search(self, params=None):
        """ Search records according to some criterias
        and returns a list of ids """
        raise NotImplementedError

    def read(self, id, params=None):
        """ Returns the information of a record """
        raise NotImplementedError

    def search_read(self, params=None):
        """ Search records according to some criterias
        and returns their information"""
        raise NotImplementedError

    def create(self, data):
        """ Create a record on the external system """
        raise NotImplementedError

    def write(self, id, data):
        """ Update records on the external system """
        raise NotImplementedError

    def delete(self, id):
        """ Delete a record on the external system """
        raise NotImplementedError

    def _call(self, endpoint, method='get', params=None, data=None):
        try:
            wc_api = getattr(self.work, 'wc_api')
        except AttributeError:
            raise AttributeError(
                'You must provide a wc_api attribute with a '
                'WooAPI instance to be able to use the '
                'Backend Adapter.'
            )
        endpoint_url = endpoint
        if params:
            url_arguments = urllib.parse.urlencode(params)
            endpoint_url = "%s?%s" % (endpoint, url_arguments)
        response = wc_api.call(endpoint_url, method=method, data=data)
        response_json = response.json()
        return response_json


class GenericAdapter(AbstractComponent):

    _name = 'woocommerce.adapter'
    _inherit = 'woocommerce.crud.adapter'

    _woo_model = None

    def search(self, params=None):
        """ Search records according to some criterias
        and returns a list of ids

        :rtype: list
        """
        if not params:
            params = {}
        response = self._call(self._woo_model, params=params)
        return [r['id'] for r in response]

    def read(self, id, params=None):
        """ Returns the information of a record

        :rtype: dict
        """
        return self._call('%s/%s' % (self._woo_model, id), params=params)

    def search_read(self, params=None):
        """ Search records according to some criterias
        and returns their information"""
        if not params:
            params = {}
        response = self._call(self._woo_model, params=params)
        return response

    def create(self, data):
        """ Create a record on the external system """
        return self._call('%s' % self._woo_model, method='post', data=[data])

    def write(self, id, data):
        """ Update records on the external system """
        return self._call('%s/%s' % (self._woo_model, id),
                          method='put', data=data)

    def delete(self, id):
        """ Delete a record on the external system """
        return self._call('%s/%s' % (self._woo_model, id), method='delete')
