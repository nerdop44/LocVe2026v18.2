from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    currency_id_dif = fields.Many2one(
        "res.currency",
        string="Moneda Ref.",
        related="order_id.currency_id_dif",
        store=False, readonly=True
    )

    price_unit_dif = fields.Monetary(
        string='P. Unit. Ref.',
        currency_field='currency_id_dif',
        compute='_compute_price_dif_sol',
        store=False
    )

    price_subtotal_dif = fields.Monetary(
        string='Subtotal Ref.',
        currency_field='currency_id_dif',
        compute='_compute_price_dif_sol',
        store=False
    )

    @api.depends('price_unit', 'price_subtotal', 'order_id.tasa_referencial', 'order_id.currency_id')
    def _compute_price_dif_sol(self):
        for line in self:
            tasa = line.order_id.tasa_referencial
            if tasa and tasa > 0:
                if line.order_id.currency_id == line.order_id.currency_id_dif:
                    line.price_unit_dif = line.price_unit
                    line.price_subtotal_dif = line.price_subtotal
                else:
                    line.price_unit_dif = line.price_unit / tasa
                    line.price_subtotal_dif = line.price_subtotal / tasa
            else:
                line.price_unit_dif = 0.0
                line.price_subtotal_dif = 0.0

    @api.constrains('price_unit', 'discount')
    def _check_price_unit_positive(self):
        for line in self:
            if not line.display_type:
                if line.price_unit <= 0.0 and line.discount < 100.0:
                    line_name = line.name or (line.product_id and line.product_id.name) or 'Línea'
                    raise ValidationError(_(
                        "Normativa SENIAT (Providencia 0071): No está permitido registrar líneas con Precio Unitario en 0.0 o negativo en '%s'.\n\n"
                        "Si desea entregar un bien o servicio a título gratuito (obsequio, bonificación o muestra sin valor comercial), "
                        "debe ingresar el Precio Unitario de lista de referencia (> 0.0) y aplicar un Descuento del 100%% para cumplir "
                        "con la exigencia fiscal del SENIAT."
                    ) % line_name)

    @api.constrains('tax_id')
    def _check_single_tax(self):
        for line in self:
            if not line.display_type and len(line.tax_id) > 1:
                line_name = line.name or (line.product_id and line.product_id.name) or 'Línea'
                raise ValidationError(_("No se permite aplicar más de una alícuota de impuesto a la línea '%s'. Para cambiar la alícuota, primero debe remover la anterior.") % line_name)


