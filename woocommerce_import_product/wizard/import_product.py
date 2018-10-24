# © 2018 FactorLibre - Álvaro Marcos <alvaro.marcos@factorlibre.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)
from openerp import api, fields, models


class ImportProduct(models.TransientModel):
    _name = "import.product"

    product_id = fields.Char("Product Id")

    @api.multi
    def import_product(self):
        self.ensure_one()
        self.env["wc.backend"].browse(
            self.env.context["active_id"]).import_product(
                self.product_id)
