# -*- coding: utf-8 -*-
# © 2018 FactorLibre - Álvaro Marcos <alvaro.marcos@factorlibre.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)
from openerp import api, fields, models


class ImportBetweenDates(models.TransientModel):
    _name = "import.between.dates"

    import_orders_from_date = fields.Datetime(
        string='Import sales from', required=True
    )
    import_orders_to_date = fields.Datetime(
        string='Import sales to', required=True
    )

    @api.multi
    def import_orders(self):
        self.ensure_one()
        self.env["wc.backend"].browse(
            self.env.context["active_id"]).import_orders_between_dates(
                self.import_orders_from_date, self.import_orders_to_date)
