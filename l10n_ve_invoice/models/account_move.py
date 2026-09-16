from datetime import datetime
import json
import logging

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import format_date

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
   # _name = "account.move"
    #_inherit = ["account.move"]
    _inherit = "account.move"

    correlative = fields.Char("Control Number", copy=False, help="Sequence control number")
    invoice_reception_date = fields.Date(
        "Reception Date",
        help="Indicates when the invoice was received by the client/company",
        tracking=True,
    )
    last_payment_date = fields.Date(compute="_compute_payment_dates", store=True)
    first_payment_date = fields.Date(compute="_compute_payment_dates", store=True)
    is_contingency = fields.Boolean(related="journal_id.is_contingency")
    l10n_ve_is_free_form = fields.Boolean(related="journal_id.l10n_ve_is_free_form", string="Is Free Form Journal", readonly=True)

    next_installment_date = fields.Date(compute="_compute_next_installment_date")
    l10n_ve_is_fully_refunded = fields.Boolean(
        string="Factura Totalmente Revertida",
        compute="_compute_l10n_ve_is_fully_refunded",
        store=True,
    )

    @api.depends('state', 'amount_total', 'reversed_entry_id')

    def _compute_l10n_ve_is_fully_refunded(self):
        for move in self:
            if move.move_type in ('out_invoice', 'in_invoice') and move.state == 'posted':
                refunds = self.search([
                    ('reversed_entry_id', '=', move.id),
                    ('state', 'in', ('posted', 'draft')),
                    ('move_type', 'in', ('out_refund', 'in_refund'))
                ])
                total_refunded = sum(refunds.mapped('amount_total'))
                move.l10n_ve_is_fully_refunded = bool(move.amount_total > 0 and total_refunded >= (move.amount_total - 0.01))
            else:
                move.l10n_ve_is_fully_refunded = False

    @api.constrains('invoice_line_ids', 'invoice_line_ids.price_unit', 'invoice_line_ids.discount')
    def _check_move_line_price_unit_positive(self):
        for move in self:
            if move.move_type in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund'):
                for line in move.invoice_line_ids.filtered(lambda l: not l.display_type):
                    if line.price_unit <= 0.0 and line.discount < 100.0:
                        name = line.name or (line.product_id and line.product_id.display_name) or 'Línea de producto'
                        raise ValidationError(_(
                            "Normativa SENIAT (Providencia 0071): No está permitido registrar líneas con Precio Unitario en 0.0 o negativo en '%s'.\n\n"
                            "Si desea entregar un bien o servicio a título gratuito (obsequio, bonificación o muestra sin valor comercial), "
                            "debe ingresar el Precio Unitario de lista de referencia (> 0.0) y aplicar un Descuento del 100%% para cumplir "
                            "con la exigencia fiscal de transparentar la base de referencia exigida por el SENIAT."
                        ) % name)



