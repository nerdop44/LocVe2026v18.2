# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class L10nVeVoidControlWizard(models.TransientModel):
    _name = 'l10n_ve.void.control.wizard'
    _description = 'Asistente para Anulación de Número de Control'

    move_id = fields.Many2one('account.move', string="Factura/Nota de Crédito", required=True)
    journal_id = fields.Many2one('account.journal', string="Diario", related="move_id.journal_id", readonly=True)
    sequence_id = fields.Many2one('ir.sequence', string="Secuencia de Control", compute="_compute_sequence_id", readonly=True)
    next_control_number = fields.Char(string="Número de Control a Anular", compute="_compute_next_control_number", readonly=True)
    
    reason = fields.Selection([
        ('paper_jam', 'Atasco de Papel'),
        ('print_error', 'Falla de Impresión'),
        ('damaged', 'Papel Dañado/Roto'),
        ('other', 'Otros'),
    ], string="Motivo de Anulación", required=True, default='paper_jam')
    notes = fields.Text(string="Notas explicativas del incidente", required=True)

    @api.depends('move_id', 'journal_id')
    def _compute_sequence_id(self):
        for wizard in self:
            wizard.sequence_id = False
            if wizard.journal_id:
                if wizard.journal_id.series_correlative_sequence_id:
                    wizard.sequence_id = wizard.journal_id.series_correlative_sequence_id
                else:
                    # Buscar la secuencia global de formas libres si no tiene asignada
                    sequence = self.env["ir.sequence"].sudo().search(
                        [("code", "=", "invoice.correlative"), ("company_id", "=", self.env.company.id)],
                        limit=1
                    )
                    if sequence:
                        wizard.sequence_id = sequence

    @api.depends('sequence_id')
    def _compute_next_control_number(self):
        for wizard in self:
            wizard.next_control_number = _("No asignada o no disponible")
            if wizard.sequence_id:
                seq = wizard.sequence_id
                wizard.next_control_number = seq.get_next_char(seq.number_next_actual)

    def action_confirm_void(self):
        self.ensure_one()
        if not self.sequence_id:
            raise UserError(_("No hay una secuencia de control configurada para el diario de este documento."))

        # 1. Consumir el número real de la secuencia
        control_number = self.sequence_id.next_by_id(self.sequence_id.id)
        
        # 2. Registrar la anulación física
        void_record = self.env['l10n_ve.free_form.void'].sudo().create({
            'control_number': control_number,
            'journal_id': self.journal_id.id,
            'reason': self.reason,
            'notes': self.notes,
            'company_id': self.move_id.company_id.id,
        })

        # 3. Registrar el evento en el log de auditoría
        audit_details = (
            f"ANULACIÓN FÍSICA DE NÚMERO DE CONTROL. "
            f"Nro Control Anulado: {control_number}. "
            f"Diario: {self.journal_id.name}. "
            f"Motivo: {dict(self._fields['reason'].selection).get(self.reason)}. "
            f"Explicación del Operador: {self.notes}."
        )
        self.env['l10n_ve.audit.log'].log_event('control_void', self.move_id, audit_details)

        # 4. Enviar un mensaje en el chatter de la factura
        self.move_id.message_post(
            body=_(
                "<b>Número de Control Anulado:</b> Se registró la anulación física del número de control "
                "<b>%s</b> debido a: %s. Notas: %s"
            ) % (control_number, dict(self._fields['reason'].selection).get(self.reason), self.notes)
        )

        return {'type': 'ir.actions.act_window_close'}
