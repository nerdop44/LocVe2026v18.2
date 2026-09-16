# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import datetime

class IgtfReportWizard(models.TransientModel):
    _name = "igtf.report.wizard"
    _description = "Reporte Consolidado IGTF SENIAT"

    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        required=True,
        default=lambda self: self.env.company,
    )
    date_from = fields.Date(
        string="Fecha Desde",
        required=True,
        default=lambda self: fields.Date.context_today(self).replace(day=1),
    )
    date_to = fields.Date(
        string="Fecha Hasta",
        required=True,
        default=lambda self: (fields.Date.context_today(self).replace(day=28) + datetime.timedelta(days=4)).replace(day=1) - datetime.timedelta(days=1),
    )
    declaration_ref = fields.Char(
        string="Nro. Planilla / Comprobante SENIAT",
        help="Referencia asignada a la declaración quincenal ante el portal del SENIAT",
    )
    declaration_status_filter = fields.Selection(
        selection=[
            ("all", "Todos"),
            ("pending", "Solo Pendientes por Declarar"),
            ("declared", "Solo Declarados"),
        ],
        string="Filtrar Estado Fiscal",
        default="all",
        required=True,
    )

    def _get_domain(self):
        self.ensure_one()
        domain = [
            ("company_id", "=", self.company_id.id),
            ("date", ">=", self.date_from),
            ("date", "<=", self.date_to),
            ("state", "in", ["in_process", "paid", "posted"]),
            "|", "|",
            ("is_igtf_on_foreign_exchange", "=", True),
            ("igtf_amount", ">", 0.0),
            ("journal_id.is_igtf", "=", True),
        ]
        if self.declaration_status_filter == "pending":
            domain.append(("igtf_declaration_status", "=", "pending"))
        elif self.declaration_status_filter == "declared":
            domain.append(("igtf_declaration_status", "in", ["declared", "paid"]))
        return domain

    def get_report_payments(self):
        if not self:
            return self.env["account.payment"]
        existing_self = self.exists()
        if not existing_self:
            return self.env["account.payment"].browse(self.ids).exists()
        payments = self.env["account.payment"]
        for wiz in existing_self:
            payments |= self.env["account.payment"].search(wiz._get_domain(), order="date asc, id asc")
        return payments

    def action_generate_report(self):
        payments = self.get_report_payments()
        d_from = min(self.mapped("date_from")) if self.mapped("date_from") else fields.Date.context_today(self)
        d_to = max(self.mapped("date_to")) if self.mapped("date_to") else fields.Date.context_today(self)
        
        view_id = self.env.ref("l10n_ve_igtf.view_igtf_consolidated_payment_tree", raise_if_not_found=False)
        
        res = {
            "name": _("Consolidado IGTF SENIAT (%s al %s)") % (d_from, d_to),
            "type": "ir.actions.act_window",
            "res_model": "account.payment",
            "view_mode": "list,form",
            "domain": [("id", "in", payments.ids)],
            "context": {
                "create": False,
                "delete": False,
            },
        }
        if view_id:
            res["views"] = [(view_id.id, "list"), (False, "form")]
        return res

    def action_print_pdf(self):
        return self.env.ref("l10n_ve_igtf.action_report_igtf_consolidated").report_action(self)

    def action_mark_as_declared(self):
        payments = self.get_report_payments()
        if not payments:
            raise UserError(_("No se encontraron pagos con IGTF para el período seleccionado."))
        
        ref = (self[:1].declaration_ref or "").strip() or _("DECL-IGTF-%s") % fields.Date.context_today(self).strftime("%Y%m%d")
        payments.write({
            "igtf_declaration_status": "declared",
            "igtf_declaration_ref": ref,
        })
        
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Declaración SENIAT Registrada"),
                "message": _("Se marcaron %d operaciones como DECLARADAS con la referencia: %s") % (len(payments), ref),
                "type": "success",
                "sticky": False,
            },
        }
