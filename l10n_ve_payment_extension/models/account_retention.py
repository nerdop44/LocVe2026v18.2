from odoo import api, models, fields, Command, _
from datetime import datetime
from odoo.exceptions import UserError, ValidationError
from ..utils.utils_retention import load_retention_lines, search_invoices_with_taxes
from collections import defaultdict
import json
from odoo.tools.float_utils import float_round
import logging

_logger = logging.getLogger(__name__)


class AccountRetention(models.Model):
    _name = "account.retention"
    _description = "Retention"
    _check_company_auto = True

    company_currency_id = fields.Many2one(
        "res.currency",
        compute="_compute_currency_info",
        store=True,
        readonly=False,
        precompute=True,
    )
    foreign_currency_id = fields.Many2one(
        "res.currency",
        compute="_compute_currency_info",
        store=True,
        readonly=False,
        precompute=True,
    )
    base_currency_is_vef = fields.Boolean(
        compute="_compute_currency_info",
        store=True,
        precompute=True,
    )


    def _get_retention_currencies(self):
        """
        Determina de forma dinámica las monedas base, alterna, fiscal (VEF/VES) y extranjera (USD).
        """
        company = self.company_id or self.env.company
        currency_base = company.currency_id
        currency_alternate = getattr(company, 'currency_id_dif', self.env['res.currency'])

        # Detectar moneda fiscal de Venezuela (VES/VEF)
        currency_tax = self.env['res.currency']
        if currency_base.name in ('VES', 'VEF'):
            currency_tax = currency_base
        elif currency_alternate and currency_alternate.name in ('VES', 'VEF'):
            currency_tax = currency_alternate
        else:
            # Buscar en monedas activas de la BD
            currency_tax = self.env['res.currency'].search([
                ('name', 'in', ('VES', 'VEF')),
                ('active', '=', True)
            ], limit=1)
            # Fallbacks a referencias base
            if not currency_tax:
                currency_tax = self.env.ref('base.VES', raise_if_not_found=False)
            if not currency_tax:
                currency_tax = self.env.ref('base.VEF', raise_if_not_found=False)
            if not currency_tax:
                currency_tax = currency_base

        # Detectar moneda extranjera de referencia (ej. USD)
        currency_foreign = self.env['res.currency']
        if currency_base != currency_tax:
            currency_foreign = currency_base
        elif currency_alternate and currency_alternate != currency_tax:
            currency_foreign = currency_alternate
        else:
            currency_foreign = self.env['res.currency'].search([
                ('name', '=', 'USD'),
                ('active', '=', True)
            ], limit=1)
            if not currency_foreign:
                currency_foreign = self.env.ref('base.USD', raise_if_not_found=False)

        return currency_base, currency_alternate, currency_tax, currency_foreign

    @api.depends('company_id')
    def _compute_currency_info(self):
        for record in self:
            base, alternate, tax, foreign = record._get_retention_currencies()
            record.company_currency_id = base.id if base else False
            record.foreign_currency_id = tax.id if tax else False
            record.base_currency_is_vef = (base == tax) if base and tax else False
    use_today_rate = fields.Boolean(
        string="Utilizar Tasa de Hoy:",
        default=False,
        help="Si se marca, se utilizará la tasa de cambio de hoy en lugar de la tasa de la factura."
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
    )
    name = fields.Char(
        "Description",
        size=64,
        help="Description of the withholding voucher",
    )
    code = fields.Char(
        size=32,
        help="Code of the withholding voucher",
    )
    state = fields.Selection(
        [("draft", "Draft"), ("emitted", "Emitted"), ("cancel", "Cancelled")],
        index=True,
        default="draft",
        help="Status of the withholding voucher",
    )
    type_retention = fields.Selection(
        [
            ("iva", "IVA"),
            ("islr", "ISLR"),
            ("municipal", "Municipal"),
        ],
        required=True,
    )
    type = fields.Selection(
        [
            ("out_invoice", "Out invoice"),
            ("in_invoice", "In invoice"),
            ("out_refund", "Out refund"),
            ("in_refund", "In refund"),
            ("out_debit", "Out debit"),
            ("in_debit", "In debit"),
            ("out_contingence", "Out contingence"),
            ("in_contingence", "In contingence"),
        ],
        "Type retention",
        help="Tipo del Comprobante",
        required=True,
        readonly=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        "Social reason",
        required=True,
        help="Social reason",
    )
    number = fields.Char("Voucher Number")
    correlative = fields.Char(readonly=True)
    date = fields.Date(
        "Voucher Date",
        help="Date of issuance of the withholding voucher by the external party.",
    )
    date_accounting = fields.Date(
        "Accounting Date",
        help=(
            "Date of arrival of the document and date to be used to make the accounting record."
            " Keep blank to use current date."
        ),
    )
    allowed_lines_move_ids = fields.Many2many(
        "account.move",
        compute="_compute_allowed_lines_move_ids",
        help=(
            "Technical field to store the allowed move types for the ISLR retention lines. This is"
            " used to filter the moves that can be selected in the ISLR retention lines."
        ),
    )

    retention_line_ids = fields.One2many(
        "account.retention.line",
        "retention_id",
        "retention line",
        help="Retentions",
    )

    esNegativo = fields.Boolean(
        string="Comprobante Negativo",
        default=False,
        copy=False,
        help="Indica si este comprobante de retención es un comprobante negativo (ajuste/reverso). "
             "Se envía con EsNegativo=true en el payload TFHKA.",
    )
    original_retention_id = fields.Many2one(
        "account.retention",
        string="Retención Original",
        copy=False,
        help="Referencia a la retención original cuando este comprobante es un ajuste negativo.",
    )

    code_visible = fields.Boolean(related="company_id.code_visible")

    payment_ids = fields.One2many(
        "account.payment",
        "retention_id",
        help="Payments",
    )

    total_invoice_amount = fields.Float(
        string="Taxable Income",
        compute="_compute_totals",
        help="Taxable Income Total",
        store=True,
    )
    total_iva_amount = fields.Float(
        string="Total IVA", compute="_compute_totals", store=True
    )
    total_retention_amount = fields.Float(
        compute="_compute_totals",
        store=True,
        help="Retained Amount Total",
    )

    foreign_total_invoice_amount = fields.Float(
        string="Total Facturado (Bs.)",
        compute="_compute_totals",
        help="Total base imponible en VEF",
        store=True,
    )
    foreign_total_iva_amount = fields.Float(
        string="Total IVA (Bs.)", compute="_compute_totals", store=True
    )
    foreign_total_retention_amount = fields.Float(
        string="Total Retenido (Bs.)",
        compute="_compute_totals",
        store=True,
        help="Total monto retenido en VEF",
    )
    original_lines_per_invoice_counter = fields.Char(
        help=(
            "Technical field to store the quantity of retention lines per invoice before the user"
            " changes them. This is used to know if the user has deleted the retention lines when"
            " the invoice is changed, in order to delete all the other lines of the same invoice"
            " that the one that just has been deleted."
        )
    )

    @api.depends("type", "partner_id")
    def _compute_allowed_lines_move_ids(self):
        """
        Computes the allowed move types for the moves of the retention lines.

        If the retention is of type "in_invoice", the allowed move types are "in_invoice" and
        "in_refund". If the retention is of type "out_invoice", the allowed move types are
        "out_invoice" and "out_refund".

        This is used to filter the moves that can be selected in the retention lines for each type
        of retention (ISLR and municipal).
        """
        for retention in self:
            allowed_types = (
                ("in_invoice", "in_refund")
                if retention.type == "in_invoice"
                else ("out_invoice", "out_refund")
            )

            domain = [
                ("company_id", "=", self.env.company.id),
                ("state", "=", "posted"),
                ("partner_id", "=", retention.partner_id.id),
                ("move_type", "in", allowed_types),
            ]

            retention.allowed_lines_move_ids = self.env["account.move"].search(domain)

    @api.depends(
        "retention_line_ids.invoice_amount",
        "retention_line_ids.iva_amount",
        "retention_line_ids.retention_amount",
        "retention_line_ids.foreign_invoice_amount",
        "retention_line_ids.foreign_iva_amount",
        "retention_line_ids.foreign_retention_amount",
    )
    def _compute_totals(self):
        for retention in self:
            retention.total_invoice_amount = 0
            retention.total_iva_amount = 0
            retention.total_retention_amount = 0
            retention.foreign_total_invoice_amount = 0
            retention.foreign_total_iva_amount = 0
            retention.foreign_total_retention_amount = 0

            for line in retention.retention_line_ids:
                if line.move_id.move_type in ("in_refund", "out_refund"):
                    retention.total_invoice_amount -= float_round(
                        line.invoice_amount,
                        precision_digits=retention.company_currency_id.decimal_places,
                    )
                    retention.total_iva_amount -= float_round(
                        line.iva_amount,
                        precision_digits=retention.company_currency_id.decimal_places,
                    )
                    retention.total_retention_amount -= float_round(
                        line.retention_amount,
                        precision_digits=retention.company_currency_id.decimal_places,
                    )
                    retention.foreign_total_invoice_amount -= float_round(
                        line.foreign_invoice_amount,
                        precision_digits=retention.foreign_currency_id.decimal_places,
                    )
                    retention.foreign_total_iva_amount -= float_round(
                        line.foreign_iva_amount,
                        precision_digits=retention.foreign_currency_id.decimal_places,
                    )
                    retention.foreign_total_retention_amount -= float_round(
                        line.foreign_retention_amount,
                        precision_digits=retention.foreign_currency_id.decimal_places,
                    )
                else:
                    retention.total_invoice_amount += float_round(
                        line.invoice_amount,
                        precision_digits=retention.company_currency_id.decimal_places,
                    )
                    retention.total_iva_amount += float_round(
                        line.iva_amount,
                        precision_digits=retention.company_currency_id.decimal_places,
                    )
                    retention.total_retention_amount += float_round(
                        line.retention_amount,
                        precision_digits=retention.company_currency_id.decimal_places,
                    )
                    retention.foreign_total_invoice_amount += float_round(
                        line.foreign_invoice_amount,
                        precision_digits=retention.foreign_currency_id.decimal_places,
                    )
                    retention.foreign_total_iva_amount += float_round(
                        line.foreign_iva_amount,
                        precision_digits=retention.foreign_currency_id.decimal_places,
                    )
                    retention.foreign_total_retention_amount += float_round(
                        line.foreign_retention_amount,
                        precision_digits=retention.foreign_currency_id.decimal_places,
                    )

    @api.onchange("partner_id")
    def onchange_partner_id(self):
        """
        Load retention lines from invoices with taxes when the partner changes for IVA retentions
        that are not posted.
        """
        self._validate_retention_journals()
        for retention in self.filtered(
            lambda r: (r.state, r.type_retention) == ("draft", "iva") and r.partner_id
        ):
            if retention.type == "in_invoice":
                result = retention._load_retention_lines_for_iva_supplier_retention()
            else:
                result = retention._load_retention_lines_for_iva_customer_retention()
            return result

    def _load_retention_lines_for_iva_supplier_retention(self):
        self.ensure_one()
        self.date_accounting = fields.Date.context_today(self)
        search_domain = [
            ("company_id", "=", self.company_id.id),
            ("partner_id", "=", self.partner_id.id),
            ("state", "=", "posted"),
            ("move_type", "in", ("in_refund", "in_invoice")),
            ("amount_residual", ">", 0),
        ]
        invoices_with_taxes = search_invoices_with_taxes(
            self.env["account.move"], search_domain
        ).filtered(
            lambda i: not any(
                i.retention_iva_line_ids.filtered(
                    lambda l: l.state in ("draft", "emitted")
                )
            )
        )
        if not any(invoices_with_taxes):
            raise UserError(
                _("There are no invoices with taxes to be retained for the supplier.")
            )
        self.clear_retention()
        lines = load_retention_lines(invoices_with_taxes, self.env["account.retention"])

        lines_per_invoice_counter = defaultdict(int)
        for line in lines:
            lines_per_invoice_counter[str(line[2]["move_id"])] += 1

        return {
            "value": {
                "retention_line_ids": lines,
                "original_lines_per_invoice_counter": json.dumps(
                    lines_per_invoice_counter
                ),
            }
        }

    def _load_retention_lines_for_iva_customer_retention(self):
        self.ensure_one()
        search_domain = [
            ("company_id", "=", self.company_id.id),
            ("partner_id", "=", self.partner_id.id),
            ("state", "=", "posted"),
            ("move_type", "in", ("out_refund", "out_invoice")),
            ("amount_residual", ">", 0),
            ("name", "!=", False),  # Añadir esta línea
        ]
        invoices_with_taxes = search_invoices_with_taxes(
            self.env["account.move"], search_domain
        ).filtered(
            lambda i: not any(
                i.retention_iva_line_ids.filtered(
                    lambda l: l.state in ("draft", "emitted")
                )
            )
        )
        if not any(invoices_with_taxes):
            raise UserError(
                _("There are no invoices with taxes to be retained for the customer.")
            )
        self.clear_retention()
        lines = load_retention_lines(invoices_with_taxes, self.env["account.retention"])

        lines_per_invoice_counter = defaultdict(int)
        for line in lines:
            lines_per_invoice_counter[str(line[2]["move_id"])] += 1

        return {
            "value": {
                "retention_line_ids": lines,
                "original_lines_per_invoice_counter": json.dumps(
                    lines_per_invoice_counter
                ),
            }
        }

    def _validate_retention_journals(self):
        """
        Validate that the company has the journals configured for the retention type.
        """
        for retention in self:
            # IVA
            if (retention.type_retention, retention.type) == (
                "iva",
                "in_invoice",
            ) and not self.env.company.iva_supplier_retention_journal_id:
                raise UserError(
                    _(
                        "The company must have a supplier IVA retention journal configured."
                    )
                )
            if (retention.type_retention, retention.type) == (
                "iva",
                "out_invoice",
            ) and not self.env.company.iva_customer_retention_journal_id:
                raise UserError(
                    _(
                        "The company must have a customer IVA retention journal configured."
                    )
                )
            # ISLR
            if (retention.type_retention, retention.type) == (
                "islr",
                "in_invoice",
            ) and not self.env.company.islr_supplier_retention_journal_id:
                raise UserError(
                    _(
                        "The company must have a supplier ISLR retention journal configured."
                    )
                )
            if (retention.type_retention, retention.type) == (
                "islr",
                "out_invoice",
            ) and not self.env.company.islr_customer_retention_journal_id:
                raise UserError(
                    _(
                        "The company must have a customer ISLR retention journal configured."
                    )
                )
            # Municipal
            if (retention.type_retention, retention.type) == (
                "municipal",
                "in_invoice",
            ) and not self.env.company.municipal_supplier_retention_journal_id:
                raise UserError(
                    _(
                        "The company must have a supplier municipal retention journal configured."
                    )
                )
            if (retention.type_retention, retention.type) == (
                "municipal",
                "out_invoice",
            ) and not self.env.company.municipal_customer_retention_journal_id:
                raise UserError(
                    _(
                        "The company must have a customer municipal retention journal configured."
                    )
                )

    def clear_retention(self):
        """
        Clear retention lines and payments.
        """
        self.ensure_one()
        self.update(
            {
                "retention_line_ids": (
                    Command.clear()
                    if any(
                        isinstance(id, models.NewId)
                        for id in self.retention_line_ids.ids
                    )
                    else False
                ),
            }
        )



    @api.onchange("retention_line_ids")
    def onchange_retention_line_ids(self):
        """
        On the IVA supplier retention when a line is deleted, delete all the others lines that have
        the same invoice.
        """
        for retention in self.filtered(
            lambda r: (r.type_retention, r.state) == ("iva", "draft") and r.partner_id
        ):
            # Cargar original_lines_per_invoice_counter, asegurando que sea un diccionario,
            # y si está vacío o es None, inicializarlo como un defaultdict.
            original_lines_per_invoice_counter_raw = retention.original_lines_per_invoice_counter
            if original_lines_per_invoice_counter_raw:
                original_lines_per_invoice_counter = defaultdict(int, json.loads(original_lines_per_invoice_counter_raw))
            else:
                original_lines_per_invoice_counter = defaultdict(int)

            lines_per_invoice_counter = defaultdict(int)
            for line in retention.retention_line_ids:
                # Nos aseguramos de que line.move_id sea un registro válido antes de intentar acceder a su .id
                if line.move_id:
                    lines_per_invoice_counter[str(line.move_id.id)] += 1

            # Almacenar las líneas a eliminar en un recordset separado para evitar
            # modificar el recordset mientras se itera sobre él, lo que puede causar problemas.
            lines_to_remove = self.env['account.retention.line'] # Inicializar un recordset vacío

            for line in retention.retention_line_ids:
                # Solo procesamos líneas que tienen un move_id válido
                if line.move_id:
                    # Obtener la cuenta original para esta factura, por defecto 0 si no se encuentra
                    original_count = original_lines_per_invoice_counter.get(str(line.move_id.id), 0)
                    # Obtener la cuenta actual para esta factura
                    current_count = lines_per_invoice_counter[str(line.move_id.id)]

                    # === MODIFICACIÓN CLAVE AQUÍ ===
                    # Solo eliminamos líneas si la cuenta actual es *menor que* la cuenta original.
                    # Esto indica una eliminación.
                    if current_count < original_count:
                        lines_to_remove |= line # Añadir la línea al conjunto de líneas a eliminar

            # Eliminar todas las líneas identificadas de una vez después del bucle
            retention.retention_line_ids -= lines_to_remove

            return {
                "value": {
                    "original_lines_per_invoice_counter": json.dumps(
                        lines_per_invoice_counter
                    )
                }
            }

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        res._safe_create_payments()
        return res

    def write(self, vals):
        res = super().write(vals)
        self._safe_create_payments()
        return res

    def action_generate_payment(self):
        # Desactivado a favor de Opción A (Pago al Aprobar)
        pass

    def unlink(self):
        for record in self:
            if record.state == "emitted":
                raise ValidationError(
                    _(
                        "You cannot delete a hold linked to a posted entry. It is necessary to cancel the retention before being deleted"
                    )
                )
        return super().unlink()

    def _safe_create_payments(self):
        """
        Crea o actualiza los pagos en borrador para retenciones IVA, ISLR y Municipales.
        Para IVA: sincroniza el pago por factura (igual que ISLR).
        Para ISLR: sincroniza por concepto+factura via _create_islr_payments_on_draft.
        Para Municipal: sincroniza por factura via _sync_municipal_payments_on_draft.
        """
        for retention in self:
            journals = {
                ("iva", "in_invoice"): retention.company_id.iva_supplier_retention_journal_id,
                ("iva", "out_invoice"): retention.company_id.iva_customer_retention_journal_id,
                ("islr", "in_invoice"): retention.company_id.islr_supplier_retention_journal_id,
                ("islr", "out_invoice"): retention.company_id.islr_customer_retention_journal_id,
                ("municipal", "in_invoice"): retention.company_id.municipal_supplier_retention_journal_id,
                ("municipal", "out_invoice"): retention.company_id.municipal_customer_retention_journal_id,
            }
            journal = journals.get((retention.type_retention, retention.type))
            if not journal:
                continue

            # Las retenciones contabilizadas no deben recrear pagos
            if retention.state != "draft":
                continue

            # Sin líneas de retención, no hay nada que pagar
            if not retention.retention_line_ids:
                continue

            # LÓGICA ISLR: sincronizar por concepto+factura
            if retention.type_retention == "islr":
                retention._create_islr_payments_on_draft()
                continue

            # LÓGICA IVA: sincronizar un pago por cada factura agrupada
            if retention.type_retention == "iva":
                retention._sync_iva_payments_on_draft()
                continue

            # LÓGICA MUNICIPAL: sincronizar un pago por factura
            if retention.type_retention == "municipal":
                retention._sync_municipal_payments_on_draft()
                continue

    def _sync_municipal_payments_on_draft(self):
        """
        Sincroniza los pagos municipales en borrador.
        Agrupa las líneas de retención por factura y crea/actualiza un pago por grupo.
        """
        self.ensure_one()
        Payment = self.env["account.payment"]
        Rate = self.env["res.currency.rate"]

        journal = (
            self.env.company.municipal_supplier_retention_journal_id
            if self.type == "in_invoice"
            else self.env.company.municipal_customer_retention_journal_id
        )
        if not journal:
            return

        # Odoo 18 requiere payment_method_line_id
        payment_method_line = journal.outbound_payment_method_line_ids[:1] if self.type == "in_invoice" else journal.inbound_payment_method_line_ids[:1]
        if not payment_method_line:
             payment_method_line = journal._get_available_payment_method_lines(
                 "outbound" if self.type == "in_invoice" else "inbound"
             )[:1]

        partner_type = "supplier" if self.type in ("in_invoice", "in_refund") else "customer"

        # Agrupar líneas por factura
        lines_by_move = defaultdict(lambda: self.env["account.retention.line"])
        for line in self.retention_line_ids:
            if line.move_id:
                lines_by_move[line.move_id] += line

        existing_payments = {}
        for payment in self.payment_ids:
            linked_moves = payment.retention_line_ids.mapped("move_id")
            for move in linked_moves:
                existing_payments[move] = payment

        payments_to_keep = self.env["account.payment"]

        for move, lines in lines_by_move.items():
            if move.move_type in ("in_invoice", "out_refund"):
                payment_type = "outbound"
            else:
                payment_type = "inbound"

            if move.move_type in ("in_refund", "out_refund"):
                payment_type = "inbound" if partner_type == "supplier" else "outbound"

            lines._compute_line_amounts()
            _, _, currency_vef, _ = self._get_retention_currencies()
            total_retention_vef = sum(lines.mapped("foreign_retention_amount"))
            foreign_rate = lines[0].foreign_currency_rate if lines else 1.0

            if currency_vef.is_zero(total_retention_vef):
                continue

            pm_account_id = payment_method_line.payment_account_id.id if payment_method_line and hasattr(payment_method_line, 'payment_account_id') else False
            outstanding_account_id = pm_account_id or journal.default_account_id.id

            payment_vals = {
                "retention_id": self.id,
                "partner_id": self.partner_id.id,
                "partner_type": partner_type,
                "payment_type_retention": "municipal",
                "is_retention": True,
                "journal_id": journal.id,
                "payment_type": payment_type,
                "payment_method_line_id": payment_method_line.id if payment_method_line else False,
                "outstanding_account_id": outstanding_account_id,
                "foreign_rate": foreign_rate,
                "tax_today": foreign_rate,
                "currency_id": currency_vef.id,
                "amount": total_retention_vef,
                "date": self.date_accounting or fields.Date.context_today(self),
                "retention_line_ids": [(6, 0, lines.ids)],
            }

            payment = existing_payments.get(move)
            if payment and payment.state == "draft":
                payment.write(payment_vals)
                if hasattr(payment, 'foreign_inverse_rate'):
                    payment.write({
                        "tax_today": payment.foreign_rate or foreign_rate or 1.0,
                        "foreign_inverse_rate": Rate.compute_inverse_rate(payment.foreign_rate or foreign_rate or 1.0)
                    })
            elif not payment:
                payment = Payment.create(payment_vals)
                if hasattr(payment, 'foreign_inverse_rate'):
                    payment.write({
                        "tax_today": payment.foreign_rate or foreign_rate or 1.0,
                        "foreign_inverse_rate": Rate.compute_inverse_rate(payment.foreign_rate or foreign_rate or 1.0)
                    })
            else:
                payments_to_keep |= payment
                continue

            lines.write({"payment_id": payment.id})
            payments_to_keep |= payment

        payments_to_remove = self.payment_ids.filtered(
            lambda p: p not in payments_to_keep and p.state == "draft"
        )
        if payments_to_remove:
            payments_to_remove.unlink()

        return payments_to_keep

    def _sync_iva_payments_on_draft(self):
        """
        Sincroniza los pagos IVA en borrador.
        Agrupa las líneas de retención por factura y crea/actualiza un pago por grupo.
        """
        self.ensure_one()
        Payment = self.env["account.payment"]
        Rate = self.env["res.currency.rate"]

        journal = (
            self.env.company.iva_supplier_retention_journal_id
            if self.type == "in_invoice"
            else self.env.company.iva_customer_retention_journal_id
        )
        if not journal:
            return

        # Odoo 18 requiere payment_method_line_id
        payment_method_line = journal.outbound_payment_method_line_ids[:1] if self.type == "in_invoice" else journal.inbound_payment_method_line_ids[:1]
        if not payment_method_line:
             # Fallback simple
             payment_method_line = journal._get_available_payment_method_lines(
                 "outbound" if self.type == "in_invoice" else "inbound"
             )[:1]

        partner_type = "supplier" if self.type in ("in_invoice", "in_refund") else "customer"

        # Agrupar líneas por factura
        lines_by_move = defaultdict(lambda: self.env["account.retention.line"])
        for line in self.retention_line_ids:
            if line.move_id:
                lines_by_move[line.move_id] += line

        existing_payments = {}
        for payment in self.payment_ids:
            linked_moves = payment.retention_line_ids.mapped("move_id")
            for move in linked_moves:
                existing_payments[move] = payment

        payments_to_keep = self.env["account.payment"]

        for move, lines in lines_by_move.items():
            if move.move_type in ("in_invoice", "out_refund"):
                payment_type = "outbound"
            else:
                payment_type = "inbound"

            if move.move_type in ("in_refund", "out_refund"):
                payment_type = "inbound" if partner_type == "supplier" else "outbound"

            # Moneda del pago y conciliación limpia con la factura
            lines._compute_line_amounts()
            _, _, currency_vef, _ = self._get_retention_currencies()
            total_retention_vef = sum(lines.mapped("foreign_retention_amount"))
            total_retention_usd = sum(lines.mapped("retention_amount"))
            foreign_rate = lines[0].foreign_currency_rate if lines else 1.0

            if currency_vef.is_zero(total_retention_vef):
                continue

            pay_currency = move.currency_id if (move and move.currency_id) else currency_vef
            pay_amount = total_retention_usd if pay_currency == self.company_id.currency_id else total_retention_vef

            # Odoo 18: las cuentas outstanding suelen estar en la payment_method_line o usar la default del diario
            pm_account_id = payment_method_line.payment_account_id.id if payment_method_line and hasattr(payment_method_line, 'payment_account_id') else False
            
            outstanding_account_id = pm_account_id or journal.default_account_id.id

            payment_vals = {
                "retention_id": self.id,
                "partner_id": self.partner_id.id,
                "partner_type": partner_type,
                "payment_type_retention": "iva",
                "is_retention": True,
                "journal_id": journal.id,
                "payment_type": payment_type,
                "payment_method_line_id": payment_method_line.id if payment_method_line else False,
                "outstanding_account_id": outstanding_account_id,
                "foreign_rate": foreign_rate,
                "tax_today": foreign_rate,
                "date": self.date_accounting or fields.Date.context_today(self),
                "retention_line_ids": [(6, 0, lines.ids)],
            }

            payment = existing_payments.get(move)
            if payment and payment.state == "draft":
                payment.write(payment_vals)
                if hasattr(payment, 'foreign_inverse_rate'):
                    payment.write({
                        "tax_today": payment.foreign_rate or foreign_rate or 1.0,
                        "foreign_inverse_rate": Rate.compute_inverse_rate(payment.foreign_rate or foreign_rate or 1.0)
                    })
            elif not payment:
                payment = Payment.create(payment_vals)
                if hasattr(payment, 'foreign_inverse_rate'):
                    payment.write({
                        "tax_today": payment.foreign_rate or foreign_rate or 1.0,
                        "foreign_inverse_rate": Rate.compute_inverse_rate(payment.foreign_rate or foreign_rate or 1.0)
                    })
            else:
                payments_to_keep |= payment
                continue

            lines.write({"payment_id": payment.id})
            payments_to_keep |= payment

        payments_to_remove = self.payment_ids.filtered(
            lambda p: p not in payments_to_keep and p.state == "draft"
        )
        if payments_to_remove:
            payments_to_remove.unlink()

        return payments_to_keep



