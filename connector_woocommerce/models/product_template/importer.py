# © 2009 Tech-Receptives Solutions Pvt. Ltd.
# © 2018 FactorLibre
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import urllib.request
import urllib.error
import urllib.parse
import base64

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping
from odoo.addons.connector.exception import MappingError

_logger = logging.getLogger(__name__)


class ProductBatchImporter(Component):
    """ Import the WooCommerce Products.

    For every product in the list, a delayed job is created.
    """
    _name = 'woocommerce.product.template.batch.importer'
    _inherit = 'woocommerce.delayed.batch.importer'
    _apply_on = ['woo.product.template']


class ProductTemplateImporter(Component):
    _name = 'woocommerce.product.template.importer'
    _inherit = 'woocommerce.importer'
    _apply_on = ['woo.product.template']

    def _import_dependencies(self):
        """ Import the dependencies for the record"""
        record = self.woo_record
        for woo_category in record['categories']:
            self._import_dependency(woo_category['id'],
                                    'woo.product.category')
        for woo_attributes in record['attributes']:
            self._import_dependency(woo_attributes['id'],
                                    'woo.product.attribute')

    def _set_attributes(self, binding):
        record = self.woo_record
        attribute_line = self.env['product.attribute.line']
        # product_product = self.env['product.product']
        for value in record['attributes']:
            attribute_odoo = self.env['woo.product.attribute'].search([
                ('external_id', '=', value['id'])
            ]).odoo_id
            options = []
            attribute_line_search = attribute_line.search([
                ('attribute_id', '=', attribute_odoo.id),
                ('product_tmpl_id', '=', binding.odoo_id.id)
            ], limit=1)
            for name in value['options']:
                result_id = self.env['woo.product.attribute.value'].search([
                    ('name', '=', name)
                ]).odoo_id.id
                if result_id and result_id not in \
                        attribute_line_search.value_ids.ids:
                    options += [result_id]
            if options:
                attribute_line.create({
                    'attribute_id': attribute_odoo.id,
                    'value_ids': [(6, 0, options)],
                    'product_tmpl_id': binding.odoo_id.id,
                })

    def _import_variants(self, binding):
        self.woo_record['binding_id'] = binding.odoo_id.id
        self.env['woo.product.product'].with_delay().import_batch(
            self.backend_record, self.woo_record['id'], binding.odoo_id.id)

    def _after_import(self, binding):
        """ Hook called at the end of the import """
        image_importer = self.component(usage='product.image.importer')
        image_importer.run(self.woo_record, binding)
        self._set_attributes(binding)
        self._import_variants(binding)
        self.deactivate_default_product(binding)
        return

    def _deactivate_default_product(self, binding):
        if binding.product_variant_count != 1:
            for product in binding.product_variant_ids:
                if not product.attribute_value_ids:
                    self.env['product.product'].browse(product.id).write(
                        {'active': False})


class ProductImageImporter(Component):

    """ Import images for a record.

    Usually called from importers, in ``_after_import``.
    For instance from the products importer.
    """
    _name = 'woocommerce.product.image.importer'
    _inherit = 'woocommerce.importer'
    _apply_on = ['woo.product.template']
    _usage = 'product.image.importer'

    def _get_images(self, storeview_id=None):
        return self.backend_adapter.get_images(self.external_id)

    def _sort_images(self, images):
        """ Returns a list of images sorted by their priority.
        An image with the 'image' type is the the primary one.
        The other images are sorted by their position.

        The returned list is reversed, the items at the end
        of the list have the higher priority.
        """
        if not images:
            return {}
        # place the images where the type is 'image' first then
        # sort them by the reverse priority (last item of the list has
        # the the higher priority)

    def properEncode(self, url):
        url = url.replace("á", "%c3%a1")
        url = url.replace("ñ", "%c3%b1")
        url = url.replace("~", "%cc%83")
        url = url.replace("ó", "%c3%b3")
        url = url.replace("´", "%c2%b4")
        return url

    def _get_binary_image(self, image_data):
        url = image_data['src']
        url = self.properEncode(url)
        try:
            request = urllib.request.Request(url)
            binary = urllib.request.urlopen(request)
        except urllib.error.HTTPError as err:
            if err.code == 404:
                # the image is just missing, we skip it
                return
            else:
                # we don't know why we couldn't download the image
                # so we propagate the error, the import will fail
                # and we have to check why it couldn't be accessed
                raise
        except UnicodeEncodeError as err:
            return
        else:
            return binary.read()

    def _write_image_data(self, binding, binary, image_data):
        binding = binding.with_context(connector_no_export=True)
        binding.write({'image': base64.b64encode(binary)})

    def run(self, woo_record, binding):
        images = woo_record['images']
        binary = None
        while not binary and images:
            image_data = images.pop()
            binary = self._get_binary_image(image_data)
        if not binary:
            return
        self._write_image_data(binding, binary, image_data)


class ProductTemplateImportMapper(Component):
    _name = 'woocommerce.product.template.import.mapper'
    _inherit = 'woocommerce.import.mapper'
    _apply_on = 'woo.product.template'

    direct = [
        ('name', 'name'),
        ('description', 'description'),
        ('weight', 'weight'),
        ('price', 'list_price')
    ]

    @mapping
    def is_active(self, record):
        """Check if the product is active in Woo
        and set active flag in OpenERP
        status == 1 in Woo means active"""
        return {'active': record.get('catalog_visibility') == 'visible'}

    @mapping
    def type(self, record):
        return {'type': record['type']}

    @mapping
    def categories(self, record):
        woo_categories = record['categories']
        binder = self.binder_for('woo.product.category')

        category_ids = []
        main_categ_id = None

        for woo_category in woo_categories:
            cat = binder.to_internal(woo_category['id'], unwrap=True)
            if not cat:
                raise MappingError("The product category with "
                                   "woo id %s is not imported." %
                                   woo_category['id'])
            category_ids.append(cat.id)

        if category_ids:
            main_categ_id = category_ids.pop(0)

        result = {'categ_ids': [(6, 0, category_ids)]}
        if main_categ_id:  # OpenERP assign 'All Products' if not specified
            result['categ_id'] = main_categ_id
        return result

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}

    @mapping
    def list_price(self, record):
        return {
            'list_price': record['price'],
            'lst_price': record['price']
        }

    @mapping
    def default_code(self, record):
        return {'default_code': record['sku']}

    @mapping
    def weight(self, record):
        return {'weight': record['weight']}
