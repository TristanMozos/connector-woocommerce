# -*- coding: utf-8 -*-
# © 2018 FactorLibre - Hugo Santos <hugo.santos@factorlibre.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openerp import fields, models


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    woocommerce_code = fields.Char('WooCommerce Carrier Code')
