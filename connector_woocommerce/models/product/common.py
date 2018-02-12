# © 2009 Tech-Receptives Solutions Pvt. Ltd.
# © 2018 FactorLibre
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import models, fields
from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class WooProductProduct(models.Model):
    _name = 'woo.product.product'
    _inherit = 'woo.binding'
    _inherits = {'product.product': 'odoo_id'}
    _description = 'woo product product'

    _rec_name = 'name'
    odoo_id = fields.Many2one(comodel_name='product.product',
                              string='product',
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
    credated_at = fields.Date('created_at')
    weight = fields.Float('weight')


class ProductProductAdapter(Component):
    _name = 'woocommerce.product.product.adapter'
    _inherit = 'woocommerce.adapter'
    _apply_on = 'woo.product.product'

    _woo_model = 'products'
