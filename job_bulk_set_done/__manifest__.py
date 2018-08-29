##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 FactorLibre (http://www.factorlibre.com)
#                       Ismael Calvo <ismael.calvo@factorlibre.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': 'Bulk Set Done',
    'version': '11.0.1.0.0',
    'category': 'Connector',
    'license': 'AGPL-3',
    'author': 'FactorLibre',
    'website': 'http://www.factorlibre.com',
    'depends': [
        'base',
        'connector'
    ],
    'demo': [],
    'data': [
        'wizard/change_job_change_state_view.xml'
    ],
    'installable': True,
}
