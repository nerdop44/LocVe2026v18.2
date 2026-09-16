from odoo import models, api, fields


class SoporteHelpModule(models.Model):
    _inherit = 'ir.module.module'

    def button_immediate_uninstall(self):
        self.ensure_one()
        from odoo.exceptions import UserError
        if self.name in ('soportehelp', 'soportehelp_account'):
            config = self.env['soportehelp.config'].sudo()._get_or_create()
            if config.enforcement_enabled:
                raise UserError(
                    'El módulo Soporte y Ayuda es requisito del sistema. '
                    'No puede desinstalarse mientras esté activo. '
                    'Desactive primero el control desde el backend o contacte al soporte.'
                )
        return super().button_immediate_uninstall()