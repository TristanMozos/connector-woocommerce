# © 2018 FactorLibre - Álvaro Marcos <alvaro.marcos@factorlibre.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Import sales between dates",
    "depends":
        [
            "base",
            "connector_woocommerce"
        ],
    "version": "11.0.1.0.0",
    "author": "FactorLibre",
    "applicattion": False,
    "installable": True,
    "data":
        [
            "wizard/import_between_dates.xml",
            "views/backend_view.xml"

        ],
    "category": ""
}
