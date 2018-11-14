# © 2009 Tech-Receptives Solutions Pvt. Ltd.
# © 2018 FactorLibre
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from odoo import models, fields, api
from odoo.addons.component.core import Component
from odoo.addons.queue_job.job import job, related_action
# from odoo.addons.component_event import skip_if

_logger = logging.getLogger(__name__)


class WooSaleOrderStatus(models.Model):
    _name = 'woo.sale.order.status'
    _description = 'WooCommerce Sale Order Status'

    name = fields.Char('Name')
    desc = fields.Text('Description')


class WooSaleOrder(models.Model):
    _name = 'woo.sale.order'
    _inherit = 'woo.binding'
    _inherits = {'sale.order': 'odoo_id'}
    _description = 'Woo Sale Order'

    _rec_name = 'name'

    status_id = fields.Many2one('woo.sale.order.status',
                                'WooCommerce Order Status')

    odoo_id = fields.Many2one(comodel_name='sale.order',
                              string='Sale Order',
                              required=True,
                              ondelete='cascade')
    woo_order_line_ids = fields.One2many(
        comodel_name='woo.sale.order.line',
        inverse_name='woo_order_id',
        string='Woo Order Lines'
    )
    backend_id = fields.Many2one(
        comodel_name='wc.backend',
        string='Woo Backend',
        store=True,
        readonly=False,
        required=True,
    )

    @job(default_channel='root.woocommerce')
    @related_action(action='related_action_unwrap_binding')
    @api.multi
    def export_state(self, fields=None):
        """ Export the state of a sale order. """
        self.ensure_one()
        with self.backend_id.work_on(self._name) as work:
            exporter = work.component(usage='sale.order.exporter')
            return exporter.run(self, fields)


class WooSaleOrderLine(models.Model):
    _name = 'woo.sale.order.line'
    _inherits = {'sale.order.line': 'odoo_id'}

    woo_order_id = fields.Many2one(comodel_name='woo.sale.order',
                                   string='Woo Sale Order',
                                   required=True,
                                   ondelete='cascade',
                                   index=True)

    odoo_id = fields.Many2one(comodel_name='sale.order.line',
                              string='Sale Order Line',
                              required=True,
                              ondelete='cascade')

    backend_id = fields.Many2one(
        related='woo_order_id.backend_id',
        string='Woo Backend',
        readonly=True,
        store=True,
        required=False,
    )

    @api.model
    def create(self, vals):
        woo_order_id = vals['woo_order_id']
        binding = self.env['woo.sale.order'].browse(woo_order_id)
        vals['order_id'] = binding.odoo_id.id
        binding = super(WooSaleOrderLine, self).create(vals)
        return binding


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    woo_bind_ids = fields.One2many(
        comodel_name='woo.sale.order.line',
        inverse_name='odoo_id',
        string="WooCommerce Bindings",
    )


class SaleOrderAdapter(Component):
    _name = 'woocommerce.sale.order.adapter'
    _inherit = 'woocommerce.adapter'
    _apply_on = 'woo.sale.order'
    _woo_model = 'orders'


class WooBindingSaleOrderListener(Component):
    _name = 'woo.stock.picking.listener'
    _inherit = 'base.connector.listener'
    _apply_on = ['stock.picking']

    # @skip_if(lambda self, record: self.no_connector_export(record))
    def on_picking_out_done(self, record, method):
        sale_id = record.group_id.sale_id.id
        woo_sale = self.env['woo.sale.order'].search([('odoo_id', '=', sale_id)])
        if woo_sale:
            woo_sale.with_delay(priority=20).export_state(
                fields=None
            )
