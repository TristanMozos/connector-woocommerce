# © 2009 Tech-Receptives Solutions Pvt. Ltd.
# © 2018 FactorLibre
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': 'WooCommerce Connector',
    'version': '11.0.1.0.0',
    'category': 'Connector',
    'author': "Tech Receptives,FactorLibre,Odoo Community Association (OCA)",
    'license': 'AGPL-3',
    'website': 'http://www.openerp.com',
    'depends': [
        'connector',
        'connector_ecommerce',
        'product_multi_category',
        'sale_stock'
    ],
    'installable': True,
    'auto_install': False,
    'data': [
        "data/connector_woocommerce_data.xml",
        "security/ir.model.access.csv",
        "views/backend_view.xml",
        "views/account_payment_mode_view.xml",
        "views/account_tax_view.xml",
        "views/product_view.xml"
    ],
    'external_dependencies': {
        'python': ['woocommerce'],
    },
    'application': True,
    "sequence": 3,
}