#    # INICIO DE LAS MODIFICACIONES SUGERIDAS PARA RELACIONAR CON account.retention.line
#    retention_iva_line_ids = fields.One2many(
#        'account.retention.line',
#        'move_id',
#        string='Retenciones de IVA',
#        domain=[('type_retention', '=', 'iva')],
#        readonly=True,
#        copy=False,
#        # Este campo One2many crea la relación inversa para las líneas de retención de IVA.
#        # 'account.retention.line' es el modelo relacionado.
#        # 'move_id' es el campo Many2one en 'account.retention.line' que conecta con este #modelo.
#    )
#    retention_islr_line_ids = fields.One2many(
#        'account.retention.line',
#        'move_id',
#        string='Retenciones de ISLR',
#        domain=[('type_retention', '=', 'islr')],
#        readonly=True,
#        copy=False,
#        # Este campo One2many crea la relación inversa para las líneas de retención de ISLR.
#        # 'account.retention.line' es el modelo relacionado.
#        # 'move_id' es el campo Many2one en 'account.retention.line' que conecta con este #modelo.
#    )
#    retention_municipal_line_ids = fields.One2many(
#        'account.retention.line',
#        'move_id',
#        string='Retenciones Municipales',
#        domain=[('type_retention', '=', 'municipal')],
#        readonly=True,
#        copy=False,
#        # Este campo One2many crea la relación inversa para las líneas de retención #municipales.
#        # 'account.retention.line' es el modelo relacionado.
#        # 'move_id' es el campo Many2one en 'account.retention.line' que conecta con este #modelo.
#    )
#    # FIN DE LAS MODIFICACIONES SUGERIDAS
   
    @api.constrains("correlative", "journal_id.is_contingency")
    def _check_correlative(self):
        AccountMove = self.env["account.move"]
        is_series_invoicing_enabled = self.company_id.group_sales_invoicing_series
        for move in self:
            if not move.is_contingency:
                continue
            if not is_series_invoicing_enabled and not move.correlative:
                raise ValidationError(
                    _(
                        "Contingency journal's invoices should always have a correlative if series "
                        "invoicing is not enabled"
                    )
                )
            repeated_moves = AccountMove.search(
                [
                    ("is_contingency", "=", True),
                    ("id", "!=", move.id),
                    ("correlative", "!=", False),
                    ("correlative", "=", move.correlative),
                    ("journal_id", "=", move.journal_id.id),
                ],
                limit=1,
            )
            if repeated_moves:
                raise UserError(
                    _("The correlative must be unique per journal when using a contingency journal")
                )

    @api.depends("amount_residual")
    def _compute_payment_dates(self):
        def clear_dates(move):
            move.last_payment_date = False
            move.first_payment_date = False

        for move in self:
            if not move.is_invoice(include_receipts=True) and move.state != "posted":
                clear_dates(move)
                continue

            is_invoice_payment_widget = bool(move.invoice_payments_widget)
            if not is_invoice_payment_widget:
                clear_dates(move)
                continue

            payments = move.invoice_payments_widget
            if not payments or not payments.get("content", False):
                clear_dates(move)
                continue

            last_date = False
            first_date = False

            dates = list()

            for payment in payments.get("content"):
                if not self.validate_payment(payment):
                    continue

                dates.append(payment.get("date", False))

            if len(dates) > 0:
                last_date = fields.Date.from_string(max(dates))
                first_date = fields.Date.from_string(min(dates))

            move.last_payment_date = last_date
            move.first_payment_date = first_date

    @api.model
    def validate_payment(self, payment):
        """This function was created to validate payments through external modules"""
        return True

    @api.onchange("invoice_line_ids")
    def _onchange_invoice_line_ids(self):
        """
        Limit the number of products that can be added to the invoice
        """
        if self.invoice_line_ids and self.move_type in ["out_invoice", "out_refund"]:
            max_product_invoice = self.company_id.max_product_invoice
            if len(self.invoice_line_ids) > max_product_invoice:
                raise ValidationError(
                    _("You can not add more than %s products to the invoice." % max_product_invoice)
                )

    @api.depends("filter_partner")
    def _compute_partner_id_domain(self):
        for move in self:
            company_id = move.company_id.id
            extend_domain = [("type", "!=", "private"), ("company_id", "in", (False, company_id))]
            domain = move.get_partner_domain(extend=extend_domain)

            move.update({"partner_id_domain": json.dumps(domain)})

    @api.depends("payment_term_details")
    def _compute_next_installment_date(self):
        lang = self.env["res.lang"].search([("code", "=", self.env.user.lang)])
        date_format = lang.date_format if lang else "%Y-%m-%d"
        for invoice in self:
            invoice.next_installment_date = False
            if not invoice.payment_term_details:
                invoice.next_installment_date = invoice.invoice_date_due
                continue
            for term in invoice.payment_term_details:
                term_date = datetime.strptime(term.get("date", ""), date_format).date()
                if term_date and term_date >= fields.Date.context_today(self):
                    invoice.next_installment_date = term_date
                    break

    def _post(self, soft=True):
        res = super()._post(soft)
        for move in res:
            if move.is_valid_to_sequence():
                move.correlative = move.get_sequence()
        return res

    @api.model
    def is_valid_to_sequence(self) -> bool:
        """
        Check if the invoice satisfies the conditions to associate a new sequence number to its
        correlative.

        Returns:
            True or False whether the invoice already has a sequence number or not.
        """
        journal_type = self.journal_id.type == "sale"
        is_contingency = self.journal_id.is_contingency
        is_series_invoicing_enabled = self.company_id.group_sales_invoicing_series
        is_valid = (
            not self.correlative
            and journal_type
            and (not is_contingency or is_series_invoicing_enabled)
        )

        return is_valid

    @api.model
    def get_sequence(self):
        """
        Allows the invoice to have both a generic sequence
        number or a specific one given certain conditions.

        Returns
        -------
            The next number from the sequence to be assigned.
        """

        self.ensure_one()
        is_series_invoicing_enabled = self.company_id.group_sales_invoicing_series
        sequence = self.env["ir.sequence"].sudo()
        correlative = None

        if is_series_invoicing_enabled:
            correlative = self.journal_id.series_correlative_sequence_id

            if not correlative:
                if self.journal_id.l10n_ve_is_free_form:
                    raise UserError(_("El diario de formas libres '%s' debe tener configurada una secuencia de control de series para poder asignar el correlativo fiscal.") % self.journal_id.name)
                raise UserError(_("The sale's series sequence must be in the selected journal."))
            return correlative.next_by_id(correlative.id)

        correlative = sequence.search(
            [("code", "=", "invoice.correlative"), ("company_id", "=", self.env.company.id)],
            limit=1
        )
        if not correlative:
            correlative = sequence.create(
                {
                    "name": "Número de control",
                    "code": "invoice.correlative",
                    "padding": 5,
                }
            )
        return correlative.next_by_id(correlative.id)

    def _get_tax_totals(self):
        """
        Restauración de Moneda Dual (V72)
        Llama al super() para permitir que account_dual_currency inyecte sus totales.
        Luego asegura que el formateo use el símbolo de la moneda de referencia ($).
        """
        self.ensure_one()
        tax_totals = super()._get_tax_totals()

        # En Odoo 18, si el módulo de moneda dual está activo, inyecta 'foreign_subtotals'
        if 'foreign_subtotals' in tax_totals:
            # Priorizamos currency_id_dif (Odoo 18) sobre secondary_currency_id (obsoleto)
            foreign_currency = getattr(self, 'currency_id_dif', False) or \
                               getattr(self, 'secondary_currency_id', False) or \
                               self.company_id.currency_id_dif
            
            if foreign_currency:
                # Formatear subtotales extranjeros con la moneda de referencia
                for subtotal in tax_totals['foreign_subtotals']:
                    if 'formatted_amount' not in subtotal or 'Bs' in subtotal.get('formatted_amount', ''):
                        subtotal['formatted_amount'] = self.format_monetary(subtotal['amount'], foreign_currency)
                
                # Formatear montos totales extranjeros si existen
                if 'foreign_amount_untaxed' in tax_totals and 'foreign_formatted_amount_untaxed' not in tax_totals:
                     tax_totals['foreign_formatted_amount_untaxed'] = self.format_monetary(tax_totals['foreign_amount_untaxed'], foreign_currency)
                if 'foreign_amount_total' in tax_totals and 'foreign_formatted_amount_total' not in tax_totals:
                     tax_totals['foreign_formatted_amount_total'] = self.format_monetary(tax_totals['foreign_amount_total'], foreign_currency)

        return tax_totals

    # Campos para Guía de Despacho
    l10n_ve_guide_number = fields.Char(string="Número de Guía de Despacho", copy=False)
    l10n_ve_carrier_name = fields.Char(string="Nombre del Transportista")
    l10n_ve_carrier_vat = fields.Char(string="RIF/Cédula del Transportista")
    l10n_ve_vehicle_plate = fields.Char(string="Placa del Vehículo")
    l10n_ve_vehicle_brand = fields.Char(string="Marca/Modelo del Vehículo")
    l10n_ve_starting_point = fields.Text(string="Dirección de Salida (Punto de Partida)")
    l10n_ve_ending_point = fields.Text(string="Dirección de Llegada (Punto de Destino)")

    def action_open_delivery_guide_wizard(self):
        self.ensure_one()
        # Intentar sugerir direcciones por defecto si están vacías
        starting_point = self.l10n_ve_starting_point or ""
        if not starting_point and self.company_id.partner_id:
            partner = self.company_id.partner_id
            parts = [partner.street or "", partner.street2 or "", partner.city or "", partner.state_id.name if partner.state_id else ""]
            starting_point = ", ".join([p for p in parts if p])

        ending_point = self.l10n_ve_ending_point or ""
        if not ending_point and self.partner_id:
            partner = self.partner_id
            parts = [partner.street or "", partner.street2 or "", partner.city or "", partner.state_id.name if partner.state_id else ""]
            ending_point = ", ".join([p for p in parts if p])

        # Retornar acción del wizard
        return {
            'name': 'Datos de Guía de Despacho',
            'type': 'ir.actions.act_window',
            'res_model': 'l10n_ve.delivery.guide.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_move_id': self.id,
                'default_l10n_ve_guide_number': self.l10n_ve_guide_number or self.env['ir.sequence'].next_by_code('stock.picking.delivery.guide') or '',
                'default_l10n_ve_carrier_name': self.l10n_ve_carrier_name,
                'default_l10n_ve_carrier_vat': self.l10n_ve_carrier_vat,
                'default_l10n_ve_vehicle_plate': self.l10n_ve_vehicle_plate,
                'default_l10n_ve_vehicle_brand': self.l10n_ve_vehicle_brand,
                'default_l10n_ve_starting_point': starting_point,
                'default_l10n_ve_ending_point': ending_point,
            }
        }

    @api.constrains('reversed_entry_id', 'move_type', 'journal_id', 'state')
    def _check_free_form_refund_constraints(self):
        for move in self:
            if move.move_type == 'out_refund' and move.journal_id.l10n_ve_is_free_form:
                # 1. Requiere factura afectada
                if not move.reversed_entry_id:
                    raise ValidationError(_(
                        "Las Notas de Crédito sobre Formas Libres requieren obligatoriamente una Factura Afectada asociada."
                    ))
                
                # 2. No se permiten cruces cruzados: origen debe ser forma libre también
                if not move.reversed_entry_id.journal_id.l10n_ve_is_free_form:
                    raise ValidationError(_(
                        "No se puede emitir una Nota de Crédito en Forma Libre para una factura original que no se emitió bajo el mismo medio (Forma Libre)."
                    ))
                
                # 3. Comprobar si la factura afectada proviene de POS (máquina fiscal)
                pos_order = self.env['pos.order'].search([('account_move', '=', move.reversed_entry_id.id)], limit=1)
                if pos_order:
                    raise ValidationError(_(
                        "No se puede aplicar una Nota de Crédito en Forma Libre a una factura originada en Punto de Venta (Máquina Fiscal)."
                    ))

    @api.constrains('invoice_line_ids', 'invoice_line_ids.tax_ids')
    def _check_refund_taxes(self):
        for move in self:
            if move.move_type == 'out_refund' and move.journal_id.l10n_ve_is_free_form and move.reversed_entry_id:
                orig_taxes = {}
                for line in move.reversed_entry_id.invoice_line_ids:
                    if line.product_id:
                        orig_taxes[line.product_id.id] = line.tax_ids.ids
                
                for line in move.invoice_line_ids:
                    if line.display_type == 'product' and line.product_id:
                        orig_tax = orig_taxes.get(line.product_id.id)
                        if orig_tax is not None and set(line.tax_ids.ids) != set(orig_tax):
                            raise ValidationError(_(
                                "No se permite modificar los impuestos en una Nota de Crédito sobre Forma Libre. "
                                "Debe mantener la alícuota fiscal histórica de la factura original."
                            ))

    @api.constrains('invoice_line_ids', 'invoice_line_ids.price_unit', 'invoice_line_ids.quantity', 'reversed_entry_id')
    def _check_refund_amounts_and_quantities(self):
        for move in self:
            if move.move_type in ('out_refund', 'in_refund') and move.reversed_entry_id:
                orig_move = move.reversed_entry_id
                
                # 1. Total del reembolso no puede superar el monto de la factura origen
                other_refunds = self.search([
                    ('reversed_entry_id', '=', orig_move.id),
                    ('id', '!=', move.id),
                    ('state', '!=', 'cancel'),
                    ('move_type', 'in', ('out_refund', 'in_refund'))
                ])
                refunded_so_far = sum(other_refunds.mapped('amount_total'))
                if (refunded_so_far + move.amount_total) > (orig_move.amount_total + 0.01):
                    raise ValidationError(_(
                        "El monto total de la Nota de Crédito (%.2f) excede el monto remanente disponible de la Factura Origen %s (Monto Factura: %.2f, Revertido Previamente: %.2f)."
                    ) % (move.amount_total, orig_move.name, orig_move.amount_total, refunded_so_far))

                # 2. Validación por línea: precio unitario y cantidad no pueden ser mayores al origen
                orig_lines_by_prod = {}
                for line in orig_move.invoice_line_ids:
                    if not line.display_type and line.product_id:
                        if line.product_id.id not in orig_lines_by_prod:
                            orig_lines_by_prod[line.product_id.id] = []
                        orig_lines_by_prod[line.product_id.id].append(line)

                for line in move.invoice_line_ids:
                    if not line.display_type and line.product_id:
                        matching_orig = orig_lines_by_prod.get(line.product_id.id)
                        if matching_orig:
                            max_orig_price = max(l.price_unit for l in matching_orig)
                            total_orig_qty = sum(l.quantity for l in matching_orig)
                            
                            if line.price_unit > (max_orig_price + 0.0001):
                                raise ValidationError(_(
                                    "No se puede aumentar el precio unitario del producto '%s' en la Nota de Crédito (%.2f). "
                                    "El precio máximo de la factura original es %.2f."
                                ) % (line.product_id.name, line.price_unit, max_orig_price))
                            
                            other_refund_lines = self.env['account.move.line'].search([
                                ('move_id', 'in', other_refunds.ids),
                                ('product_id', '=', line.product_id.id),
                                ('display_type', '=', False)
                            ])
                            qty_refunded_so_far = sum(other_refund_lines.mapped('quantity'))
                            if (qty_refunded_so_far + line.quantity) > (total_orig_qty + 0.0001):
                                raise ValidationError(_(
                                    "La cantidad del producto '%s' en la Nota de Crédito (%.2f + %.2f previas) excede la cantidad de la factura original (%.2f)."
                                ) % (line.product_id.name, line.quantity, qty_refunded_so_far, total_orig_qty))

    def action_reverse(self):
        for move in self:
            if move.l10n_ve_is_fully_refunded:
                raise ValidationError(_("La factura %s ya ha sido revertida por completo y no se puede generar otra Nota de Crédito.") % move.name)
        return super().action_reverse()


    def action_open_void_control_wizard(self):
        self.ensure_one()
        return {
            'name': 'Anular Correlativo por Atasco',
            'type': 'ir.actions.act_window',
            'res_model': 'l10n_ve.void.control.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_move_id': self.id,
            }
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'correlative' in vals and vals['correlative']:
                vals['correlative'] = self._format_control_number(vals['correlative'])
        return super(AccountMove, self).create(vals_list)

    def write(self, vals):
        if 'correlative' in vals and vals['correlative']:
            vals['correlative'] = self._format_control_number(vals['correlative'])
        return super(AccountMove, self).write(vals)

    def _format_control_number(self, val):
        if not val:
            return val
        # Limpiar cualquier caracter que no sea dígito
        digits = ''.join(c for c in val if c.isdigit())
        if not digits:
            return val
        # Rellenar con ceros a la izquierda hasta 8 dígitos y anteponer '00-'
        return f"00-{digits[-8:].zfill(8)}"

    @api.constrains('reversed_entry_id', 'state')
    def _check_invoice_not_fully_refunded(self):
        for move in self:
            if move.move_type in ('out_refund', 'in_refund') and move.state == 'posted' and move.reversed_entry_id:
                invoice = move.reversed_entry_id
                # Buscar todas las notas de crédito publicadas para esta factura
                refunds = self.search([
                    ('reversed_entry_id', '=', invoice.id),
                    ('state', '=', 'posted'),
                    ('move_type', '=', move.move_type)
                ])
                total_refunded = sum(refunds.mapped('amount_total'))
                if total_refunded > invoice.amount_total + 0.01:
                    raise ValidationError(_("La factura '%s' ya ha sido totalmente afectada por otra(s) Nota(s) de Crédito. No es posible emitir reembolsos que excedan el monto total de la factura original.") % invoice.name)

    @api.constrains('invoice_line_ids', 'reversed_entry_id', 'state')
    def _check_credit_note_lines(self):
        for move in self:
            if move.move_type in ('out_refund', 'in_refund') and move.reversed_entry_id and move.state == 'posted':
                invoice = move.reversed_entry_id
                
                # Mapear cantidades facturadas por producto
                original_qty = {}
                for line in invoice.invoice_line_ids:
                    if not line.display_type and line.product_id:
                        original_qty[line.product_id.id] = original_qty.get(line.product_id.id, 0.0) + line.quantity
                
                # Buscar cantidades ya reembolsadas en notas de crédito publicadas
                other_refunds = self.search([
                    ('reversed_entry_id', '=', invoice.id),
                    ('state', '=', 'posted'),
                    ('move_type', '=', move.move_type)
                ])
                
                refund_qty = {}
                for r in other_refunds:
                    for line in r.invoice_line_ids:
                        if not line.display_type and line.product_id:
                            prod_id = line.product_id.id
                            refund_qty[prod_id] = refund_qty.get(prod_id, 0.0) + line.quantity
                
                # Validar cada línea de la nota de crédito actual
                for line in move.invoice_line_ids:
                    if not line.display_type and line.product_id:
                        prod_id = line.product_id.id
                        if prod_id not in original_qty:
                            raise ValidationError(_("No se permite agregar el producto '%s' a la Nota de Crédito, ya que no forma parte de la factura original.") % line.product_id.name)
                        
                        total_ref_qty = refund_qty.get(prod_id, 0.0)
                        if total_ref_qty > original_qty[prod_id] + 0.0001:
                            raise ValidationError(_("La cantidad total reembolsada del producto '%s' (%s) excede la cantidad facturada originalmente (%s).") % (
                                line.product_id.name, total_ref_qty, original_qty[prod_id]
                            ))


