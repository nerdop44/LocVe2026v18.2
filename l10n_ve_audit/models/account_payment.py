# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.su and self.env.user.has_group('l10n_ve_audit.group_fiscal_auditor'):
            raise UserError(_("Los auditores fiscales del SENIAT tienen acceso estrictamente de solo lectura."))
        return super(AccountPayment, self).create(vals_list)

    def write(self, vals):
        if not self.env.su and self.env.user.has_group('l10n_ve_audit.group_fiscal_auditor'):
            raise UserError(_("Los auditores fiscales del SENIAT tienen acceso estrictamente de solo lectura."))
        return super(AccountPayment, self).write(vals)

    def unlink(self):
        if not self.env.su and self.env.user.has_group('l10n_ve_audit.group_fiscal_auditor'):
            raise UserError(_("Los auditores fiscales del SENIAT tienen acceso estrictamente de solo lectura."))
        return super(AccountPayment, self).unlink()
