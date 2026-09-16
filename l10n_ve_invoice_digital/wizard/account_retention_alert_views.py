# -*- coding: utf-8 -*-
# Remake ING. Nerdo José Pulido Aguirre - Localización Venezolana (LocVe)

from odoo import models, fields, _


class AccountRetentionAlertWizard(models.TransientModel):
    _name = 'account.retention.alert.wizard'
    _description = 'Alerta de Secuencia de Retención TFHKA (LocVe)'

    move_id = fields.Many2one('account.retention', string="Retención")
    message = fields.Text(string="Mensaje de Alerta")

    def action_confirm(self):
        document_type = self.env.context.get('document_type', '05')
        return self.move_id.with_context(account_retention_alert=True, document_type=document_type).generate_document_digital()
