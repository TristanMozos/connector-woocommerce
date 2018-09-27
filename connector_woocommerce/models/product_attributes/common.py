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


class WooProductAttribute(models.Model):
    _name = 'woo.product.attribute'
    _inherit = 'woo.binding'
    _inherits = {'product.attribute': 'odoo_id'}

    odoo_id = fields.Many2one(comodel_name='product.attribute',
                              string='Attribute',
                              required=True,
                              ondelete='cascade')

    backend_id = fields.Many2one(
        comodel_name='wc.backend',
        string='Woo Backend',
        store=True,
        readonly=False,
        required=True,
    )

    slug = fields.Char('Slug Name')


class WooProductAttributeValue(models.Model):
    _name = 'woo.product.attribute.value'
    _inherit = 'woo.binding'
    _inherits = {'product.attribute.value': 'odoo_id'}

    odoo_id = fields.Many2one(comodel_name='product.attribute.value',
                              string='Attribute Value',
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
    def import_batch(self, backend, id_attribute, params=None):
        """ Prepare the import of records modified on  Woocommerce"""
        if params is None:
            params = {}
        with backend.work_on(self._name) as work:
            importer = work.component(usage='batch.importer')
            return importer.run(id_attribute, params=params)

    @job(default_channel='root.woocommerce')
    @api.model
    def import_record(self, backend, external_id, id_attribute, force=False):
        """ Import a Woocommerce record """
        with backend.work_on(self._name) as work:
            importer = work.component(usage='record.importer')
            return importer.run(external_id, id_attribute, force=force)


class ProductAttributeAdapter(Component):
    _name = 'woocommerce.product.attribute.adapter'
    _inherit = 'woocommerce.adapter'
    _apply_on = 'woo.product.attribute'

    _woo_model = 'products/attributes'


class ProductAttributeValueAdapter(Component):
    _name = 'woocommerce.product.attribute.value.adapter'
    _inherit = 'woocommerce.adapter'
    _apply_on = 'woo.product.attribute.value'

    _woo_model = 'products/attributes/{attribute_id}/terms'
    _id_attribute = ''

    def search(self, id_attribute, params=None):
        self._woo_model = self._woo_model.format(attribute_id=id_attribute)
        self._id_attribute = id_attribute
        if not params:
            params = {}
        response = self._call(self._woo_model, params=params)
        return response

    def read(self, id, id_attribute, params=None):
        """ Returns the information of a record
        :rtype: dict
        """
        self._woo_model = self._woo_model.format(attribute_id=id_attribute)
        values = self._call('%s/%s' % (self._woo_model, id), params=params)
        values['id_attribute'] = id_attribute
        return values