#    # Bloque de código a REEMPLAZAR (buscar _safe_create_payments en tu archivo)
## =========================================================================

#    def _safe_create_payments(self):
#        """
#        Versión segura para crear pagos que no modifica movimientos publicados.
#        Ahora incluye lógica de desviación para ISLR (borrador), replicando el flujo de IVA.
#        """
#        for retention in self:
#            # 1. El municipal no crea pagos automáticos. Salto inmediato.
#            if retention.type_retention == "municipal":
#                continue
                
#            # 2. Las retenciones contabilizadas (emitted) no deben crear/recrear pagos.
#            if retention.state != 'draft':
#                continue
                
#            # 3. LÓGICA ISLR: Siempre se llama para recrear/actualizar en borrador si hay cambios en líneas.
#            if retention.type_retention == "islr":
#                retention._create_islr_payments_on_draft()
#                continue
            
#            # 4. LÓGICA IVA: Solo se crea si es IVA y *NO* tiene pagos (mantenemos la lógica original de IVA).
#            if retention.type_retention == "iva" and not retention.payment_ids:
#                payment_vals = {
#                    "retention_id": retention.id,
#                    "partner_id": retention.partner_id.id,
#                    "payment_type_retention": "iva",
#                    "is_retention": True,
#                    "currency_id": self.env.user.company_id.currency_id.id,
#                }        

