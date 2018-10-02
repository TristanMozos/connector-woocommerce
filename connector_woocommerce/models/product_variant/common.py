# © 2009 Tech-Receptives Solutions Pvt. Ltd.
# © 2018 FactorLibre
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from odoo import models, fields, api
from odoo.addons.queue_job.job import job
from odoo.addons.component.core import Component


_logger = logging.getLogger(__name__)


def chunks(items, length):
    for index in range(0, len(items), length):
        yield items[index:index + length]


class WooProductProduct(models.Model):
    _name = 'woo.product.product'
    _inherit = 'woo.binding'
    _inherits = {'product.product': 'odoo_id'}

    odoo_id = fields.Many2one(comodel_name='product.product',
                              string='Product Variant',
                              required=True,
                              ondelete='cascade')

    backend_id = fields.Many2one(
        comodel_name='wc.backend',
        string='Woo Backend',
        store=True,
        readonly=False,
        required=True,
    )

    @job(default_channel='root.woocommerce')
    @api.model
    def import_batch(self, backend, external_id, template_id, params=None):
        """ Prepare the import of records modified on  Woocommerce"""
        if params is None:
            params = {}
        with backend.work_on(self._name) as work:
            importer = work.component(usage='batch.importer')
            return importer.run(external_id, template_id, params=params)

    @job(default_channel='root.woocommerce')
    @api.model
    def import_record(self, backend, external_id, id_attribute,
                      binding_id, force=False):
        """ Import a Woocommerce record """
        with backend.work_on(self._name) as work:
            importer = work.component(usage='record.importer')
            return importer.run(external_id, id_attribute,
                                binding_id, force=force)


class ProductProductAdapter(Component):
    _name = 'woocommerce.product.product.adapter'
    _inherit = 'woocommerce.adapter'
    _apply_on = 'woo.product.product'

    _woo_model = 'products/{template_id}/variations'

    def search(self, external_id, params=None):
        self._woo_model = self._woo_model.format(template_id=external_id)
        if not params:
            params = {}
        response = self._call(self._woo_model, params=params)
        return response

    def read(self, id, id_template, params=None):
        """ Returns the information of a record
        :rtype: dict
        """
        self._woo_model = self._woo_model.format(template_id=id_template)
        values = self._call('%s/%s' % (self._woo_model, id), params=params)
        values['id_template'] = id_template
        return values
