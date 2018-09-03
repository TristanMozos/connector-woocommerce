# © 2018 FactorLibre - Álvaro Marcos <alvaro.marcos@factorlibre.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)
from openerp import api, fields, models


class ImportOrder(models.TransientModel):
    _name = "import.order"

    order_id = fields.Char("Order Id")

    @api.multi
    def import_order(self):
        self.ensure_one()
        self.env["wc.backend"].browse(
            self.env.context["active_id"]).import_order(
                self.order_id)
