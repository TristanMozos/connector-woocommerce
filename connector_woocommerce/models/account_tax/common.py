# -*- coding: utf-8 -*-
# © 2018 FactorLibre - Hugo Santos <hugo.santos@factorlibre.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openerp import fields, models


class WooAccountTax(models.Model):
    _name = 'woo.account.tax'
    _inherit = 'woo.binding'
    _inherits = {'account.tax': 'odoo_id'}
    _description = 'woo account tax'

    _rec_name = 'name'

    odoo_id = fields.Many2one(comodel_name='account.tax',
                              string='Tax',
                              required=True,
                              ondelete='cascade')
    backend_id = fields.Many2one(
        comodel_name='wc.backend',
        string='Woo Backend',
        required=True
    )


class AccountTax(models.Model):
    _inherit = 'account.tax'

    woocommerce_bind_ids = fields.One2many(
        'woo.account.tax', 'odoo_id', 'WooCommerce Bindings')
