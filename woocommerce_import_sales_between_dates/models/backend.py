# © 2018 FactorLibre - Álvaro Marcos <alvaro.marcos@factorlibre.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openerp import models, api


class wc_backend(models.Model):
    _inherit = 'wc.backend'

    @api.multi
    def import_orders_between_dates(
            self, import_orders_from_date, import_orders_to_date):
        for backend in self:
            params = {}
            if import_orders_from_date:
                params['after'] = self._date_as_user_tz(
                    import_orders_from_date)
            if import_orders_to_date:
                params['before'] = self._date_as_user_tz(
                    import_orders_to_date)
            self.env['woo.sale.order'].with_delay().import_batch(
                backend, params=params)
        return True
