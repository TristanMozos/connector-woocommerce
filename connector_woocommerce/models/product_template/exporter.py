# -*- coding: utf-8 -*-
# © 2018 FactorLibre - Hugo Santos <hugo.santos@factorlibre.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo.addons.component.core import Component


class ProductInventoryExporter(Component):
    _name = 'woo.product.inventory.exporter'
    _inherit = 'woocommerce.exporter'
    _apply_on = ['woo.product.template']
    _usage = 'product.inventory.exporter'

    def _get_data(self, binding, fields):
        result = {}
        if 'woo_qty' in fields:
            result.update({
                'stock_quantity': binding.woo_qty,
                'manage_stock': True,
                'in_stock': binding.woo_qty > 0
            })
        return result

    def run(self, binding, fields):
        """ Export the product inventory to WooCommerce """
        external_id = self.binder.to_external(binding)
        data = self._get_data(binding, fields)
        self.backend_adapter.write(external_id, data)
