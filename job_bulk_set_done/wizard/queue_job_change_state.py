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

from openerp import models, fields, api


class QueueJobChangeState(models.TransientModel):
    _name = 'queue.job.change_state'
    _description = 'Queue Job Change State'

    @api.multi
    def _get_job_ids(self):
        print("_get_job_ids")
        context = self.env.context
        res = []
        if context.get('active_model') == 'queue.job':
            res = context.get('active_ids', [])
        print("res:", res)
        return res

    job_ids = fields.Many2many('queue.job', string='Jobs', default=_get_job_ids)

    @api.multi
    def set_done_jobs(self):
        # active_ids = self.env.context.get('active_ids', False)
        print("self.job_ids:", self.job_ids)
        if self.job_ids:
            self.job_ids.button_done()
        return {'type': 'ir.actions.act_window_close'}
