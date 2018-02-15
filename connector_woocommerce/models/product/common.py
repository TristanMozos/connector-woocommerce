# © 2009 Tech-Receptives Solutions Pvt. Ltd.
# © 2018 FactorLibre
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from collections import defaultdict

from odoo import api, models, fields
from odoo.addons.component.core import Component
from odoo.addons.component_event import skip_if
from odoo.addons.queue_job.job import job, related_action


_logger = logging.getLogger(__name__)


def chunks(items, length):
    for index in range(0, len(items), length):
        yield items[index:index + length]


class WooProductProduct(models.Model):
    _name = 'woo.product.product'
    _inherit = 'woo.binding'
    _inherits = {'product.product': 'odoo_id'}
    _description = 'woo product product'

    _rec_name = 'name'
    odoo_id = fields.Many2one(comodel_name='product.product',
                              string='product',
                              required=True,
                              ondelete='cascade')
    backend_id = fields.Many2one(
        comodel_name='wc.backend',
        string='Woo Backend',
        store=True,
        readonly=False,
        required=True,
    )

    slug = fields.Char('Slug Name')
    credated_at = fields.Date('created_at')
    weight = fields.Float('weight')
    woo_qty = fields.Float('Computed Quantity',
                           help="Last computed quantity to send to "
                           "WooCommerce")
    no_stock_sync = fields.Boolean(
        string='No Stock Synchronization',
        required=False,
        help="Check this to exclude the product "
             "from stock synchronizations.",
    )

    RECOMPUTE_QTY_STEP = 1000  # products at a time

    @job(default_channel='root.woocommerce')
    @related_action(action='related_action_unwrap_binding')
    @api.multi
    def export_inventory(self, fields=None):
        """ Export the inventory configuration and quantity of a product. """
        self.ensure_one()
        with self.backend_id.work_on(self._name) as work:
            exporter = work.component(usage='product.inventory.exporter')
            return exporter.run(self, fields)

    @api.multi
    def recompute_wocommerce_qty(self):
        """ Check if the quantity in the stock location configured
        on the backend has changed since the last export.

        If it has changed, write the updated quantity on `woo_qty`.
        The write on `woo_qty` will trigger an `on_record_write`
        event that will create an export job.

        It groups the products by backend to avoid to read the backend
        informations for each product.
        """
        # group products by backend
        backends = defaultdict(set)
        for product in self:
            backends[product.backend_id].add(product.id)

        for backend, product_ids in list(backends.items()):
            self._recompute_woocommerce_qty_backend(backend,
                                                    self.browse(product_ids))
        return True

    @api.multi
    def _recompute_woocommerce_qty_backend(self, backend, products,
                                           read_fields=None):
        """ Recompute the products quantity for one backend.

        If field names are passed in ``read_fields`` (as a list), they
        will be read in the product that is used in
        :meth:`~.woo_qty`.

        """
        if backend.product_stock_field_id:
            stock_field = backend.product_stock_field_id.name
        else:
            stock_field = 'virtual_available'

        location = self.env['stock.location']
        if self.env.context.get('location'):
            location = location.browse(self.env.context['location'])
        else:
            location = backend.warehouse_id.lot_stock_id

        product_fields = ['woo_qty', stock_field]
        if read_fields:
            product_fields += read_fields

        self_with_location = self.with_context(location=location.id)
        for chunk_ids in chunks(products.ids, self.RECOMPUTE_QTY_STEP):
            records = self_with_location.browse(chunk_ids)
            for product in records.read(fields=product_fields):
                new_qty = self._woo_qty(product,
                                        backend,
                                        location,
                                        stock_field)
                if new_qty != product['woo_qty']:
                    self.browse(product['id']).woo_qty = new_qty

    @api.multi
    def _woo_qty(self, product, backend, location, stock_field):
        """ Return the current quantity for one product.

        Can be inherited to change the way the quantity is computed,
        according to a backend / location.

        If you need to read additional fields on the product, see the
        ``read_fields`` argument of
        :meth:`~._recompute_woocommerce_qty_backend`

        """
        return product[stock_field]


class ProductProduct(models.Model):
    _inherit = 'product.product'

    woocommerce_bind_ids = fields.One2many(
        'woo.product.product', 'odoo_id', 'WooCommerce Bindings')


class ProductProductAdapter(Component):
    _name = 'woocommerce.product.product.adapter'
    _inherit = 'woocommerce.adapter'
    _apply_on = 'woo.product.product'

    _woo_model = 'products'


class WooBindingProductListener(Component):
    _name = 'woo.binding.product.product.listener'
    _inherit = 'base.connector.listener'
    _apply_on = ['woo.product.product']

    # fields which should not trigger an export of the products
    # but an export of their inventory
    INVENTORY_FIELDS = ('woo_qty',)

    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    def on_record_write(self, record, fields=None):
        if record.no_stock_sync:
            return
        inventory_fields = list(
            set(fields).intersection(self.INVENTORY_FIELDS)
        )
        if inventory_fields:
            record.with_delay(priority=20).export_inventory(
                fields=inventory_fields
            )
