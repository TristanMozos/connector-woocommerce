# © 2009 Tech-Receptives Solutions Pvt. Ltd.
# © 2018 FactorLibre
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging

from datetime import datetime, timedelta
from odoo import _
from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping
from openerp.addons.connector.exception import RetryableJobError
from odoo.addons.queue_job.exception import NothingToDoJob, FailedJobError

_logger = logging.getLogger(__name__)


class SaleOrderBatchImporter(Component):
    """ Import the WooCommerce Orders.

    For every order in the list, a delayed job is created.
    """
    _name = 'woocommerce.sale.order.batch.importer'
    _inherit = 'woocommerce.delayed.batch.importer'
    _apply_on = ['woo.sale.order']

    def _import_record(self, external_id, job_options=None, **kwargs):
        job_options = {
            'max_retries': 0,
            'priority': 5,
        }
        return super(SaleOrderBatchImporter, self)._import_record(
            external_id, job_options=job_options)

    def run(self, filters=None):
        """ Run the synchronization """
        record_ids = self.backend_adapter.search(filters)
        order_ids = []
        for record_id in record_ids:
            woo_sale_order = self.env['woo.sale.order'].search(
                [('external_id', '=', record_id)])
            if woo_sale_order:
                self.update_existing_order(woo_sale_order[0], record_id)
            else:
                order_ids.append(record_id)
        _logger.info('search for woo partners %s returned %s',
                     filters, record_ids)
        for record_id in order_ids:
            self._import_record(record_id)


class SaleImportRule(Component):
    _name = 'woocommerce.sale.import.rule'
    _inherit = 'base.woocommerce.connector'
    _apply_on = 'woo.sale.order'
    _usage = 'sale.import.rule'

    def _rule_always(self, record, method):
        """ Always import the order """
        return True

    def _rule_never(self, record, method):
        """ Never import the order """
        raise NothingToDoJob('Orders with payment method %s '
                             'are never imported.' %
                             record['payment_method'])

    def _rule_paid(self, record, method):
        """ Import the order only if it has received a payment """
        if not record.get('date_paid'):
            raise RetryableJobError('The order has not been paid.\n'
                                    'The import will be retried later.')

    _rules = {
        'always': _rule_always,
        'paid': _rule_paid,
        'never': _rule_never,
        'authorized': _rule_paid,
    }

    def _rule_global(self, record, method):
        """ Rule always executed, whichever is the selected rule """
        # the order has been canceled since the job has been created
        order_id = record['id']
        max_days = method.days_before_cancel
        if max_days:
            fmt = '%Y-%m-%dT%H:%M:%S'
            order_date = datetime.strptime(record['date_created'], fmt)
            if order_date + timedelta(days=max_days) < datetime.now():
                raise NothingToDoJob('Import of the order %s canceled '
                                     'because it has not been paid since %d '
                                     'days' % (order_id, max_days))

    def check(self, record):
        """ Check whether the current sale order should be imported
        or not. It will actually use the payment method configuration
        and see if the choosed rule is fullfilled.

        :returns: True if the sale order should be imported
        :rtype: boolean
        """
        payment_method = record['payment_method']
        method = self.env['account.payment.mode'].search(
            [('woo_payment_method_code', '=', payment_method)],
            limit=1,
        )
        if not method:
            raise FailedJobError(
                "The configuration is missing for the Payment Mode '%s'.\n\n"
                "Resolution:\n"
                "- Go to "
                "'Accounting > Configuration > Management > Payment Modes'\n"
                "- Create a new Payment Mode with WooCommerce Code '%s'\n"
                "- Eventually link the Payment Mode to an existing Workflow "
                "Process or create a new one." % (payment_method,
                                                  payment_method))
        self._rule_global(record, method)
        self._rules[method.import_rule](self, record, method)


