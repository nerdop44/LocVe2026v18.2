from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class AccountRetentionLine(models.Model):
    _name = "account.retention.line"
    _description = "Retention Line"

    check_company = True

    name = fields.Char(
        string="Description", required=True, compute="_compute_name", store=True, readonly=False
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    state = fields.Selection(related="retention_id.state")
    company_currency_id = fields.Many2one(related="retention_id.company_currency_id")
    foreign_currency_id = fields.Many2one(related="retention_id.foreign_currency_id")
    retention_id = fields.Many2one("account.retention", string="Retention", ondelete="cascade")
    invoice_type = fields.Selection(
        selection=[
            ("out_invoice", "Out invoice"),
            ("in_invoice", "In invoice"),
            ("out_refund", "Out refund"),
            ("in_refund", "In refund"),
            ("out_debit", "Out debit"),
            ("in_debit", "In debit"),
        ],
    )
    date_accounting = fields.Date(related="retention_id.date_accounting", store=True)
    # Para campos no monetarios, puedes usar precisiones estándar o personalizadas.
    # Si "Tasa" no es un registro en decimal.precision, puedes usar una estándar como 'Account'
    aliquot = fields.Float() # La precisión por defecto suele ser suficiente
    retention_rate = fields.Float(store=True)

    # Para campos monetarios, Odoo 18 lo gestiona automáticamente
    # Simplemente elimina el parámetro 'digits'
    invoice_amount = fields.Float(
        string="Taxable income",
        digits=(16, 2),
        compute="_compute_amounts",
        store=True,
        readonly=False,
    )
    retention_amount = fields.Float(
        string="Retention amount",
        compute="_compute_retention_amount",
        store=True,
        readonly=False,
    )
#    aliquot = fields.Float(digits=(16, 2))
    amount_tax_ret = fields.Float(string="Retained tax", digits=(16, 2))
    base_ret = fields.Float("Retained base", digits=(16, 2))
    imp_ret = fields.Float(string="tax incurred", digits=(16, 2))
    retention_rate = fields.Float(store=True, digits="Tasa")
    move_id = fields.Many2one("account.move", "move", ondelete="cascade", store=True)
    is_retention_client = fields.Boolean(default=True)
    display_invoice_number = fields.Char(
        string="Invoice Number", compute="_compute_display_invoice_number", store=True
    )

    @api.depends('move_id', 'move_id.name', 'move_id.ref', 'move_id.move_type')
    def _compute_display_invoice_number(self):
        for line in self:
            if line.move_id:
                if line.move_id.move_type in ['out_invoice', 'out_refund', 'out_debit']:
                    line.display_invoice_number = line.move_id.name
                else:
                    line.display_invoice_number = line.move_id.ref or line.move_id.name or '--'
            else:
                line.display_invoice_number = '--'
    invoice_total = fields.Float(string="Total invoiced", digits="Tasa", store=True)
    iva_amount = fields.Float(string="IVA", digits=(16, 2))

    foreign_retention_amount = fields.Float(
        digits="Tasa", compute="_compute_retention_amount", store=True, readonly=False
    )

    payment_concept_id = fields.Many2one(
        "payment.concept", "Payment concept", ondelete="cascade", index=True
    )
    code = fields.Char(
        related="payment_concept_id.line_payment_concept_ids.code"
    )
    code_visible = fields.Boolean(
        related='company_id.code_visible')
    economic_activity_id = fields.Many2one(
        "economic.activity",
        ondelete="cascade",
        compute="_compute_economic_activity_id",
        readonly=False,
        store=True,
        index=True,
    )

    payment_id = fields.Many2one("account.payment", "Payment", index=True)
    payment_date = fields.Date(related="payment_id.date", store=True)
    payment_journal_id = fields.Many2one(
        "account.journal",
        "Payment journal",
        ondelete="cascade",
        index=True,
        related="payment_id.journal_id",
    )

    related_pay_from = fields.Float(
        string="Pays from",
        compute="_compute_related_fields",
        store=True,
    )
    related_percentage_tax_base = fields.Float(
        string="% tax base",
        compute="_compute_related_fields",
        store=True,
        readonly=False,
    )
    related_percentage_fees = fields.Float(
        string="% tariffs",
        compute="_compute_related_fields",
        store=True,
    )
    related_amount_subtract_fees = fields.Float(
        string="Amount subtract tariffs",
        compute="_compute_related_fields",
        store=True,
    )

    # Montos en VEF (Bs.) — Regla universal venezolana
    foreign_invoice_amount = fields.Float(
        string="Base Imponible (Bs.)", compute="_compute_amounts", store=True, readonly=False
    )
    foreign_invoice_total = fields.Float(string="Total Factura (Bs.)")
    foreign_iva_amount = fields.Float(string="IVA (Bs.)")
    foreign_currency_rate = fields.Float(string="Tasa (Extensión de Pago)")
    foreign_currency_inverse_rate = fields.Float(string="Inverse Rate")

    # Después de la definición de tus fields (campos) y antes de tus @api.depends o @api.onchange existentes.
    # Por ejemplo, puedes ponerlo después de 'foreign_currency_rate = fields.Float(string="Rate")'

    @api.onchange('move_id')
    def _onchange_move_id_populate_fields(self):
        """
        Popula los campos de la línea de retención basados en la factura seleccionada (move_id).
        Este método se ejecuta inmediatamente al seleccionar la factura.
        """
        if self.move_id:
            invoice = self.move_id

            self.invoice_total = invoice.amount_total
            self.invoice_amount = invoice.amount_untaxed
            
            # Identificar las monedas dinámicamente
            if self.retention_id:
                base_currency, alternate_currency, vef_currency, foreign_currency = self.retention_id._get_retention_currencies()
            else:
                base_currency = self.env.company.currency_id
                alternate_currency = getattr(self.env.company, 'currency_id_dif', self.env['res.currency'])
                vef_currency = alternate_currency if alternate_currency.name in ('VEF', 'VES') else base_currency

            # Regla v62: Montos en VEF (Bolívares) con tasa dual explícita
            invoice_rate = invoice.tax_today or 1.0
            today_rate = getattr(self.env.company, 'currency_id_dif', self.env['res.currency']).inverse_rate or 1.0
            used_rate = today_rate if (self.retention_id and self.retention_id.use_today_rate) else invoice_rate
            
            invoice_currency = invoice.currency_id
            invoice_is_in_vef = invoice_currency.name in ('VEF', 'VES')
            
            if invoice_is_in_vef:
                self.foreign_invoice_amount = invoice.amount_untaxed
                self.foreign_invoice_total = invoice.amount_total
            else:
                self.foreign_invoice_amount = getattr(invoice, 'amount_untaxed_bs', 0.0) or (invoice.amount_untaxed * used_rate)
                self.foreign_invoice_total = getattr(invoice, 'amount_total_bs', 0.0) or (invoice.amount_total * used_rate)
            
            # Poblar los campos de IVA directamente (Estimación proporcional si no hay campo signed de tax)
            self.iva_amount = invoice.amount_tax
            self.foreign_iva_amount = self.foreign_invoice_total - self.foreign_invoice_amount

            self.foreign_currency_rate = used_rate
            self.foreign_currency_inverse_rate = 1.0 / used_rate if used_rate else 0.0

            self.is_retention_client = invoice.move_type in ('out_invoice', 'out_refund', 'out_debit')
            self.invoice_type = invoice.move_type

        else:
            # Limpiar los campos si no hay factura seleccionada
            self.invoice_total = 0.0
            self.foreign_invoice_total = 0.0
            self.invoice_amount = 0.0
            self.foreign_invoice_amount = 0.0
            self.iva_amount = 0.0
            self.foreign_iva_amount = 0.0
            self.foreign_currency_rate = 0.0
            self.is_retention_client = False
            self.invoice_type = False
            self.retention_amount = 0.0
            self.foreign_retention_amount = 0.0
            self.aliquot = 0.0
            self.related_pay_from = 0.0
            self.related_percentage_tax_base = 0.0
            self.related_percentage_fees = 0.0
            self.related_amount_subtract_fees = 0.0
            self.payment_concept_id = False
            self.economic_activity_id = False

    @api.depends("retention_id.type_retention", "move_id")
    def _compute_name(self):
        for record in self:
            if record.name:
                continue
            names = {
                "islr": _("ISLR Retention"),
                "iva": _("IVA Retention"),
                "municipal": _("Municipal Retention"),
            }
            type_retention = "islr"
            if record.retention_id.type_retention:
                type_retention = record.retention_id.type_retention
            elif record.move_id:
                if record in record.move_id.retention_iva_line_ids:
                    type_retention = "iva"
                elif record in record.move_id.retention_municipal_line_ids:
                    type_retention = "municipal"

            record.name = names.get(type_retention, _("Retention"))

    @api.depends("retention_id", "move_id")
    def _compute_economic_activity_id(self):
        for line in self:
            if line.economic_activity_id:
                continue
            if line.retention_id and line.retention_id.type_retention == "municipal":
                line.economic_activity_id = line.retention_id.partner_id.economic_activity_id
            if line.move_id and line.id in line.move_id.retention_municipal_line_ids.ids:
                line.economic_activity_id = line.move_id.partner_id.economic_activity_id

    def unlink(self):
        for record in self:
            record.payment_id.unlink()
        return super().unlink()

    # =========== CAMBIO AQUÍ ===========
    @api.onchange("payment_concept_id", "move_id")
    @api.depends("payment_concept_id", "move_id")
    def _compute_related_fields(self):
        """
        Calcula los campos relacionados con el concepto de pago para retenciones ISLR.
        Aplica la regla universal venezolana: los montos siempre se expresan en VEF (Bs.).
        """
        lines_from_islr_retention = self.filtered(
            lambda l: (not l.retention_id or l.retention_id.type_retention == "islr")
        )

        for record in lines_from_islr_retention:
            if not record.move_id:
                continue

            tax_totals = record.move_id.tax_totals or {}

            # Identificar las monedas dinámicamente
            if record.retention_id:
                base_currency, alternate_currency, vef_currency, foreign_currency = record.retention_id._get_retention_currencies()
            else:
                base_currency = record.env.company.currency_id
                alternate_currency = getattr(record.env.company, 'currency_id_dif', record.env['res.currency'])
                vef_currency = alternate_currency if alternate_currency.name in ('VEF', 'VES') else base_currency

            # Tasa dual
            invoice_rate = record.move_id.tax_today or 1.0
            today_rate = getattr(record.env.company, 'currency_id_dif', record.env['res.currency']).inverse_rate or 1.0
            used_rate = today_rate if (record.retention_id and record.retention_id.use_today_rate) else invoice_rate

            invoice_currency = record.move_id.currency_id
            invoice_is_in_vef = invoice_currency.name in ('VEF', 'VES')

            # Montos en moneda empresa (Bs. o USD)
            if invoice_is_in_vef:
                amount_untaxed_company = record.move_id.amount_untaxed / used_rate if used_rate else record.move_id.amount_untaxed
                amount_total_company = record.move_id.amount_total / used_rate if used_rate else record.move_id.amount_total
                vef_untaxed = record.move_id.amount_untaxed
                vef_total = record.move_id.amount_total
            else:
                amount_untaxed_company = record.move_id.amount_untaxed
                amount_total_company = record.move_id.amount_total
                vef_untaxed = getattr(record.move_id, 'amount_untaxed_bs', 0.0) or (record.move_id.amount_untaxed * used_rate)
                vef_total = getattr(record.move_id, 'amount_total_bs', 0.0) or (record.move_id.amount_total * used_rate)

            # Asignar valores
            record.invoice_total = amount_total_company
            record.foreign_invoice_total = vef_total
            record.invoice_amount = amount_untaxed_company
            record.foreign_invoice_amount = vef_untaxed
            record.foreign_currency_rate = used_rate
            record.foreign_currency_inverse_rate = 1.0 / used_rate if used_rate else 0.0

            # Si no hay concepto de pago, no continuamos
            if not record.payment_concept_id:
                continue

            if not record.move_id.partner_id.type_person_id and not record.move_id.partner_id.commercial_partner_id.type_person_id:
                _logger.warning(f"El partner {record.move_id.partner_id.name} no tiene tipo de persona asignado")
                continue

            partner_person_type = record.move_id.partner_id.type_person_id or record.move_id.partner_id.commercial_partner_id.type_person_id
            partner_person_type_id = partner_person_type.id if partner_person_type else False

            payment_concept = record.payment_concept_id.line_payment_concept_ids
            for line in payment_concept:
                if partner_person_type_id and partner_person_type_id == line.type_person_id.id:
                    record.related_pay_from = line.pay_from or 0.0
                    record.related_percentage_tax_base = line.percentage_tax_base or 0.0
                    record.related_percentage_fees = line.tariff_id.percentage if line.tariff_id else 0.0
                    record.related_amount_subtract_fees = line.tariff_id.amount_subtract if line.tariff_id else 0.0

                    record.invoice_amount = amount_untaxed_company
                    record.foreign_invoice_amount = vef_untaxed
                    break  # Salir al encontrar la primera coincidencia
                
    def _compute_line_amounts(self):
        for record in self:
            if not record.move_id:
                record.invoice_amount = 0.0
                record.invoice_total = 0.0
                record.iva_amount = 0.0
                record.retention_amount = 0.0
                record.foreign_invoice_amount = 0.0
                record.foreign_invoice_total = 0.0
                record.foreign_iva_amount = 0.0
                record.foreign_retention_amount = 0.0
                record.foreign_currency_rate = 1.0
                continue

            invoice = record.move_id

            if record.retention_id:
                base_currency, alternate_currency, vef_currency, foreign_currency = record.retention_id._get_retention_currencies()
            else:
                base_currency = record.env.company.currency_id
                alternate_currency = getattr(record.env.company, 'currency_id_dif', record.env['res.currency'])
                vef_currency = alternate_currency if alternate_currency.name in ('VEF', 'VES') else base_currency

            invoice_currency = invoice.currency_id
            invoice_is_vef = vef_currency and (invoice_currency == vef_currency)

            invoice_rate = record.foreign_currency_rate or invoice.tax_today or 1.0
            today_rate = getattr(record.env.company, 'currency_id_dif', record.env['res.currency']).inverse_rate or 1.0
            used_rate = today_rate if (record.retention_id and record.retention_id.use_today_rate) else invoice_rate
            used_rate = used_rate or 1.0

            if invoice_is_vef:
                bs_untaxed = abs(invoice.amount_untaxed)
                bs_total = abs(invoice.amount_total)
                bs_iva = abs(invoice.amount_tax)
                usd_untaxed = bs_untaxed / used_rate
                usd_total = bs_total / used_rate
                usd_iva = bs_iva / used_rate
            else:
                usd_untaxed = abs(invoice.amount_untaxed)
                usd_total = abs(invoice.amount_total)
                usd_iva = abs(invoice.amount_tax)
                bs_untaxed = getattr(invoice, 'amount_untaxed_bs', 0.0) or (usd_untaxed * used_rate)
                bs_total = getattr(invoice, 'amount_total_bs', 0.0) or (usd_total * used_rate)
                bs_iva = bs_total - bs_untaxed

            type_retention = record.retention_id.type_retention if record.retention_id else False
            if not type_retention:
                if record.payment_concept_id:
                    type_retention = 'islr'
                elif record.economic_activity_id:
                    type_retention = 'municipal'
                else:
                    type_retention = 'iva'

            withholding_amount = record.related_percentage_tax_base or (invoice.partner_id.withholding_type_id.value if invoice.partner_id.withholding_type_id else 0.0)
            if not withholding_amount and record.retention_id and record.retention_id.type == 'in_invoice':
                withholding_amount = 75.0

            computed_invoice_amount = usd_untaxed
            computed_foreign_invoice_amount = bs_untaxed
            computed_invoice_total = usd_total
            computed_iva_amount = usd_iva
            computed_foreign_invoice_total = bs_total
            computed_foreign_iva_amount = bs_iva
            computed_foreign_currency_rate = used_rate

            computed_retention_amount = 0.0
            computed_foreign_retention_amount = 0.0

            if type_retention == 'iva':
                computed_retention_amount = computed_iva_amount * (withholding_amount / 100.0)
                computed_foreign_retention_amount = computed_foreign_iva_amount * (withholding_amount / 100.0)
            elif type_retention == 'islr':
                tax_base_pct = record.related_percentage_tax_base or 100.0
                fee_pct = record.aliquot if record.aliquot else (record.related_percentage_fees or 0.0)
                subtract = record.related_amount_subtract_fees or 0.0

                computed_retention_amount = (
                    (computed_invoice_amount * (tax_base_pct / 100))
                    * (fee_pct / 100)
                ) - (subtract / used_rate if used_rate else 0.0)
                computed_retention_amount = max(computed_retention_amount, 0.0)

                computed_foreign_retention_amount = (
                    (computed_foreign_invoice_amount * (tax_base_pct / 100))
                    * (fee_pct / 100)
                ) - subtract
                computed_foreign_retention_amount = max(computed_foreign_retention_amount, 0.0)
            elif type_retention == 'municipal':
                aliquot = record.economic_activity_id.aliquot or record.aliquot or 0.0
                computed_retention_amount = computed_invoice_amount * aliquot / 100.0
                computed_foreign_retention_amount = computed_foreign_invoice_amount * aliquot / 100.0

            record.invoice_amount = computed_invoice_amount
            record.invoice_total = computed_invoice_total
            record.iva_amount = computed_iva_amount
            record.foreign_invoice_amount = computed_foreign_invoice_amount
            record.foreign_invoice_total = computed_foreign_invoice_total
            record.foreign_iva_amount = computed_foreign_iva_amount
            record.foreign_currency_rate = computed_foreign_currency_rate
            if computed_retention_amount > 0 or not record.retention_amount:
                record.retention_amount = computed_retention_amount
            if computed_foreign_retention_amount > 0 or not record.foreign_retention_amount:
                record.foreign_retention_amount = computed_foreign_retention_amount

    @api.depends("move_id", "retention_id.use_today_rate")
    def _compute_amounts(self):
        self._compute_line_amounts()

    @api.onchange(
        "invoice_amount",
        "foreign_invoice_amount",
        "related_percentage_tax_base",
        "related_percentage_fees",
        "related_amount_subtract_fees",
        "foreign_currency_rate",
    )
    @api.depends(
        "invoice_amount",
        "foreign_invoice_amount",
        "related_percentage_tax_base",
        "related_percentage_fees",
        "related_amount_subtract_fees",
        "foreign_currency_rate",
        "move_id",
    )
    def _compute_retention_amount(self):
        """
        Calcula el monto de retención ISLR para líneas de proveedor.
        Regla universal venezolana:
        - retention_amount: en la moneda de la empresa
        - foreign_retention_amount: SIEMPRE en VEF (Bs.)
          foreign_invoice_amount ya fue asignado en VEF por _compute_related_fields
        """
        islr_retention_lines = self.filtered(
            lambda l: (not l.retention_id and l.payment_concept_id)
            or (l.retention_id.type_retention == "islr")
        )
        for record in islr_retention_lines:
            used_rate = record.foreign_currency_rate or record.move_id.tax_today or 1.0
            subtract = record.related_amount_subtract_fees

            # --- Control acumulativo del sustraendo (Punto 8) ---
            # Si la empresa tiene activado islr_subtract_once_per_month,
            # verificamos si ya existe una retención emitida en el mismo mes
            # para el mismo partner con sustraendo aplicado.
            if subtract > 0 and record.retention_id and record.retention_id.type == "in_invoice" and record.retention_id.company_id.islr_subtract_once_per_month:
                date_acc = record.retention_id.date_accounting
                if date_acc:
                    first_of_month = date_acc.replace(day=1)
                    existing = self.env['account.retention.line'].search([
                        ('retention_id.state', '=', 'emitted'),
                        ('retention_id.type_retention', '=', 'islr'),
                        ('retention_id.partner_id', '=', record.retention_id.partner_id.id),
                        ('retention_id.date_accounting', '>=', first_of_month),
                        ('retention_id.date_accounting', '<=', date_acc),
                        ('related_amount_subtract_fees', '>', 0),
                        ('id', '!=', record.id),
                    ], limit=1)
                    if existing:
                        subtract = 0.0  # Sustraendo ya aplicado este mes a este RIF

            # Retención en moneda empresa
            record.retention_amount = (
                (record.invoice_amount * (record.related_percentage_tax_base / 100))
                * (record.related_percentage_fees / 100)
            ) - (subtract / used_rate if used_rate else 0.0)

            # Retención en VEF (siempre — foreign_invoice_amount ya está en VEF)
            record.foreign_retention_amount = (
                (record.foreign_invoice_amount * (record.related_percentage_tax_base / 100))
                * (record.related_percentage_fees / 100)
            ) - subtract


    @api.onchange("economic_activity_id", "move_id")
    def onchange_economic_activity_id(self):
        """
        Computes the aliquot of the line when the economic activity is changed for the retentions
        of municipal type.
        """
        municipal_lines = self.filtered(
            lambda l: (not l.retention_id or l.retention_id.type_retention == "municipal")
            and l.economic_activity_id and l.move_id
        )

        for record in municipal_lines:
            record.invoice_amount = record.move_id.amount_untaxed
            record.foreign_invoice_amount = getattr(record.move_id, 'amount_untaxed_bs', 0.0) or (record.move_id.amount_untaxed * (record.move_id.foreign_rate or 1.0))

            record.iva_amount = record.move_id.amount_tax
            record.foreign_iva_amount = getattr(record.move_id, 'amount_tax_bs', 0.0) or (record.move_id.amount_tax * (record.move_id.foreign_rate or 1.0))

            record.invoice_total = record.move_id.amount_total
            record.foreign_invoice_total = getattr(record.move_id, 'amount_total_bs', 0.0) or (record.move_id.amount_total * (record.move_id.foreign_rate or 1.0))
            record.foreign_currency_rate = record.move_id.foreign_rate or 1.0

            record.aliquot = record.economic_activity_id.aliquot
            record.retention_amount = record.invoice_amount * record.aliquot / 100
            record.foreign_retention_amount = record.foreign_invoice_amount * record.aliquot / 100

    @api.onchange("invoice_amount", "foreign_invoice_amount", "aliquot")
    def onchange_municipal_invoice_amount(self):
        """
        Computes the retention amount when the invoice amount or the aliquot are changed for the
        retentions of municipal type.
        """
        for record in self.filtered(
            lambda l: (not l.retention_id and l.economic_activity_id)
            or (l.retention_id and l.retention_id.type_retention == "municipal")
        ):
            record.retention_amount = record.invoice_amount * record.aliquot / 100
            record.foreign_retention_amount = record.foreign_invoice_amount * record.aliquot / 100

    @api.onchange("retention_amount", "invoice_amount")
    def onchange_retention_amount(self):
        if self.env.context.get("noonchange"):
            return
        for line in self.filtered(lambda l: not l.retention_id or l.retention_id.type == "out_invoice"):
            if line.move_id and line.move_id.foreign_inverse_rate:
                ctx = self.with_context(noonchange=True).env.context
                if not line.retention_id or line.retention_id.type_retention in ("islr", "municipal"):
                    line.with_context(ctx).foreign_invoice_amount = line.invoice_amount * line.move_id.foreign_inverse_rate
                line.with_context(ctx).foreign_retention_amount = line.retention_amount * line.move_id.foreign_inverse_rate

    @api.onchange("foreign_retention_amount", "foreign_invoice_amount")
    def onchange_foreign_retention_amount(self):
        if self.env.context.get("noonchange"):
            return
        for line in self.filtered(lambda l: not l.retention_id or l.retention_id.type == "out_invoice"):
            if line.move_id and line.move_id.foreign_rate:
                ctx = self.with_context(noonchange=True).env.context
                if not line.retention_id or line.retention_id.type_retention in ("islr", "municipal"):
                    line.with_context(ctx).invoice_amount = line.foreign_invoice_amount * (1 / line.move_id.foreign_rate)
                line.with_context(ctx).retention_amount = line.foreign_retention_amount * (1 / line.move_id.foreign_rate)

    # =========== CAMBIO AQUÍ ===========
    @api.constrains(
        "retention_amount",
        "foreign_retention_amount",
        "move_id"
    )
    def _constraint_amounts(self):
        for record in self:
            if record.retention_id and record.retention_id.state == 'draft':
                continue
                
            if record.retention_amount == 0 and record.foreign_retention_amount == 0:
                raise ValidationError(_("You cannot create a retention line with a zero retention amount."))

            is_client_retention = record.retention_id and record.retention_id.type == "out_invoice"

            if is_client_retention and record.move_id:
                limit_amount = abs(record.move_id.amount_residual_signed) if record.move_id.currency_id != record.company_currency_id else record.move_id.amount_residual
                if record.retention_amount > limit_amount:
                    raise ValidationError(
                        _("The total amount of the retention is greater than the residual amount of the invoice.")
                    )

    def get_invoice_paid_amount_not_related_with_retentions(self):
        """
        Returns the amount paid on the invoice that is not related with the retentions for the ISLR
        supplier retention lines.
        """
        # This method seems to calculate for a single line, but iterates. Refactoring for clarity.
        # It should likely operate on `self` which could be a recordset.
        # Assuming `self` is a single record for the logic to make sense.
        self.ensure_one()
        line = self
        
        if not (line.retention_id and line.retention_id.type_retention == 'islr'):
            return 0.0

        payable_line = line.move_id.line_ids.filtered(
            lambda l: l.account_id.account_type == "liability_payable" and l.credit > 0
        )
        if not payable_line:
            return 0.0

        partials = self.env["account.partial.reconcile"].search([
            ('credit_move_id', '=', payable_line[0].id)
        ])
        
        retention_payments = partials.mapped('debit_move_id.payment_id').filtered('is_retention')
        retention_payment_moves = retention_payments.mapped('move_id.line_ids')

        non_retention_partials = partials.filtered(lambda p: p.debit_move_id not in retention_payment_moves)
        
        invoice_paid_amount = 0.0
        for partial in non_retention_partials:
            # Logic to sum amounts in company currency
            if partial.debit_currency_id == self.env.company.currency_id:
                invoice_paid_amount += partial.amount
            else:
                # Fallback to company currency amount on the partial
                invoice_paid_amount += partial.amount


        return invoice_paid_amount
