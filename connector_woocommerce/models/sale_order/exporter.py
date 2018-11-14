from odoo.addons.component.core import Component


class SaleStateExporter(Component):
    _name = 'woo.sale.order.exporter'
    _inherit = 'woocommerce.exporter'
    _apply_on = ['woo.sale.order']
    _usage = 'sale.order.exporter'

    def _get_data(self, binding, fields):
        result = {}
        result.update({
            'status': 'completed',
        })
        return result

    def run(self, binding, fields):
        """ Export the product inventory to WooCommerce """
        external_id = self.binder.to_external(binding)
        data = self._get_data(binding, fields)
        self.backend_adapter.write(external_id, data)
