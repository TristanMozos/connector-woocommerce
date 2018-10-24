# © 2018 FactorLibre - Álvaro Marcos <alvaro.marcos@factorlibre.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openerp import models, api


class wc_backend(models.Model):
    _inherit = 'wc.backend'

    @api.multi
    def import_product(self, product_id):
        for backend in self:
            if product_id:
                self.env['woo.product.template'].import_record(
                    backend, product_id)
        return True