#                def account_retention_line_empty_recordset():
#                    return self.env["account.retention.line"]

#                if retention.type == "in_invoice":
#                    retention._create_payments_for_iva_supplier(
#                        payment_vals, account_retention_line_empty_recordset
#                    )
#                if retention.type == "out_invoice":
#                    retention._create_payments_for_iva_customer(
#                        payment_vals, account_retention_line_empty_recordset
#                    )


    def _create_payments_for_iva_supplier(
        self, payment_vals, account_retention_line_empty_recordset
    ):
        Payment = self.env["account.payment"]
        Rate = self.env["res.currency.rate"]
        payment_vals["partner_type"] = "supplier"
        payment_vals[
            "journal_id"
        ] = self.env.company.iva_supplier_retention_journal_id.id
        in_refund_lines = self.retention_line_ids.filtered(
            lambda l: l.move_id.move_type == "in_refund"
        )
        in_invoice_lines = self.retention_line_ids.filtered(
            lambda l: l.move_id.move_type == "in_invoice"
        )

        in_refunds_dict = defaultdict(account_retention_line_empty_recordset)
        in_invoices_dict = defaultdict(account_retention_line_empty_recordset)

        for line in in_refund_lines:
            in_refunds_dict[line.move_id] += line
        for line in in_invoice_lines:
            in_invoices_dict[line.move_id] += line

        for lines in in_refunds_dict.values():
            payment_vals["payment_method_id"] = (
                self.env.ref("account.account_payment_method_manual_in").id,
            )
            payment_vals["payment_type"] = "inbound"
            payment_vals["foreign_rate"] = lines[0].foreign_currency_rate
            payment = Payment.create(payment_vals)
            payment.update(
                {
                    "foreign_inverse_rate": Rate.compute_inverse_rate(
                        payment.foreign_rate
                    )
                }
            )
            lines.write({"payment_id": payment.id})
            payment.compute_retention_amount_from_retention_lines()
        for lines in in_invoices_dict.values():
            payment_vals["payment_method_id"] = (
                self.env.ref("account.account_payment_method_manual_out").id,
            )
            payment_vals["payment_type"] = "outbound"
            payment_vals["foreign_rate"] = lines[0].foreign_currency_rate
            payment = Payment.create(payment_vals)
            payment.update(
                {
                    "foreign_inverse_rate": Rate.compute_inverse_rate(
                        payment.foreign_rate
                    )
                }
            )
            lines.write({"payment_id": payment.id})
            payment.compute_retention_amount_from_retention_lines()

    def _create_payments_for_iva_customer(
        self, payment_vals, account_retention_line_empty_recordset
    ):
        Payment = self.env["account.payment"]
        Rate = self.env["res.currency.rate"]
        payment_vals["partner_type"] = "customer"
        payment_vals[
            "journal_id"
        ] = self.env.company.iva_customer_retention_journal_id.id
        out_refund_lines = self.retention_line_ids.filtered(
            lambda l: l.move_id.move_type == "out_refund"
        )
        out_invoice_lines = self.retention_line_ids.filtered(
            lambda l: l.move_id.move_type == "out_invoice"
        )

        out_refunds_dict = defaultdict(account_retention_line_empty_recordset)
        out_invoices_dict = defaultdict(account_retention_line_empty_recordset)

        for line in out_refund_lines:
            out_refunds_dict[line.move_id] += line
        for line in out_invoice_lines:
            out_invoices_dict[line.move_id] += line

        for lines in out_refunds_dict.values():
            payment_vals["payment_method_id"] = (
                self.env.ref("account.account_payment_method_manual_out").id,
            )
            payment_vals["payment_type"] = "outbound"
            payment_vals["foreign_rate"] = lines[0].foreign_currency_rate
            payment = Payment.create(payment_vals)
            payment.update(
                {
                    "foreign_inverse_rate": Rate.compute_inverse_rate(
                        payment.foreign_rate
                    )
                }
            )
            lines.write({"payment_id": payment.id})
            payment.compute_retention_amount_from_retention_lines()
        for lines in out_invoices_dict.values():
            payment_vals["payment_method_id"] = (
                self.env.ref("account.account_payment_method_manual_in").id,
            )
            payment_vals["payment_type"] = "inbound"
            payment_vals["foreign_rate"] = lines[0].foreign_currency_rate
            payment = Payment.create(payment_vals)
            payment.update(
                {
                    "foreign_inverse_rate": Rate.compute_inverse_rate(
                        payment.foreign_rate
                    )
                }
            )
            lines.write({"payment_id": payment.id})
            payment.compute_retention_amount_from_retention_lines()

    def action_draft(self):
        is_admin = self.env.su or self.env.user.has_group('base.group_system') or self.env.user.has_group('account.group_account_manager')
        ctx_debug = self.env.context.get('debug') or self.env.context.get('params', {}).get('debug')
        is_debug_mode = bool(ctx_debug) or self.env.su

        if not (is_admin and is_debug_mode):
            raise UserError(_("La acción 'Convertir a Borrador' en Comprobantes de Retención está restringida exclusivamente para Administradores del Sistema con el Modo Desarrollador (Debug Mode) activo."))

        self.write({"state": "draft"})

    def action_reset_retention(self):
        if not self.env.user.has_group('base.group_system'):
            raise UserError(_("Only system administrators can reset retention vouchers."))
        for record in self:
            payments = record.payment_ids
            lines = record.retention_line_ids

            if payments:
                payments.mapped("move_id.line_ids").remove_move_reconcile()
                payments.action_draft()
                payments.action_cancel()

            for line in lines:
                if line.move_id:
                    line.move_id.write({
                        "iva_voucher_number": False,
                        "islr_voucher_number": False,
                        "municipal_voucher_number": False,
                    })

            # Desasociar líneas de los pagos en BD
            if lines:
                lines.write({"payment_id": False})

            # Invalidar caché contable
            self.env.invalidate_all()

            # Eliminar físicamente los pagos bypassando hooks
            from odoo.models import BaseModel
            if payments:
                BaseModel.unlink(payments)

            # Volver la retención a borrador
            record.with_context(skip_safe_create_payments=True).write({
                "original_lines_per_invoice_counter": False,
                "state": "draft",
            })

