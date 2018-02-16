# © 2009 Tech-Receptives Solutions Pvt. Ltd.
# © 2018 FactorLibre
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create

_logger = logging.getLogger(__name__)


class CustomerBatchImporter(Component):
    """ Import the WooCommerce Partners.

    For every partner in the list, a delayed job is created.
    """
    _name = 'woocommerce.partner.batch.importer'
    _inherit = 'woocommerce.delayed.batch.importer'
    _apply_on = 'woo.res.partner'


class CustomerImporter(Component):
    _name = 'woocommerce.partner.importer'
    _inherit = 'woocommerce.importer'
    _apply_on = 'woo.res.partner'


class CustomerImportMapper(Component):
    _name = 'woocommerce.partner.import.mapper'
    _inherit = 'woocommerce.import.mapper'
    _apply_on = 'woo.res.partner'

    direct = [
        ('email', 'email')
    ]

    @mapping
    def name(self, record):
        if record.get('billing_address', {}).get('company'):
            return {
                'name': record['billing_address']['company'],
                'company_type': 'company'
            }
        return {
            'name': record['first_name'] + " " + record['last_name'],
            'company_type': 'person'
        }

    @mapping
    def city(self, record):
        if record.get('billing_address'):
            rec = record['billing_address']
            return {'city': rec['city'] or None}

    @mapping
    def zip(self, record):
        if record.get('billing_address'):
            rec = record['billing_address']
            return {'zip': rec['postcode'] or None}

    @mapping
    def address(self, record):
        if record.get('billing_address'):
            rec = record['billing_address']
            return {'street': rec['address_1'] or None}

    @mapping
    def address_2(self, record):
        if record.get('billing_address'):
            rec = record['billing_address']
            return {'street2': rec['address_2'] or None}

    @mapping
    def country(self, record):
        if record.get('billing_address'):
            rec = record['billing_address']
            if rec['country']:
                country_id = self.env['res.country'].search(
                    [('code', '=', rec['country'])])
                country_id = country_id.id
            else:
                country_id = False
            return {'country_id': country_id}

    @mapping
    def state(self, record):
        if record.get('billing_address'):
            rec = record['billing_address']
            if rec['state'] and rec['country']:
                state_id = self.env['res.country.state'].search(
                    [('code', '=', rec['state'])], limit=1)
                if state_id:
                    return {'state_id': state_id.id}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}

    @only_create
    @mapping
    def is_company(self, record):
        # partners are companies so we can bind
        # addresses on them
        return {'is_company': True}


class AddressImportMapper(Component):
    _name = 'woocommerce.address.import.mapper'
    _inherit = 'woocommerce.import.mapper'
    _apply_on = 'woo.address'

    @mapping
    def name(self, record):
        return {
            'name': record['first_name'] + " " + record['last_name']
        }

    @mapping
    def city(self, record):
        return {'city': record['city'] or None}

    @mapping
    def zip(self, record):
        return {'zip': record['postcode'] or None}

    @mapping
    def address(self, record):
        return {'street': record['address_1'] or None}

    @mapping
    def address_2(self, record):
        return {'street2': record['address_2'] or None}

    @mapping
    def country(self, record):
        if record['country']:
            country_id = self.env['res.country'].search(
                [('code', '=', record['country'])])
            country_id = country_id.id
        else:
            country_id = False
        return {'country_id': country_id}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}
