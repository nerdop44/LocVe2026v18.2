# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class L10nVeFreeFormVoid(models.Model):
    _name = 'l10n_ve.free_form.void'
    _description = 'Control de Números de Control Anulados/Dañados'
    _order = 'date desc, id desc'

    control_number = fields.Char(string="Número de Control Anulado", required=True, readonly=True)
    journal_id = fields.Many2one('account.journal', string="Diario", required=True, readonly=True)
    date = fields.Date(string="Fecha", default=fields.Date.context_today, required=True, readonly=True)
    user_id = fields.Many2one('res.users', string="Usuario", default=lambda self: self.env.user, required=True, readonly=True)
    company_id = fields.Many2one('res.company', string="Compañía", default=lambda self: self.env.company, required=True, readonly=True)
    reason = fields.Selection([
        ('paper_jam', 'Atasco de Papel'),
        ('print_error', 'Falla de Impresión'),
        ('damaged', 'Papel Dañado/Roto'),
        ('other', 'Otros'),
    ], string="Motivo de Anulación", required=True, default='paper_jam', readonly=True)
    notes = fields.Text(string="Notas adicionales", readonly=True)
