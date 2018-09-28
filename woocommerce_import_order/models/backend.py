# © 2018 FactorLibre - Álvaro Marcos <alvaro.marcos@factorlibre.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openerp import models, api


class wc_backend(models.Model):
    _inherit = 'wc.backend'

    @api.multi
    def import_order(self, order_id):
        for backend in self:
            if order_id:
                self.env['woo.sale.order'].import_record(
                    backend, order_id)
        return True
