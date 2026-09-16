from datetime import datetime

from odoo import models, fields, api


class SoporteHelpHistory(models.Model):
    _name = 'soportehelp.history'
    _description = 'Actividad del Módulo Soporte y Ayuda'
    _rec_name = 'display_name'
    _order = 'timestamp desc'

    config_id = fields.Many2one('soportehelp.config', string='Configuración', ondelete='cascade')
    timestamp = fields.Datetime(string='Fecha', default=fields.Datetime.now, required=True)
    event_type = fields.Selection(
        [
            ('registration', 'Registro'),
            ('activation', 'Activación/Desactivación'),
            ('inventory', 'Inventario'),
            ('ticket', 'Ticket'),
            ('heartbeat', 'Heartbeat'),
            ('maintenance', 'Mantenimiento'),
            ('tamper', 'Cambio no autorizado'),
            ('version', 'Cambio de versión'),
        ],
        string='Tipo de evento',
        default='inventory',
    )
    module_name = fields.Char(string='Módulo')
    version_from = fields.Char(string='Versión desde')
    version_to = fields.Char(string='Versión hacia')
    message = fields.Text(string='Detalle')

    display_name = fields.Char(string='Referencia', compute='_compute_display_name')

    @api.depends('event_type', 'timestamp', 'module_name')
    def _compute_display_name(self):
        for record in self:
            label = dict(record._fields['event_type'].selection).get(record.event_type, record.event_type)
            mod = f" · {record.module_name}" if record.module_name else ''
            record.display_name = f"{record.timestamp} · {label}{mod}"