#    # Bloque de código a AÑADIR (Es un método completamente nuevo)
## =============================================================

#    def _create_islr_payments_on_draft(self):
#        """
#        Crea los pagos de ISLR en modo borrador, agrupados por concepto y factura, 
#        y los re-crea si las líneas cambian. 
#        Se llama desde create/write a través de _safe_create_payments.
#        """
#        self.ensure_one()
#        Rate = self.env["res.currency.rate"]
        
#        # 1. Eliminar pagos existentes asociados a esta retención (para recrear en draft)
#        self.payment_ids.unlink()

#        Payment = self.env['account.payment']
#        journal_id = (
#            self.env.company.islr_supplier_retention_journal_id.id 
#            if self.type == 'in_invoice' 
#            else self.env.company.islr_customer_retention_journal_id.id
#        )
    
#        # 2. Agrupar líneas por concepto de pago y move_id
#        lines_to_pay = self.retention_line_ids.filtered(lambda l: l.retention_amount != 0.0 and l.payment_concept_id)
#        # Agrupación por (Concepto, Factura) para generar un pago por grupo
#        lines_by_concept_and_move = defaultdict(lambda: self.env['account.retention.line'])
        
#        for line in lines_to_pay:
#            lines_by_concept_and_move[(line.payment_concept_id, line.move_id)] += line
        
#        payments = self.env['account.payment']
#        for (concept, move), lines in lines_by_concept_and_move.items():
            
#            # Determinar tipo de pago y socio (Inbound/Outbound)
#            partner_type = 'supplier' if self.type in ('in_invoice', 'in_refund') else 'customer'
#            payment_type = 'outbound' if self.type == 'in_invoice' else 'inbound'
            
#            # Invertir para notas de crédito (refunds)
#            if move.move_type in ('in_refund', 'out_refund'):
#                 payment_type = 'inbound' if payment_type == 'outbound' else 'outbound'
            
#            # Asignar método de pago manual según el tipo (como en IVA)
#            payment_method_ref = (
#                "account.account_payment_method_manual_in"
#                if payment_type == "inbound"
#                else "account.account_payment_method_manual_out"
#            )

#            payment_vals = {
#                'retention_id': self.id,
#                'partner_id': self.partner_id.id,
#                'payment_type_retention': 'islr',
#                'is_retention': True,
#                'journal_id': journal_id,
#                'partner_type': partner_type,
#                'payment_type': payment_type,
#                'payment_concept_id': concept.id,
#                'foreign_rate': lines[0].foreign_currency_rate,
#                'payment_method_id': self.env.ref(payment_method_ref).id,
#                'amount': sum(lines.mapped('retention_amount')),
#                'currency_id': self.env.company.currency_id.id,
#                'date': self.date_accounting or fields.Date.context_today(self),
#             }
        
#            payment = Payment.create(payment_vals)
            
#            # Asignar rate inversa y líneas de retención
#            payment.update({
#                "foreign_inverse_rate": Rate.compute_inverse_rate(payment.foreign_rate),
#                "retention_line_ids": [(6, 0, lines.ids)],
#            })
            
#            # Asignar payment_id a las líneas
#            lines.write({'payment_id': payment.id})
#            payments += payment
    
#        return payments