class SaleOrderImporter(Component):
    _name = 'woocommerce.sale.order.importer'
    _inherit = 'woocommerce.importer'
    _apply_on = ['woo.sale.order']

    def _must_skip(self):
        """ Hook called right after we read the data from the backend.

        If the method returns a message giving a reason for the
        skipping, the import will be interrupted and the message
        recorded in the job (if the import is called directly by the
        job, not by dependencies).

        If it returns None, the import will continue normally.

        :returns: None | str | unicode
        """
        if self.binder.to_internal(self.external_id):
            return _('Already imported')

    def _import_addresses(self):
        record = self.woo_record

        partner_email = record.get('billing', {}).get('email')
        if not record.get('customer_id') and partner_email:
            partner = self.env['woo.res.partner'].search([
                ('email', '=', partner_email),
                ('backend_id', '=', self.backend_record.id)
            ])
            if partner:
                woocommerce_id = partner.external_id
                if not str(woocommerce_id).startswith('guestorder:'):
                    record['customer_id'] = woocommerce_id

        is_guest_order = True
        if record.get('customer_id'):
            is_guest_order = False
            self._import_dependency(record['customer_id'],
                                    'woo.res.partner')

        partner_binder = self.binder_for('woo.res.partner')
        if is_guest_order:
            guest_customer_id = 'guestorder:%s' % record['number']

            record['customer_id'] = guest_customer_id
            address = record['billing']
            customer_record = {
                'id': guest_customer_id,
                'first_name': address['first_name'],
                'last_name': address['last_name'],
                'email': address['email'],
                'billing_address': address
            }
            mapper = self.component(usage='import.mapper',
                                    model_name='woo.res.partner')
            map_record = mapper.map_record(customer_record)
            partner_binding = self.env['woo.res.partner'].create(
                map_record.values(for_create=True))
            partner_binder.bind(guest_customer_id, partner_binding)
        else:
            importer = self.component(usage='record.importer',
                                      model_name='woo.res.partner')
            importer.run(record['customer_id'])
            partner_binding = partner_binder.to_internal(record['customer_id'])

        partner = partner_binding.odoo_id

        addresses_defaults = {'parent_id': partner.id,
                              'woo_partner_id': partner_binding.id,
                              'email': partner_email,
                              'active': False}

        addr_mapper = self.component(usage='import.mapper',
                                     model_name='woo.address')

        def create_address(address_record):
            map_record = addr_mapper.map_record(address_record)
            map_record.update(addresses_defaults)
            address_bind = self.env['woo.address'].create(
                map_record.values(for_create=True,
                                  parent_partner=partner))
            return address_bind.odoo_id.id

        billing_id = create_address(record['billing'])

        shipping_id = None
        if record['shipping']:
            shipping_id = create_address(record['shipping'])

        self.partner_id = partner.id
        self.partner_invoice_id = billing_id
        self.partner_shipping_id = shipping_id or billing_id

    def _check_special_fields(self):
        assert self.partner_id, (
            "self.partner_id should have been defined "
            "in SaleOrderImporter._import_addresses")
        assert self.partner_invoice_id, (
            "self.partner_id should have been "
            "defined in SaleOrderImporter._import_addresses")
        assert self.partner_shipping_id, (
            "self.partner_id should have been defined "
            "in SaleOrderImporter._import_addresses")

    def _create_data(self, map_record, **kwargs):
        self._check_special_fields()
        return super(SaleOrderImporter, self)._create_data(
            map_record,
            partner_id=self.partner_id,
            partner_invoice_id=self.partner_invoice_id,
            partner_shipping_id=self.partner_shipping_id,
            **kwargs)

    def _update_data(self, map_record, **kwargs):
        self._check_special_fields()
        return super(SaleOrderImporter, self)._update_data(
            map_record,
            partner_id=self.partner_id,
            partner_invoice_id=self.partner_invoice_id,
            partner_shipping_id=self.partner_shipping_id,
            **kwargs)

    def _import_dependencies(self):
        """ Import the dependencies for the record"""
        record = self.woo_record

        self._import_addresses()
        record = record['items']
        for line in record:
            _logger.debug('line: %s', line)
            if 'product_id' in line:
                self._import_dependency(line['product_id'],
                                        'woo.product.product')

    def _clean_woo_items(self, resource):
        """
        Method that clean the sale order line given by WooCommerce before
        importing it

        This method has to stay here because it allow to customize the
        behavior of the sale order.

        """
        child_items = {}  # key is the parent item id
        top_items = []

        # Group the childs with their parent
        for item in resource['line_items']:
            if item.get('parent_item_id'):
                child_items.setdefault(item['parent_item_id'], []).append(item)
            else:
                top_items.append(item)

        all_items = []
        for top_item in top_items:
            all_items.append(top_item)
        resource['items'] = all_items
        return resource

    def _get_woo_data(self):
        """ Return the raw WooCommerce data for ``self.external_id`` """
        record = super(SaleOrderImporter, self)._get_woo_data()
        # sometimes we need to clean woo items (ex : configurable
        # product in a sale)
        record = self._clean_woo_items(record)
        return record

    def _before_import(self):
        rules = self.component(usage='sale.import.rule')
        rules.check(self.woo_record)


