# -*- coding: utf-8 -*-
# Remake ING. Nerdo José Pulido Aguirre - Localización Venezolana (LocVe)

from odoo import api, models, _
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)


FREE_FORM_REPORT_NAMES = [
    'l10n_ve_invoice.template_invoice_free_form_l10n_ve_invoice',
    'l10n_ve_invoice.report_freeform_vef',
    'l10n_ve_invoice.report_freeform_usd',
]


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        report = self._get_report(report_ref)
        if report.report_name in FREE_FORM_REPORT_NAMES:
            _logger.info("FREE_FORM_RESTRICTION: report=%s, res_ids=%s", report.report_name, res_ids)
            if res_ids:
                first_record = self.env[report.model].browse(res_ids[0])
                if first_record.company_id.ocultar_forma_libre_digital:
                    _logger.warning("FREE_FORM_RESTRICTION: BLOCKED report=%s for company=%s",
                                    report.report_name, first_record.company_id.name)
                    raise UserError(_(
                        "La impresión en Forma Libre está deshabilitada. "
                        "Use facturación digital (TFHKA) o Máquina Fiscal."
                    ))
        return super()._render_qweb_pdf(report_ref, res_ids=res_ids, data=data)

    def get_valid_action_reports(self, model, record_ids):
        valid_ids = super().get_valid_action_reports(model, record_ids)
        if valid_ids and record_ids:
            records = self.env[model].browse(record_ids[:1])
            company = records[:1].company_id if records else self.env.company
            if company and getattr(company, 'ocultar_forma_libre_digital', False):
                free_form_reports = self.search([('report_name', 'in', FREE_FORM_REPORT_NAMES)])
                valid_ids = [rid for rid in valid_ids if rid not in free_form_reports.ids]
        return valid_ids


class IrActions(models.Model):
    _inherit = 'ir.actions.actions'

    @api.model
    def get_bindings(self, model_name):
        result = super().get_bindings(model_name)
        if model_name == 'account.move' and 'report' in result:
            company = self.env.company
            if getattr(company, 'ocultar_forma_libre_digital', False):
                free_form_reports = self.env['ir.actions.report'].sudo().search([
                    ('report_name', 'in', FREE_FORM_REPORT_NAMES)
                ])
                ff_ids = set(free_form_reports.ids)
                original_count = len(result['report'])
                result['report'] = [b for b in result['report'] if b.get('id') not in ff_ids]
                if len(result['report']) < original_count:
                    _logger.info("FREE_FORM_RESTRICTION: Hidden %d free form reports from Print menu",
                                 original_count - len(result['report']))
        return result