# =============================================================
# Bloque de código a AÑADIR (Es un método completamente nuevo)
# =============================================================

    def _create_islr_payments_on_draft(self):
        """
        Sincroniza los pagos de ISLR en modo borrador, agrupados por concepto y factura.
        """
        self.ensure_one()
        Payment = self.env['account.payment']
        Rate = self.env["res.currency.rate"]

        journal_id = (
            self.env.company.islr_supplier_retention_journal_id.id
            if self.type == 'in_invoice'
            else self.env.company.islr_customer_retention_journal_id.id
        )
        journal = self.env['account.journal'].browse(journal_id)
        if not journal:
            return

        # Odoo 18 requiere payment_method_line_id
        payment_method_line = journal.outbound_payment_method_line_ids[:1] if self.type == "in_invoice" else journal.inbound_payment_method_line_ids[:1]
        if not payment_method_line:
             payment_method_line = journal._get_available_payment_method_lines(
                 "outbound" if self.type == "in_invoice" else "inbound"
             )[:1]

        # 1. Determinar los pagos que DEBERÍAN existir
        lines_by_concept_and_move = defaultdict(lambda: self.env['account.retention.line'])
        for line in self.retention_line_ids.filtered(lambda l: l.payment_concept_id):
            lines_by_concept_and_move[(line.payment_concept_id, line.move_id)] += line

        existing_payments = {}
        for p in self.payment_ids:
            if p.retention_line_ids:
                # Usamos el concepto y el move del primer registro vinculado al pago
                first_line = p.retention_line_ids[0]
                existing_payments[(first_line.payment_concept_id, first_line.move_id)] = p
        
        payments_to_keep = self.env['account.payment']

        # 2. Iterar sobre los pagos requeridos para crear o actualizar
        for (concept, move), lines in lines_by_concept_and_move.items():
            lines._compute_line_amounts()
            # Moneda VEF
            _, _, currency_vef, _ = self._get_retention_currencies()
            total_retention_vef = sum(lines.mapped('foreign_retention_amount'))
            
            if currency_vef.is_zero(total_retention_vef):
                continue

            partner_type = 'supplier' if self.type in ('in_invoice', 'in_refund') else 'customer'
            payment_type = 'outbound' if self.type == 'in_invoice' else 'inbound'
            if move.move_type in ('in_refund', 'out_refund'):
                payment_type = 'inbound' if payment_type == 'outbound' else 'outbound'

            # Odoo 18: las cuentas outstanding suelen estar en la payment_method_line o usar la default del diario
            pm_account_id = payment_method_line.payment_account_id.id if payment_method_line and hasattr(payment_method_line, 'payment_account_id') else False
            
            outstanding_account_id = pm_account_id or journal.default_account_id.id

            rate_islr = lines[0].foreign_currency_rate if lines else 1.0
            payment_vals = {
                'retention_id': self.id,
                'partner_id': self.partner_id.id,
                'payment_type_retention': 'islr',
                'is_retention': True,
                'journal_id': journal.id,
                'partner_type': partner_type,
                'payment_type': payment_type,
                'payment_concept_id': concept.id,
                'foreign_rate': rate_islr,
                'tax_today': rate_islr,
                'payment_method_line_id': payment_method_line.id if payment_method_line else False,
                'outstanding_account_id': outstanding_account_id,
                'amount': total_retention_vef,
                'currency_id': currency_vef.id,
                'date': self.date_accounting or fields.Date.context_today(self),
                "retention_line_ids": [Command.set(lines.ids)],
            }

            # Si ya existe un pago para esta combinación, se actualiza. Si no, se crea.
            payment = existing_payments.get((concept, move))
            if payment and payment.state == 'draft':
                payment.write(payment_vals)
                if hasattr(payment, 'foreign_inverse_rate'):
                    payment.write({
                        "tax_today": payment.foreign_rate or rate_islr,
                        "foreign_inverse_rate": Rate.compute_inverse_rate(payment.foreign_rate or rate_islr)
                    })
            elif not payment:
                payment = Payment.create(payment_vals)
                if hasattr(payment, 'foreign_inverse_rate'):
                    payment.write({
                        "tax_today": payment.foreign_rate or rate_islr,
                        "foreign_inverse_rate": Rate.compute_inverse_rate(payment.foreign_rate or rate_islr)
                    })
            else:
                payments_to_keep |= payment
                continue
            
            lines.write({'payment_id': payment.id})
            payments_to_keep |= payment

        # 3. Eliminar pagos que ya no son necesarios
        payments_to_remove = self.payment_ids.filtered(lambda p: p not in payments_to_keep and p.state == 'draft')
        if payments_to_remove:
            payments_to_remove.unlink()

        return payments_to_keep

    # NOTA: _safe_create_payments está definido más arriba (línea ~514).
    # La definición activa incluye guards de estado, tipo municipal y líneas vacías.
    
    def action_post(self):

        for retention in self:
            try:
                # Validaciones iniciales (se mantienen igual)
                if retention.state == 'emitted':
                    _logger.info(f"Retención {retention.id} ya está en estado 'emitted', omitiendo")
                    continue

                _logger.info(f"Iniciando publicación de retención {retention.id}")

                # Asignar número de secuencia si no existe
                if not retention.number:
                    _logger.info(f"Asignando número de secuencia a retención {retention.id}")
                    retention._set_sequence()
                    _logger.info(f"Número asignado: {retention.number}")
            
                if retention.type in ["out_invoice", "out_refund", "out_debit"] and not retention.number:
                    error_msg = f"Retención {retention.id} no tiene número asignado"
                    _logger.error(error_msg)
                    raise UserError(_("Debe ingresar un número para la retención"))
        
                # Establecer fechas si no están definidas
                today = fields.Date.context_today(self)
                if not retention.date_accounting:
                    retention.date_accounting = today
                    _logger.info(f"Fecha contable establecida: {retention.date_accounting}")
                if not retention.date:
                    retention.date = today
                    _logger.info(f"Fecha de retención establecida: {retention.date}")

                # VALIDACIONES ESPECÍFICAS PARA ISLR (NUEVO)
                if retention.type_retention == 'islr':
                    if not retention.partner_id.type_person_id:
                        raise UserError(_("Para retenciones ISLR, el partner debe tener tipo de persona configurado"))
                
                    if not all(line.payment_concept_id for line in retention.retention_line_ids):
                        raise UserError(_("Todas las líneas de retención ISLR deben tener un concepto de pago asignado"))

                # Crear pagos si no existen (FALLBACK)
                # La creación principal para IVA/ISLR ocurre en create/write vía _safe_create_payments
                if not retention.payment_ids:
                    _logger.info("Creando pagos para la retención (FALLBACK)")
                    retention._safe_create_payments() # Llamada unificada que ahora gestiona ambos