class SaleOrderImportMapper(Component):
    _name = 'woocommerce.sale.order.mapper'
    _inherit = 'woocommerce.import.mapper'
    _apply_on = 'woo.sale.order'

    direct = [
        ('number', 'name')
    ]

    children = [('items', 'woo_order_line_ids', 'woo.sale.order.line')]

    @mapping
    def status(self, record):
        if record['status']:
            status_id = self.env['woo.sale.order.status'].search(
                [('name', '=', record['status'])])
            if status_id:
                return {'status_id': status_id[0].id}
            else:
                status_id = self.env['woo.sale.order.status'].create({
                    'name': record['status']
                })
                return {'status_id': status_id.id}
        else:
            return {'status_id': False}

    @mapping
    def customer_id(self, record):
        binder = self.binder_for('woo.res.partner')
        if record['customer_id']:
            partner = binder.to_internal(record['customer_id'],
                                         unwrap=True) or False
            assert partner, ("Please Check Customer Role \
                                in WooCommerce")
            result = {'partner_id': partner.id}
        else:
            customer = record['customer']['billing_address']
            country_id = False
            state_id = False
            if customer['country']:
                country_id = self.env['res.country'].search(
                    [('code', '=', customer['country'])])
                if country_id:
                    country_id = country_id.id
            if customer['state']:
                state_id = self.env['res.country.state'].search(
                    [('code', '=', customer['state'])])
                if state_id:
                    state_id = state_id.id
            name = customer['first_name'] + ' ' + customer['last_name']
            partner_dict = {
                'name': name,
                'city': customer['city'],
                'phone': customer['phone'],
                'zip': customer['postcode'],
                'state_id': state_id,
                'country_id': country_id
            }
            partner_id = self.env['res.partner'].create(partner_dict)
            partner_dict.update({
                'backend_id': self.backend_record.id,
                'openerp_id': partner_id.id,
            })
            result = {'partner_id': partner_id.id}
        return result

    @mapping
    def carrier_id(self, record):
        shipping_lines = record.get('shipping_lines', [])
        result = {}
        if shipping_lines:
            woocommerce_code = shipping_lines[0].get('method_id')
            if woocommerce_code:
                carrier = self.env['delivery.carrier'].search(
                    [('woocommerce_code', '=', woocommerce_code)],
                    limit=1,
                )
                if carrier:
                    result = {'carrier_id': carrier.id}
                else:
                    # FIXME: a mapper should not have any side effects
                    product = self.env.ref(
                        'connector_ecommerce.product_product_shipping')
                    carrier = self.env['delivery.carrier'].create({
                        'product_id': product.id,
                        'name': woocommerce_code,
                        'woocommerce_code': woocommerce_code})
                    result = {'carrier_id': carrier.id}
        return result

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}

    @mapping
    def payment(self, record):
        payment_method = record['payment_method']
        method = self.env['account.payment.mode'].search(
            [('woo_payment_method_code', '=', payment_method)],
            limit=1,
        )
        assert method, ("method %s should exist because the import fails "
                        "in SaleOrderImporter._before_import when it is "
                        " missing" % payment_method)
        return {'payment_mode_id': method.id}

    def _add_shipping_line(self, map_record, values):
        record = map_record.source
        for shipping_line in record.get('shipping_lines', []):
            amount_incl = float(shipping_line.get('total') or 0.0)
            amount_excl = amount_incl - float(record.get('total_tax') or 0.0)
            line_builder = self.component(usage='order.line.builder.shipping')
            # add even if the price is 0, otherwise odoo will add a shipping
            # line in the order when we ship the picking
            if record.get('prices_include_tax', False):
                line_builder.price_unit = amount_incl
            else:
                line_builder.price_unit = amount_excl

            if values.get('carrier_id'):
                carrier = self.env['delivery.carrier'].browse(
                    values['carrier_id'])
                line_builder.product = carrier.product_id

            line = (0, 0, line_builder.get_line())
            values['order_line'].append(line)
        return values

    def finalize(self, map_record, values):
        values.setdefault('order_line', [])
        values = self._add_shipping_line(map_record, values)
        # TODO: Discounts
        values.update({
            'partner_id': self.options.partner_id,
            'partner_invoice_id': self.options.partner_invoice_id,
            'partner_shipping_id': self.options.partner_shipping_id,
        })
        onchange = self.component(
            usage='ecommerce.onchange.manager.sale.order'
        )
        return onchange.play(values, values['woo_order_line_ids'])


class SaleOrderLineImportMapper(Component):
    _name = 'woocommerce.sale.order.line.mapper'
    _inherit = 'woocommerce.import.mapper'
    _apply_on = 'woo.sale.order.line'

    direct = [('quantity', 'product_uom_qty'),
              # ('quantity', 'product_qty'),
              ('name', 'name'),
              ('price', 'price_unit')
              ]

    @mapping
    def product_id(self, record):
        binder = self.binder_for('woo.product.product')
        product = binder.to_internal(record['product_id'], unwrap=True)
        assert product is not None, (
            "product_id %s should have been imported in "
            "SaleOrderImporter._import_dependencies" % record['product_id'])
        return {'product_id': product.id}
