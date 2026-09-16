from odoo import models, fields, api
from odoo.exceptions import UserError


class SoporteHelpMaintenanceApply(models.TransientModel):
    _name = 'soportehelp.maintenance.apply'
    _description = 'Aplicar Pase de Mantenimiento'

    token = fields.Text(string='Token de Mantenimiento', required=True)
    note = fields.Text(string='Nota', readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        core = self.env['soportehelp.core']
        res['note'] = 'Ingrese el pase de mantenimiento emitido por el soporte para abrir una ventana temporal.'
        return res

    def action_apply(self):
        self.ensure_one()
        result = self.env['soportehelp.core'].apply_maintenance_token(self.token)
        if not result.get('ok'):
            raise UserError(
                "El pase no es válido: " + str(result.get('error', 'error desconocido'))
            )
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'soportehelp.config',
            'view_mode': 'form',
            'target': 'current',
        }