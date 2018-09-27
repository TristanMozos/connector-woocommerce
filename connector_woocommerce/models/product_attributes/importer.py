# © 2009 Tech-Receptives Solutions Pvt. Ltd.
# © 2018 FactorLibre
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import urllib.request
import urllib.error
from odoo.addons.connector.exception import IDMissingInBackend
from odoo import _
from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import (mapping, only_create)

_logger = logging.getLogger(__name__)


class ProductAttributeBatchImporter(Component):
    _name = 'woocommerce.product.attribute.batch.importer'
    _inherit = 'woocommerce.delayed.batch.importer'
    _apply_on = ['woo.product.attribute']


class ProductAttributeValueBatchImporter(Component):
    _name = 'woocommerce.product.attribute.value.batch.importer'
    _inherit = 'woocommerce.delayed.batch.importer'
    _apply_on = ['woo.product.attribute.value']

    def _run_page(self, id_attribute, params, **kwargs):
        record_ids = self.backend_adapter.search(id_attribute, params=params)
        for record_id in record_ids:
            self._import_record(record_id['id'], id_attribute,
                                job_options=None, **kwargs)
        return record_ids

    def _import_record(self, external_id, id_attribute,
                       job_options=None, **kwargs):
        """ Delay the import of the records"""
        delayable = self.model.with_delay(**job_options or {})
        delayable.import_record(self.backend_record, external_id,
                                id_attribute, **kwargs)

    def run(self, id_attribute, params=None, **kwargs):
        """ Run the synchronization """
        self.attribute_id = id_attribute
        if params is None:
            params = {}

        if 'per_page' in params:
            self._run_page(id_attribute, params, **kwargs)
            return
        page_number = 0
        params['per_page'] = self.page_limit
        while True:
            page_number += 1
            params['page'] = page_number
            record_ids = self._run_page(id_attribute, params, **kwargs)
            if len(record_ids) != self.page_limit:
                break


class ProductAttributeImporter(Component):
    _name = 'woocommerce.product.attribute.importer'
    _inherit = 'woocommerce.importer'
    _apply_on = ['woo.product.attribute']

    def _import_attribute_values(self, backend_id):
        """ Delay the import of the records"""
        self.env['woo.product.attribute.value'].with_delay(
            ).import_batch(backend_id, self.woo_record['id'])

    def _after_import(self, binding):
        self._import_attribute_values(self.backend_record)
        return


class ProductAttributeValueImporter(Component):
    _name = 'woocommerce.product.attribute.value.importer'
    _inherit = 'woocommerce.importer'
    _apply_on = ['woo.product.attribute.value']

    def run(self, external_id, id_attribute, force=False):
        """ Run the synchronization

        :param external_id: identifier of the record on WooCommerce
        """
        self.external_id = external_id
        lock_name = 'import({}, {}, {}, {})'.format(
            self.backend_record._name,
            self.backend_record.id,
            self.work.model_name,
            external_id,
        )

        try:
            self.woo_record = self._get_woo_data(id_attribute)
        except IDMissingInBackend:
            return _('Record does no longer exist in WooCommerce')

        skip = self._must_skip()
        if skip:
            return skip

        binding = self._get_binding()
        if not force and self._is_uptodate(binding):
            return _('Already up-to-date.')

        # Keep a lock on this import until the transaction is committed
        # The lock is kept since we have detected that the informations
        # will be updated into Odoo
        self.advisory_lock_or_retry(lock_name)
        self._before_import()

        # import the missing linked resources
        self._import_dependencies()

        map_record = self._map_data()

        if binding:
            record = self._update_data(map_record)
            self._update(binding, record)
        else:
            record = self._create_data(map_record)
            binding = self._create(record)
        self.binder.bind(self.external_id, binding)

        self._after_import(binding)

    def _get_woo_data(self, id_attribute):
        """ Return the raw WooCommerce data for ``self.external_id`` """
        return self.backend_adapter.read(self.external_id, id_attribute)


class ProductAttributeImportMapper(Component):
    _name = 'woocommerce.product.attribute.import.mapper'
    _inherit = 'woocommerce.import.mapper'
    _apply_on = 'woo.product.attribute'

    direct = [
        ('name', 'name')
    ]

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}

    @mapping
    @only_create
    def openerp_id(self, record):
        attribute = self.env['product.attribute'].search([
            ('name', '=', record['name'])
        ])
        if attribute:
            return {'odoo_id': attribute.id}


class ProductAttributeValueImportMapper(Component):
    _name = 'woocommerce.product.attribute.value.import.mapper'
    _inherit = 'woocommerce.import.mapper'
    _apply_on = 'woo.product.attribute.value'

    direct = [
        ('name', 'name')
    ]

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}

    @mapping
    def name(self, record):
        return {'name': record['name']}

    @mapping
    def openerp_id(self, record):
        attribute = self.env['woo.product.attribute'].search([
            ('external_id', '=', int(record['id_attribute']))
        ]).odoo_id
        if attribute:
            return {'attribute_id': attribute.id}
