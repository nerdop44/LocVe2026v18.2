# -*- coding: utf-8 -*-
# Remake ING. Nerdo José Pulido Aguirre - Localización Venezolana (LocVe)

from odoo import models, _
from odoo.exceptions import UserError


class MoveActionPostAlertWizard(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        res = super(MoveActionPostAlertWizard, self).action_post()
        for record in self:
            if record.company_id.invoice_digital_tfhka and getattr(record, 'sequence_number', 0) > 1:
                previous_invoice = self.env["account.move"].search(
                    [
                        ("company_id", "=", record.company_id.id),
                        ("move_type", "=", record.move_type),
                        ("is_digitalized", "=", False),
                        ("state", "=", "posted"),
                        ("journal_id", "=", record.journal_id.id),
                        ("id", "!=", record.id),
                    ], order="id asc", limit=1, 
                )
                if previous_invoice and not previous_invoice.is_digitalized:
                    move_type = previous_invoice.move_type
                    if move_type == "out_invoice" and not getattr(previous_invoice, 'debit_origin_id', False):
                        _logger_msg = _("La factura anterior %s no ha sido digitalizada en TFHKA.") % (previous_invoice.name)
                    elif move_type == "out_refund":
                        _logger_msg = _("La nota de crédito anterior %s no ha sido digitalizada en TFHKA.") % (previous_invoice.name)
        return res