#                # Crear pagos si no existen (modificado para ISLR)
#                if not retention.payment_ids:
#                    _logger.info("Creando pagos para la retención")
#                    if retention.type_retention == 'islr':
#                        retention._create_islr_payments()  # Nuevo método para ISLR
#                    else:
#                        retention._create_payments_from_retention_lines()  # Método existente para IVA/municipal

                # Procesar cada pago con contexto seguro (se mantiene igual)
                for payment in retention.payment_ids.with_context(
                    skip_manually_modified_check=True,
                    skip_retention_state_check=True
                ):
                    _logger.info(f"Procesando pago {payment.id}")
                    if payment.state == 'draft' and retention.number:
                        payment.write({'memo': f"Retención {retention.number}"})
                        
                    if not payment.outstanding_account_id:
                        journal = payment.journal_id
                        pm_account = False
                        if payment.payment_method_line_id and hasattr(payment.payment_method_line_id, 'payment_account_id'):
                            pm_account = payment.payment_method_line_id.payment_account_id
                            
                        outstanding = pm_account or journal.default_account_id
                        if outstanding:
                            payment.outstanding_account_id = outstanding
                        elif payment.payment_method_line_id.payment_account_id:
                            payment.outstanding_account_id = payment.payment_method_line_id.payment_account_id

                    if not payment.move_id:
                        if hasattr(payment, 'action_create'):
                            _logger.info("Creando asiento contable para el pago")
                            payment.action_create()
                        else:
                            _logger.info("Publicando pago (versión moderna)")
                        payment.with_context(skip_manually_modified_check=True).action_post()
                    elif payment.state == 'draft':
                        _logger.info(f"Publicando pago borrador {payment.id}")
                        payment.with_context(skip_manually_modified_check=True).action_post()

                # Asignar número de comprobante a facturas (se mantiene igual)
                move_ids = retention.mapped("retention_line_ids.move_id")
                if move_ids:
                    _logger.info(f"Asignando número de comprobante a {len(move_ids)} facturas")
                    retention.set_voucher_number_in_invoice(move_ids, retention)

                # Reconciliación Automática
                try:
                    retention._reconcile_all_payments()
                    _logger.info(f"Reconciliación completada para retención {retention.id}")
                except Exception as e:
                    _logger.warning(
                        f"Reconciliación automática no completada para retención {retention.id}: {e}. "
                        "Las líneas se pueden reconciliar manualmente desde la factura."
                    )

                # Actualizar estado de la retención (se mantiene igual)
                retention.write({'state': 'emitted'})
                _logger.info(f"Retención {retention.id} marcada como emitida")
            except Exception as e:
                _logger.error("Error al publicar retención %s: %s", retention.id, str(e), exc_info=True)
                raise UserError(_("Error al publicar la retención: %s") % str(e))

    def _create_islr_payments(self):
        """
        Nuevo método para crear pagos de ISLR agrupados por concepto
        """
        Payment = self.env['account.payment']
        journal_id = (
            self.env.company.islr_supplier_retention_journal_id.id 
            if self.type == 'in_invoice' 
            else self.env.company.islr_customer_retention_journal_id.id
        )
    
        # Agrupar líneas por concepto de pago
        lines_by_concept = defaultdict(lambda: self.env['account.retention.line'])
        for line in self.retention_line_ids:
            lines_by_concept[line.payment_concept_id] += line
    
        payments = self.env['account.payment']
        Rate = self.env["res.currency.rate"]
        for concept, lines in lines_by_concept.items():
            rate_legacy = lines[0].foreign_currency_rate if lines else 1.0
            payment_vals = {
                'retention_id': self.id,
                'partner_id': self.partner_id.id,
                'payment_type_retention': 'islr',
                'is_retention': True,
                'journal_id': journal_id,
                'partner_type': 'supplier' if self.type == 'in_invoice' else 'customer',
                'payment_type': 'outbound' if self.type == 'in_invoice' else 'inbound',
                'payment_concept_id': concept.id,
                'foreign_rate': rate_legacy,
                'tax_today': rate_legacy,
                'retention_line_ids': [(6, 0, lines.ids)],
                'amount': sum(lines.mapped('retention_amount')),
                'currency_id': self.env.company.currency_id.id,
                'date': self.date_accounting,
             }
        
            payment = Payment.create(payment_vals)
            if hasattr(payment, 'foreign_inverse_rate'):
                payment.write({
                    "tax_today": payment.foreign_rate or rate_legacy,
                    "foreign_inverse_rate": Rate.compute_inverse_rate(payment.foreign_rate or rate_legacy)
                })
            payments += payment
    
        return payments   


    def set_voucher_number_in_invoice(self, move, retention):
        try:
            _logger.info(f"Asignando número de comprobante a facturas para retención {retention.id}")
        
            if retention.type_retention == "iva":
                _logger.info(f"Asignando iva_voucher_number: {retention.number}")
                move.write({"iva_voucher_number": retention.number})
            elif retention.type_retention == "islr":
                _logger.info(f"Asignando islr_voucher_number: {retention.number}")
                move.write({"islr_voucher_number": retention.number})
            elif retention.type_retention == "municipal":
                _logger.info(f"Asignando municipal_voucher_number: {retention.number}")
                move.write({"municipal_voucher_number": retention.number})
            
            _logger.info(f"Números de comprobante asignados correctamente a {len(move)} facturas")
        
        except Exception as e:
            _logger.error(f"Error asignando número de comprobante: {str(e)}")
            raise
    
    def _safe_set_voucher_number(self, moves, retention):
        """Asigna número de comprobante sin modificar campos protegidos"""
        for move in moves:
            if move.state == 'posted':  # Solo para facturas publicadas
                vals = {}
                if retention.type_retention == "iva":
                    vals['iva_voucher_number'] = retention.number
                elif retention.type_retention == "islr":
                    vals['islr_voucher_number'] = retention.number
                elif retention.type_retention == "municipal":
                    vals['municipal_voucher_number'] = retention.number
            
                if vals:
                    move.write(vals)
    
    def action_print_municipal_retention_xlsx(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/get_xlsx_municipal_retention?&retention_id={self.id}",
            "target": "self",
        }

    def _set_sequence(self):
        for retention in self.filtered(lambda r: not r.number):
            try:
                _logger.info(f"Asignando secuencia a retención {retention.id}")
            
                sequence_number = ""
                # Determinar si se usa reinicio anual de correlativos
                use_annual_reset = retention.company_id.retention_sequence_annual_reset
                seq_date = retention.date_accounting if use_annual_reset else None
                
                if retention.type_retention == "iva":
                    sequence = retention.get_sequence_iva_retention()
                    _logger.info(f"Secuencia IVA encontrada: {sequence.id}")
                    sequence_number = sequence.next_by_id(sequence_date=seq_date) if seq_date else sequence.next_by_id()
                elif retention.type_retention == "islr":
                    sequence = retention.get_sequence_islr_retention()
                    _logger.info(f"Secuencia ISLR encontrada: {sequence.id}")
                    sequence_number = sequence.next_by_id(sequence_date=seq_date) if seq_date else sequence.next_by_id()
                else:
                    sequence = retention.get_sequence_municipal_retention()
                    _logger.info(f"Secuencia Municipal encontrada: {sequence.id}")
                    sequence_number = sequence.next_by_id(sequence_date=seq_date) if seq_date else sequence.next_by_id()
            
                correlative = f"{retention.date_accounting.year}{retention.date_accounting.month:02d}{sequence_number}"
                retention.name = correlative
                retention.number = correlative
            
                _logger.info(f"Retención {retention.id} - Número asignado: {retention.number}")
            
            except Exception as e:
                _logger.error(f"Error asignando secuencia a retención {retention.id}: {str(e)}")
                raise UserError(_("Error al asignar número de secuencia: %s") % str(e))



    @api.model
    def get_sequence_iva_retention(self):
        _logger.info("Buscando secuencia para retenciones IVA")
        sequence = self.env["ir.sequence"].search(
            [
                ("code", "=", "retention.iva.control.number"),
                ("company_id", "=", self.env.company.id),
            ], limit=1
        )
        if not sequence:
            _logger.info("Secuencia para retenciones IVA no encontrada, creando nueva")
            sequence = self.env["ir.sequence"].create(
                {
                    "name": "Numero de control retenciones IVA",
                    "code": "retention.iva.control.number",
                    "padding": 5,
                    "company_id": self.env.company.id,
                }
            )
            _logger.info(f"Nueva secuencia IVA creada con ID {sequence.id}")

        _logger.info(f"Retornando secuencia IVA: {sequence.id}")
        return sequence

    @api.model
    def get_sequence_islr_retention(self):
        _logger.info("Buscando secuencia para retenciones ISLR")
        sequence = self.env["ir.sequence"].search(
            [
                ("code", "=", "retention.islr.control.number"),
                ("company_id", "=", self.env.company.id),
            ], limit=1
        )
        if not sequence:
            _logger.info("Secuencia para retenciones ISLR no encontrada, creando nueva")
            sequence = self.env["ir.sequence"].create(
                {
                    "name": "Numero de control retenciones ISLR",
                    "code": "retention.islr.control.number",
                    "padding": 5,
                    "company_id": self.env.company.id,
                }
            )
            _logger.info(f"Nueva secuencia ISLR creada con ID {sequence.id}")

        _logger.info(f"Retornando secuencia ISLR: {sequence.id}")
        return sequence

    def get_sequence_municipal_retention(self):
        _logger.info("Buscando secuencia para retenciones Municipales")
        sequence = self.env["ir.sequence"].search(
            [
                ("code", "=", "retention.municipal.control.number"),
                ("company_id", "=", self.env.company.id),
            ], limit=1
        )
        if not sequence:
            _logger.info("Secuencia para retenciones Municipales no encontrada, creando nueva")
            sequence = self.env["ir.sequence"].create(
                {
                    "name": "Numero de control retenciones Municipales",
                    "code": "retention.municipal.control.number",
                    "padding": 5,
                    "company_id": self.env.company.id,
                }
            )
            _logger.info(f"Nueva secuencia Municipal creada con ID {sequence.id}")

        _logger.info(f"Retornando secuencia Municipal: {sequence.id}")
        return sequence

    def clear_islr_retention_number(self):
        for line in self.retention_line_ids:
            if line.move_id.islr_voucher_number:
                line.move_id.islr_voucher_number = False

    def action_cancel(self):
        for retention in self:
            if retention.number and not retention.number.endswith("-canc") and "-canc-" not in retention.number:
                canc_num = self.env['account.payment']._get_next_canceled_name(
                    "account.retention", retention.number, retention.company_id.id
                )
                retention.write({"number": canc_num})
        self.payment_ids.mapped("move_id.line_ids").remove_move_reconcile()
        self.payment_ids.action_cancel()
        self.write({"state": "cancel"})
        self.clear_islr_retention_number()

    def create_payment_from_retention_form(self):
        _logger.info("Entrando en create_payment_from_retention_form (VERSION DE LOGGING)")
        # ... (el resto del código de la función) ...
        """
        Create the corresponding payments for the retention based on the fields of the retention.

        This is meant to create the payment for the ISLR and municipal retentions and it is
        triggered on the action_post method of the retention if it still doesn't have payments at
        that point.

        Returns
        -------
        account.payment recordset
            The payments created for the retention.
        """
        self.ensure_one()
        Payment = self.env["account.payment"]
        journals = {
            ("islr", "in_invoice"): self.env.company.islr_supplier_retention_journal_id,
            (
                "islr",
                "out_invoice",
            ): self.env.company.islr_customer_retention_journal_id,
            (
                "municipal",
                "in_invoice",
            ): self.env.company.municipal_supplier_retention_journal_id,
            (
                "municipal",
                "out_invoice",
            ): self.env.company.municipal_customer_retention_journal_id,
        }
        journal_id = journals[(self.type_retention, self.type)].id

        if self.type_retention == "islr":
            self._validate_islr_retention_fields()

        payment_type = "outbound" if self.type == "in_invoice" else "inbound"
        partner_type = "supplier" if self.type == "in_invoice" else "customer"
        payment_vals = []

        for line in self.retention_line_ids:
            if line.move_id.move_type == "in_refund":
                payment_type = "inbound" if self.type == "in_invoice" else "outbound"
            if line.move_id.move_type == "out_refund":
                payment_type = "outbound" if self.type == "out_invoice" else "inbound"

            payment_method_ref = (
                "account.account_payment_method_manual_in"
                if payment_type == "inbound"
                else "account.account_payment_method_manual_out"
            )

            payment_vals.append(
                {
                    "state": "draft",
                    "payment_type": payment_type,
                    "partner_type": partner_type,
                    "partner_id": line.move_id.partner_id.id,
                    "journal_id": journal_id,
                    "payment_type_retention": self.type_retention,
                    "payment_method_id": self.env.ref(payment_method_ref).id,
                    "is_retention": True,
                    "foreign_rate": line.move_id.foreign_rate,
                    "foreign_inverse_rate": line.move_id.foreign_inverse_rate,
                    "retention_line_ids": [(4, line.id)],
                    "currency_id": self.env.user.company_id.currency_id.id,
                    'amount': line.retention_amount, # <--- AÑADE ESTA LÍNEA
                    'payment_concept_id': line.payment_concept_id.id if line.payment_concept_id else False, # <--- AÑADE ESTA LÍNEA
                    'date': self.date_accounting, # <--- AÑADE ESTA LÍNEA
                    # "retention_line_ids": line,
                    # "currency_id": self.env.user.company_id.currency_id.id,
                }
            )

        # payments = Payment.create(payment_vals)
        payments = self.env["account.payment"]
        for vals in payment_vals:
            payments += Payment.create(vals)
        payments.compute_retention_amount_from_retention_lines()

        # >>>>>>>>>>>> AGREGAR ESTA LÍNEA <<<<<<<<<<<<<<<<
        payments.action_post()
        _logger.warning(f"Payments IDs after action_post: {payments.ids}, Move IDs after action_post: {[p.move_id for p in payments]}")  # <---- LÍNEA AGREGADA AQUÍ

        for payment in payments:
            _logger.warning(f"Payment ID: {payment.id}, Move ID after action_post: {payment.move_id}")


        return payments

    def _validate_islr_retention_fields(self):
        """
        Validates the partner has a type person and all the retention lines have a payment concept.
        """
        self.ensure_one()
        if not self.partner_id.type_person_id:
            raise UserError(_("Select a type person"))
        if not any(self.retention_line_ids.filtered(lambda l: l.payment_concept_id)):
            raise UserError(_("Select a payment concept"))

    def _reconcile_all_payments(self):
        for payment in self.mapped("payment_ids"):
            try:
                if payment.partner_type == "supplier":
                    self._reconcile_supplier_payment(payment)
                elif payment.partner_type == "customer":
                    self._reconcile_customer_payment(payment)
            except UserError as e:
                _logger.error(f"Error reconciliando pago {payment.id}: {str(e)}")
                raise

            except Exception as e:
                _logger.error(f"Error inesperado reconciliando pago {payment.id}: {str(e)}")
                raise UserError(_("Ocurrió un error inesperado al reconciliar los pagos."))


    def _reconcile_supplier_payment(self, payment):
        """
        Reconciliación de pagos a proveedores para retenciones usando ORM nativo.
        Maneja automáticamente diferencias de cambio (VEF vs USD).
        """
        _logger.info(f"Reconciliando pago a proveedor ID: {payment.id}")
    
        if not payment.move_id:
            _logger.warning(f"Pago {payment.id} no tiene asiento contable, omitiendo reconciliación")
            return

        if payment.move_id.state == 'draft':
            payment.move_id.action_post()
            
        if payment.move_id.state != 'posted':
            _logger.warning(f"Asiento del pago {payment.id} no está publicado, omitiendo reconciliación")
            return

        payment.retention_line_ids._compute_line_amounts()
        if payment.retention_id:
            payment.retention_id.retention_line_ids._compute_line_amounts()
            
        facturas = (payment.retention_line_ids.mapped('move_id') | (payment.retention_id and payment.retention_id.retention_line_ids.mapped('move_id'))).filtered(
            lambda m: m.state == 'posted'
        )
        if not facturas:
            _logger.warning("No hay facturas publicadas vinculadas a este pago")
            return

        # Auto-reparación de monto, tasa y líneas desincronizadas en pagos creados previamente
        total_retention_vef = sum((payment.retention_line_ids or payment.retention_id.retention_line_ids).mapped("foreign_retention_amount"))
        has_zero_lines = any(l.debit == 0.0 and l.credit == 0.0 for l in payment.move_id.line_ids)
        if total_retention_vef > 0 and (payment.currency_id.is_zero(payment.amount) or abs(payment.amount - total_retention_vef) > 0.01 or has_zero_lines):
            _logger.info(f"Reparando monto y líneas en pago {payment.id}: de {payment.amount} a {total_retention_vef}")
            if payment.move_id and payment.move_id.line_ids.filtered(lambda l: l.reconciled):
                payment.move_id.line_ids.remove_move_reconcile()
            if payment.state != 'draft':
                payment.action_draft()
            rate = payment.foreign_rate or (payment.retention_line_ids and payment.retention_line_ids[0].foreign_currency_rate) or (facturas and facturas[0].tax_today) or 1.0
            payment.write({
                "amount": total_retention_vef,
                "tax_today": rate,
                "foreign_rate": rate,
            })
            payment._synchronize_to_moves({'amount', 'currency_id', 'payment_type', 'partner_id', 'date'})
            if hasattr(payment, '_currency_equal'):
                payment._currency_equal()
            payment.action_post()

        Rate = self.env["res.currency.rate"]
        if not payment.tax_today or payment.tax_today == 0:
            rate = (
                payment.foreign_rate
                or (payment.retention_line_ids and payment.retention_line_ids[0].foreign_currency_rate)
                or (facturas and facturas[0].tax_today)
                or 1.0
            )
            payment.write({
                "tax_today": rate,
                "foreign_rate": rate,
                "foreign_inverse_rate": Rate.compute_inverse_rate(rate),
            })
            if payment.move_id:
                payment.move_id.write({"tax_today": rate})
                payment.move_id.line_ids.write({"tax_today": rate})
            
        # Buscar líneas en el pago que apunten a cuentas por pagar y no estén reconciliadas
        payment_payable_lines = payment.move_id.line_ids.filtered(
            lambda l: l.account_id.account_type == 'liability_payable' and not l.reconciled
        )
        if not payment_payable_lines:
            _logger.warning(f"No hay líneas 'liability_payable' en el asiento del pago {payment.id}")
            return
            
        for factura in facturas:
            # Buscar en la factura las líneas por pagar no reconciliadas de la misma cuenta o tipo
            invoice_payable_lines = factura.line_ids.filtered(
                lambda l: (l.account_id == payment_payable_lines[0].account_id or l.account_id.account_type == 'liability_payable') 
                         and not l.reconciled
            )
            if not invoice_payable_lines:
                _logger.warning(f"No hay líneas reconciliables en factura {factura.name}")
                continue
                
            try:
                (payment_payable_lines[0] | invoice_payable_lines[0]).reconcile()
                _logger.info(f"Reconciliación exitosa: pago {payment.name} ↔ factura {factura.name}")
            except Exception as e:
                _logger.warning(f"Error reconciliando pago {payment.name} con factura {factura.name}: {e}")
                pass

    def _reconcile_customer_payment(self, payment):
        """
        Reconciliación de pagos de clientes para retenciones usando ORM nativo.
        Maneja automáticamente diferencias de cambio (VEF vs USD).
        """
        _logger.info(f"Reconciliando pago de cliente ID: {payment.id}")
        
        if not payment.move_id:
            _logger.warning(f"Pago {payment.id} no tiene asiento contable, omitiendo reconciliación")
            return

        if payment.move_id.state == 'draft':
            payment.move_id.action_post()
            
        if payment.move_id.state != 'posted':
            _logger.warning(f"Asiento del pago {payment.id} no está publicado, omitiendo reconciliación")
            return

        payment.retention_line_ids._compute_line_amounts()
        if payment.retention_id:
            payment.retention_id.retention_line_ids._compute_line_amounts()
            
        facturas = (payment.retention_line_ids.mapped('move_id') | (payment.retention_id and payment.retention_id.retention_line_ids.mapped('move_id'))).filtered(
            lambda m: m.state == 'posted'
        )
        if not facturas:
            return

        # Auto-reparación de monto y tasa en pagos creados con amount = 0
        total_retention_vef = sum((payment.retention_line_ids or payment.retention_id.retention_line_ids).mapped("foreign_retention_amount"))
        has_zero_lines = any(l.debit == 0.0 and l.credit == 0.0 for l in payment.move_id.line_ids)
        if total_retention_vef > 0 and (payment.currency_id.is_zero(payment.amount) or abs(payment.amount - total_retention_vef) > 0.01 or has_zero_lines):
            _logger.info(f"Reparando monto y líneas en pago {payment.id}: de {payment.amount} a {total_retention_vef}")
            if payment.move_id and payment.move_id.line_ids.filtered(lambda l: l.reconciled):
                payment.move_id.line_ids.remove_move_reconcile()
            if payment.state != 'draft':
                payment.action_draft()
            rate = payment.foreign_rate or (payment.retention_line_ids and payment.retention_line_ids[0].foreign_currency_rate) or (facturas and facturas[0].tax_today) or 1.0
            payment.write({
                "amount": total_retention_vef,
                "tax_today": rate,
                "foreign_rate": rate,
            })
            payment._synchronize_to_moves({'amount', 'currency_id', 'payment_type', 'partner_id', 'date'})
            if hasattr(payment, '_currency_equal'):
                payment._currency_equal()
            payment.action_post()

        Rate = self.env["res.currency.rate"]
        if not payment.tax_today or payment.tax_today == 0:
            rate = (
                payment.foreign_rate
                or (payment.retention_line_ids and payment.retention_line_ids[0].foreign_currency_rate)
                or (facturas and facturas[0].tax_today)
                or 1.0
            )
            payment.write({
                "tax_today": rate,
                "foreign_rate": rate,
                "foreign_inverse_rate": Rate.compute_inverse_rate(rate),
            })
            if payment.move_id:
                payment.move_id.write({"tax_today": rate})
                payment.move_id.line_ids.write({"tax_today": rate})
            
        payment_receivable_lines = payment.move_id.line_ids.filtered(
            lambda l: l.account_id.account_type == 'asset_receivable' and not l.reconciled
        )
        if not payment_receivable_lines:
            _logger.warning(f"No hay líneas 'asset_receivable' en el asiento del pago {payment.id}")
            return
            
        for factura in facturas:
            invoice_receivable_lines = factura.line_ids.filtered(
                lambda l: (l.account_id == payment_receivable_lines[0].account_id or l.account_id.account_type == 'asset_receivable') 
                         and not l.reconciled
            )
            if not invoice_receivable_lines:
                continue
                
            try:
                (payment_receivable_lines[0] | invoice_receivable_lines[0]).reconcile()
                _logger.info(f"Reconciliación exitosa: pago {payment.name} ↔ factura {factura.name}")
            except Exception as e:
                _logger.warning(f"Error reconciliando pago {payment.name} con factura {factura.name}: {e}")
                pass

    @api.model
    def compute_retention_lines_data(self, invoice_id, payment=None):
        """
        Computes the retention lines data for the given invoice.

        Params
        ------
        invoice_id: account.move
            The invoice for which the retention lines are computed.
        type_retention: tuple[str,str]
            The type of retention and the type of invoice.
        payment: account.payment
            The payment for which the retention lines are computed.

        Returns
        -------
        list[dict]
            The retention lines data.
        """
        tax_ids = invoice_id.invoice_line_ids.filtered(
            lambda l: l.tax_ids and l.tax_ids[0].amount > 0
        ).mapped("tax_ids")
        _logger.info(f"compute_retention_lines_data: Impuestos encontrados en las líneas de factura: {tax_ids.ids}")

        if not any(tax_ids):
            raise UserError(_("The invoice %s has no tax.") % invoice_id.name)

        withholding_amount = invoice_id.partner_id.withholding_type_id.value

        lines_data = []
        if "subtotals" in invoice_id.tax_totals and invoice_id.tax_totals["subtotals"]:
            _logger.warning(f"Tax Totals for invoice ID {invoice_id.id}: {invoice_id.tax_totals}")

            # ==========================================================================
            # REGLA UNIVERSAL VENEZOLANA: Las retenciones SIEMPRE se expresan en VEF
            # ==========================================================================
            # La lógica es independiente de cuál sea la moneda base de la empresa.
            # El principio es:
            #   1. Si la factura ya está en VEF → montos de retención en VEF directamente
            #   2. Si la factura está en cualquier otra moneda (USD, EUR, etc.) →
            #      convertir a VEF usando la tasa de l10n_ve_tax (ya precalculada en
            #      tax_totals['foreign_amount_untaxed'] y ['foreign_amount_total'])
            #
            # En todos los casos también guardamos los montos en la moneda de la empresa
            # para el registro contable en la moneda del sistema.
            # ==========================================================================

            tax_totals = invoice_id.tax_totals

            # Identificar las monedas dinámicamente
            base_currency, alternate_currency, vef_currency, foreign_currency = self._get_retention_currencies()
            invoice_currency = invoice_id.currency_id

            # ¿La factura ya está en VEF/VES?
            invoice_is_in_vef = invoice_currency.name in ('VEF', 'VES')

            # Regla v62: Determinar la tasa a usar (Priorizar tasa BCV de la factura)
            invoice_rate = invoice_id.tax_today or 1.0
            today_rate = getattr(self.env.company, 'currency_id_dif', self.env['res.currency']).inverse_rate or 1.0
            used_rate = today_rate if self.use_today_rate else invoice_rate

            # Tasa y tasa inversa
            foreign_rate = used_rate
            foreign_inverse_rate = 1.0 / used_rate if used_rate else 0.0

            # Validación: si la factura NO está en VEF/VES, se necesita tasa para convertir
            if not invoice_is_in_vef and not foreign_rate:
                raise UserError(_(
                    "No se pudo crear la línea de retención. La tasa de cambio para la factura '%s' "
                    "(moneda %s) no está definida. Por favor, configure la tasa de cambio en "
                    "Configuración > Monedas > Tasas."
                ) % (invoice_id.display_name, invoice_currency.name))

            # Montos globales en VEF (Regla v62: Conversión Manual con Tasa Dual)
            if invoice_is_in_vef:
                global_vef_untaxed = invoice_id.amount_untaxed
                global_vef_total = invoice_id.amount_total
            else:
                if self.use_today_rate:
                    global_vef_untaxed = invoice_id.amount_untaxed * used_rate
                    global_vef_total = invoice_id.amount_total * used_rate
                else:
                    global_vef_untaxed = getattr(invoice_id, 'amount_untaxed_bs', 0.0) or (invoice_id.amount_untaxed * used_rate)
                    global_vef_total = getattr(invoice_id, 'amount_total_bs', 0.0) or (invoice_id.amount_total * used_rate)

            for subtotal in tax_totals["subtotals"]:
                subtotal_name = subtotal.get("name", "Subtotal")
                subtotal_tax_groups = subtotal.get("tax_groups", [])
                total_groups = len(subtotal_tax_groups)

                for idx, tax_group_data in enumerate(subtotal_tax_groups):
                    tax = tax_ids.filtered(lambda t: t.tax_group_id.id == tax_group_data.get("id"))
                    if not tax:
                        continue
                    tax = tax[0]

                    # Montos en la moneda de empresa (USD o VEF)
                    invoice_amount_company = tax_group_data.get("base_amount", tax_group_data.get("base_amount_currency", 0.0))
                    iva_amount_company = tax_group_data.get("tax_amount", tax_group_data.get("tax_amount_currency", 0.0))

                    # ==========================================================
                    # Calcular montos en la moneda fiscal (VEF/VES)
                    # ==========================================================
                    if invoice_is_in_vef:
                        # La factura ya está en VEF/VES → usar montos del documento directamente
                        vef_invoice_amount = tax_group_data.get("base_amount_currency", tax_group_data.get("base_amount", 0.0))
                        vef_iva_amount = tax_group_data.get("tax_amount_currency", tax_group_data.get("tax_amount", 0.0))
                        vef_invoice_total = invoice_id.amount_total
                    elif global_vef_untaxed > 0:
                        # La factura está en otra moneda (ej. USD) y escalamos proporcionalmente los VEF globales
                        total_invoice_untaxed = sum(
                            tg.get("base_amount", tg.get("base_amount_currency", 0.0))
                            for sub in tax_totals.get("subtotals", [])
                            for tg in sub.get("tax_groups", [])
                        ) or 1.0
                        proportion = tax_group_data.get("base_amount_currency", 0.0) / total_invoice_untaxed if total_invoice_untaxed else 0.0
                        vef_invoice_amount = global_vef_untaxed * proportion
                        vef_iva_amount = (global_vef_total - global_vef_untaxed) * proportion
                        vef_invoice_total = global_vef_total
                    else:
                        # Fallback
                        vef_invoice_amount = invoice_amount_company * used_rate
                        vef_iva_amount = iva_amount_company * used_rate
                        vef_invoice_total = invoice_id.amount_total * used_rate

                    # Retención en VEF (siempre)
                    vef_retention_amount = float_round(
                        vef_iva_amount * (withholding_amount / 100),
                        precision_digits=vef_currency.decimal_places if vef_currency else 2,
                    )

                    # Retención en moneda empresa (para el apunte contable)
                    retention_amount_company = float_round(
                        iva_amount_company * (withholding_amount / 100),
                        precision_digits=invoice_id.company_currency_id.decimal_places,
                    )

                    invoice_total_company = sum(
                        tg.get("base_amount", 0.0) + tg.get("tax_amount", 0.0)
                        for sub in tax_totals.get("subtotals", [])
                        for tg in sub.get("tax_groups", [])
                    ) or invoice_id.amount_total

                    _logger.warning(
                        f"Retención calculada: "
                        f"invoice={invoice_amount_company} {invoice_currency.name}, "
                        f"iva={iva_amount_company} {invoice_currency.name}, "
                        f"vef_invoice={vef_invoice_amount}, vef_iva={vef_iva_amount}, "
                        f"tasa={foreign_rate}, ret_vef={vef_retention_amount}"
                    )

                    line_data = {
                        "name": _("Iva Retention"),
                        "invoice_type": invoice_id.move_type,
                        "move_id": invoice_id.id,
                        "payment_id": payment.id if payment else None,
                        "aliquot": tax.amount,
                        # Montos en moneda empresa
                        "invoice_amount": invoice_amount_company,
                        "iva_amount": iva_amount_company,
                        "invoice_total": invoice_total_company,
                        "retention_amount": retention_amount_company,
                        # Montos en VEF (siempre — regla universal de retenciones VE)
                        "foreign_invoice_amount": vef_invoice_amount,
                        "foreign_iva_amount": vef_iva_amount,
                        "foreign_invoice_total": vef_invoice_total,
                        "foreign_retention_amount": vef_retention_amount,
                        # Tasa
                        "foreign_currency_rate": foreign_rate,
                        "foreign_currency_inverse_rate": foreign_inverse_rate,
                        "related_percentage_tax_base": withholding_amount,
                    }
                    # Evitar líneas con monto cero
                    if line_data.get("retention_amount") != 0.0 or line_data.get("foreign_retention_amount") != 0.0:
                        lines_data.append(line_data)



        return lines_data



