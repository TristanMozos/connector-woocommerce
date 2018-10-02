# © 2009 Tech-Receptives Solutions Pvt. Ltd.
# © 2018 FactorLibre
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from odoo.addons.connector.exception import IDMissingInBackend
from odoo import _
from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping
from odoo.addons.queue_job.exception import NothingToDoJob

_logger = logging.getLogger(__name__)


class ProductProductBatchImporter(Component):
    _name = 'woocommerce.product.product.batch.importer'
    _inherit = 'woocommerce.delayed.batch.importer'
    _apply_on = ['woo.product.product']

    def _run_page(self, external_id, template_id, params, **kwargs):
        record_ids = self.backend_adapter.search(external_id, params=params)
        for record_id in record_ids:
            self._import_record(record_id['id'], external_id, template_id,
                                job_options=None, **kwargs)
        return record_ids

    def _import_record(self, external_id, id_template, binding_id,
                       job_options=None, **kwargs):
        """ Delay the import of the records"""
        delayable = self.model.with_delay(**job_options or {})
        delayable.import_record(self.backend_record, external_id,
                                id_template, binding_id, **kwargs)

    def run(self, external_id, template_id, params=None, **kwargs):
        """ Run the synchronization """
        if params is None:
            params = {}

        if 'per_page' in params:
            self._run_page(external_id, template_id, params, **kwargs)
            return
        page_number = 0
        params['per_page'] = self.page_limit
        while True:
            page_number += 1
            params['page'] = page_number
            record_ids = self._run_page(external_id, template_id,
                                        params, **kwargs)
            if len(record_ids) != self.page_limit:
                break


class ProductProductImporter(Component):
    _name = 'woocommerce.product.product.importer'
    _inherit = 'woocommerce.importer'
    _apply_on = ['woo.product.product']

    def run(self, external_id, id_template, binding_id, force=False):
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
            self.woo_record = self._get_woo_data(external_id, id_template)
            self.woo_record['binding_id'] = binding_id
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

    def _get_woo_data(self, id_variant, id_template):
        """ Return the raw WooCommerce data for ``self.external_id`` """
        return self.backend_adapter.read(id_variant, id_template)

    def _after_import(self, binding):
        """ Hook called at the end of the import """
        return


class ProductProductImportMapper(Component):
    _name = 'woocommerce.product.product.import.mapper'
    _inherit = 'woocommerce.import.mapper'
    _apply_on = 'woo.product.product'

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}

    @mapping
    def product_tmpl_id(self, record):
        if record['binding_id']:
            return {
                'product_tmpl_id': record['binding_id']
            }
        else:
            binder = self.binder_for('woo.product.template')
            template = binder.to_internal(record['id_template'], unwrap=True)
            if template:
                return {'product_tmpl_id': template.id}

    @mapping
    def name(self, record):
        binder = self.binder_for('woo.product.template')
        template = binder.to_internal(record['id_template'], unwrap=True)
        if template:
            return {'name': template.name}

    @mapping
    def list_price(self, record):
        return {
            'list_price': record['price'],
            'lst_price': record['price']
        }

    @mapping
    def attributes(self, record):
        options = []
        for attribute in record['attributes']:
            result_id = self.env['product.attribute.value'].search([
                ('name', '=', attribute['option'])
            ]).id
            if result_id:
                options += [result_id]
        return {
            'attribute_value_ids': [(6, 0, options)]
        }

    @mapping
    def qty_available(self, record):
        return {
            'qty_available': record['stock_quantity']
        }

    @mapping
    def sku(self, record):
        return {
            'default_code': record['sku']
        }

    @mapping
    def weight(self, record):
        return {'weight': record['weight']}
