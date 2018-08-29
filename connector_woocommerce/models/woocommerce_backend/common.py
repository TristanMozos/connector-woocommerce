# © 2009 Tech-Receptives Solutions Pvt. Ltd.
# © 2018 FactorLibre
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import pytz
import logging

from contextlib import contextmanager
from datetime import datetime, timedelta

from odoo import models, fields, api, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError
from ...components.backend_adapter import (WooLocation,
                                           WooAPI)

_logger = logging.getLogger(__name__)

try:
    from woocommerce import API
except ImportError:
    _logger.debug("Cannot import 'woocommerce'")

IMPORT_DELTA_BUFFER = 30  # seconds


class WooBackend(models.Model):
    _name = 'wc.backend'
    _inherit = 'connector.backend'
    _description = 'WooCommerce Backend Configuration'

    @api.model
    def select_versions(self):
        """ Available versions in the backend.

        Can be inherited to add custom versions.  Using this method
        to add a version from an ``_inherit`` does not constrain
        to redefine the ``version`` field in the ``_inherit`` model.
        """
        return [('v2', 'V2')]

    @api.model
    def _get_stock_field_id(self):
        field = self.env['ir.model.fields'].search(
            [('model', '=', 'product.product'),
             ('name', '=', 'virtual_available')],
            limit=1)
        return field

    name = fields.Char("Name", required=True)
    location = fields.Char("Url", required=True)
    consumer_key = fields.Char("Consumer key")
    consumer_secret = fields.Char("Consumer Secret")
    version = fields.Selection(selection='select_versions', required=True)
    verify_ssl = fields.Boolean("Verify SSL")
    warehouse_id = fields.Many2one(
        comodel_name='stock.warehouse',
        string='Warehouse',
        required=True,
        help='Warehouse used to compute the '
             'stock quantities.',
    )
    product_stock_field_id = fields.Many2one(
        comodel_name='ir.model.fields',
        string='Stock Field',
        default=_get_stock_field_id,
        domain="[('model', 'in', ['product.product', 'product.template']),"
               " ('ttype', '=', 'float')]",
        help="Choose the field of the product which will be used for "
             "stock inventory updates.\nIf empty, Quantity Available "
             "is used.",
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        related='warehouse_id.company_id',
        string='Company',
        readonly=True,
    )
    default_lang_id = fields.Many2one(
        comodel_name='res.lang',
        string='Default Language',
        help="If a default language is selected, the records "
             "will be imported in the translation of this language.\n"
             "Note that a similar configuration exists "
             "for each storeview.",
    )
    import_orders_from_date = fields.Datetime(
        string='Import orders from date',
    )

    @contextmanager
    @api.multi
    def work_on(self, model_name, **kwargs):
        self.ensure_one()
        # lang = self.default_lang_id
        # if lang.code != self.env.context.get('lang'):
        #     self = self.with_context(lang=lang.code)
        woocommerce_location = WooLocation(
            self.location,
            self.consumer_key,
            self.consumer_secret
        )
        wc_api = WooAPI(woocommerce_location)
        _super = super(WooBackend, self)
        with _super.work_on(model_name, wc_api=wc_api, **kwargs) as work:
            yield work

    @api.model
    def _date_as_user_tz(self, dtstr):
        if not dtstr:
            return None
        timezone = pytz.timezone(self.env.user.partner_id.tz or 'utc')
        dt = datetime.strptime(dtstr, DEFAULT_SERVER_DATETIME_FORMAT)
        dt = pytz.utc.localize(dt)
        dt = dt.astimezone(timezone)
        return dt.strftime('%Y-%m-%dT%H:%M:%S')

    @api.multi
    def get_product_ids(self, data):
        product_ids = [x['id'] for x in data['products']]
        product_ids = sorted(product_ids)
        return product_ids

    @api.multi
    def get_product_category_ids(self, data):
        product_category_ids = [x['id'] for x in data['product_categories']]
        product_category_ids = sorted(product_category_ids)
        return product_category_ids

    @api.multi
    def get_customer_ids(self, data):
        customer_ids = [x['id'] for x in data['customers']]
        customer_ids = sorted(customer_ids)
        return customer_ids

    @api.multi
    def get_order_ids(self, data):
        order_ids = self.check_existing_order(data)
        return order_ids

    @api.multi
    def update_existing_order(self, woo_sale_order, data):
        """ Enter Your logic for Existing Sale Order """
        return True

    @api.multi
    def check_existing_order(self, data):
        order_ids = []
        for val in data['orders']:
            woo_sale_order = self.env['woo.sale.order'].search(
                [('external_id', '=', val['id'])])
            if woo_sale_order:
                self.update_existing_order(woo_sale_order[0], val)
                continue
            order_ids.append(val['id'])
        return order_ids

    @api.multi
    def test_connection(self):
        location = self.location
        cons_key = self.consumer_key
        sec_key = self.consumer_secret

        wcapi = API(url=location, consumer_key=cons_key,
                    consumer_secret=sec_key,
                    wp_api=True,
                    timeout=20,
                    version="wc/v2")
        r = wcapi.get("products")
        if r.status_code == 404:
            raise UserError(_("Enter Valid url"))
        val = r.json()
        msg = ''
        if 'errors' in r.json():
            msg = val['errors'][0]['message'] + '\n' + val['errors'][0]['code']
            raise UserError(_(msg))
        else:
            raise UserError(_('Test Success'))
        return True

    @api.multi
    def import_categories(self):
        for backend in self:
            self.env['woo.product.category'].with_delay().import_batch(backend)
        return True

    @api.multi
    def import_products(self):
        for backend in self:
            self.env['woo.product.product'].with_delay().import_batch(backend)
        return True

    @api.multi
    def import_customers(self):
        for backend in self:
            self.env['woo.res.partner'].with_delay().import_batch(backend)
        return True

    @api.multi
    def import_orders(self):
        import_start_time = datetime.now()
        for backend in self:
            params = {}
            if backend.import_orders_from_date:
                params['after'] = self._date_as_user_tz(
                    backend.import_orders_from_date)
            self.env['woo.sale.order'].with_delay().import_batch(
                backend, params=params)
        next_time = import_start_time - timedelta(seconds=30)
        next_time = fields.Datetime.to_string(next_time)
        self.write({'import_orders_from_date': next_time})
        return True

    @api.multi
    def _domain_for_update_product_stock_qty(self):
        return [
            ('backend_id', 'in', self.ids),
            ('type', '!=', 'service'),
            ('no_stock_sync', '=', False),
        ]

    @api.multi
    def update_product_stock_qty(self):
        woo_product_env = self.env['woo.product.product']
        domain = self._domain_for_update_product_stock_qty()
        woo_products = woo_product_env.search(domain)
        woo_products.recompute_wocommerce_qty()
        return True

    @api.model
    def _woocommerce_backend(self, callback, domain=None):
        if domain is None:
            domain = []
        backends = self.search(domain)
        if backends:
            getattr(backends, callback)()

    @api.model
    def _scheduler_import_sale_orders(self, domain=None):
        self._woocommerce_backend('import_orders', domain=domain)

    @api.model
    def _scheduler_update_product_stock_qty(self, domain=None):
        self._woocommerce_backend('update_product_stock_qty', domain=domain)