#        lines_data = []
#        subtotals_name = invoice_id.tax_totals["subtotals"][0]["name"]
#        tax_groups = zip(
#            invoice_id.tax_totals["groups_by_subtotal"][subtotals_name],
#            invoice_id.tax_totals["groups_by_foreign_subtotal"][subtotals_name],
#        )

#        lines_data = []
#        if "subtotals" in invoice_id.tax_totals and invoice_id.tax_totals["subtotals"]:
#            subtotals_name = invoice_id.tax_totals["subtotals"][0].get("name")
#            if subtotals_name and "groups_by_subtotal" in invoice_id.tax_totals and "groups_by_foreign_subtotal" in invoice_id.tax_totals:
#               tax_groups = zip(
#                   invoice_id.tax_totals["groups_by_subtotal"].get(subtotals_name, []),
#                   invoice_id.tax_totals["groups_by_foreign_subtotal"].get(subtotals_name, []),            
#             )
        
#        for tax_group, foreign_tax_group in tax_groups:
#            taxes = tax_ids.filtered(
#                lambda l: l.tax_group_id.id == tax_group["tax_group_id"]
#            )
#            if not taxes:
#                continue
#            tax = taxes[0]
#            retention_amount = tax_group["tax_group_amount"] * (
#                withholding_amount / 100
#            )
#            retention_amount = float_round(
#                retention_amount,
#                precision_digits=invoice_id.company_currency_id.decimal_places,
#            )
#            line_data = {
#                "name": _("Iva Retention"),
#                "invoice_type": invoice_id.move_type,
#                "move_id": invoice_id.id,
#                "payment_id": payment.id if payment else None,
#                "aliquot": tax.amount,


    def action_create_negative_retention(self, original_retention):
        """
        Crea un comprobante de retención negativo (ajuste) para reversar una retención existente.
        Se llama cuando se revierte una factura que tenía retenciones.

        Params
        ------
        original_retention: account.retention
            La retención original que se va a reversar.

        Returns
        -------
        account.retention
            La nueva retención negativa creada.
        """
        # Deduplicación: si ya existe una retención negativa para esta original, no crear otra
        existing = self.search([
            ("esNegativo", "=", True),
            ("original_retention_id", "=", original_retention.id),
        ], limit=1)
        if existing:
            _logger.info(
                "Ya existe retención negativa (ID %s) para retención %s, retornando existente",
                existing.id, original_retention.number,
            )
            return existing

        new_retention = self.create({
            "name": f"Ajuste negativo de {original_retention.number}",
            "type_retention": original_retention.type_retention,
            "type": original_retention.type,
            "partner_id": original_retention.partner_id.id,
            "company_id": original_retention.company_id.id,
            "date": fields.Date.context_today(self),
            "date_accounting": fields.Date.context_today(self),
            "esNegativo": True,
            "original_retention_id": original_retention.id,
            "state": "draft",
        })

        for orig_line in original_retention.retention_line_ids:
            self.env["account.retention.line"].create({
                "name": orig_line.name,
                "retention_id": new_retention.id,
                "move_id": orig_line.move_id.id,
                "invoice_type": orig_line.invoice_type,
                "aliquot": orig_line.aliquot,
                "invoice_amount": orig_line.invoice_amount,
                "iva_amount": orig_line.iva_amount,
                "invoice_total": orig_line.invoice_total,
                "retention_amount": -orig_line.retention_amount,
                "foreign_invoice_amount": orig_line.foreign_invoice_amount,
                "foreign_iva_amount": orig_line.foreign_iva_amount,
                "foreign_invoice_total": orig_line.foreign_invoice_total,
                "foreign_retention_amount": -orig_line.foreign_retention_amount,
                "foreign_currency_rate": orig_line.foreign_currency_rate,
                "foreign_currency_inverse_rate": orig_line.foreign_currency_inverse_rate,
                "related_percentage_tax_base": orig_line.related_percentage_tax_base,
                "date_accounting": orig_line.date_accounting,
                "payment_concept_id": orig_line.payment_concept_id.id if orig_line.payment_concept_id else False,
            })

        return new_retention

    def get_signature(self):
        if self.company_id.signature_stamp_signature:
            sig = self.company_id.signature_stamp_signature
            return sig.decode('utf-8') if isinstance(sig, bytes) else sig
        config = self.env["signature.config"].search(
            [("active", "=", True), ("company_id", "=", self.company_id.id)],
            limit=1,
        )
        if config and config.signature:
            return config.signature.decode() if isinstance(config.signature, bytes) else config.signature
        return False

    def get_stamp(self):
        if self.company_id.signature_stamp_stamp:
            stamp = self.company_id.signature_stamp_stamp
            return stamp.decode('utf-8') if isinstance(stamp, bytes) else stamp
        return False
