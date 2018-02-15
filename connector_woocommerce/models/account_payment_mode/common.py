# -*- coding: utf-8 -*-
# © 2018 FactorLibre - Hugo Santos <hugo.santos@factorlibre.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openerp import models, fields


class AccountPaymentMode(models.Model):
    _inherit = 'account.payment.mode'

    woo_payment_method_code = fields.Char('WooCommerce Payment Method Code')
