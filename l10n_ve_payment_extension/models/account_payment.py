from odoo import _, api, fields, models, Command
from odoo.tools.float_utils import float_round
from odoo.exceptions import UserError, ValidationError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    is_retention = fields.Boolean(
        string="Is retention",
        help="Check this box if this payment is a retention",
        default=False,
        copy=False,
    )

    payment_type_retention = fields.Selection(
        [
            ("iva", "IVA"),
            ("islr", "ISLR"),
            ("municipal", "Municipal"),
        ],
        copy=False,
    )

#    # === AÑADIR ESTE BLOQUE / CAMPO FALTANTE ===
#    payment_concept_id = fields.Many2one(
#        'payment.concept',
#        string='Concepto de Pago (ISLR)',
#        help="Concepto de pago de ISLR asociado a este pago de retención.",
#        copy=False,
#    )
    # === FIN DEL BLOQUE A AÑADIR ===
    
#    retention_id = fields.Many2one("account.retention", ondelete="cascade")

    retention_line_ids = fields.One2many(
        "account.retention.line",
        "payment_id",
        string="Retention Lines",
        store=True,
        copy=False,
    )

    invoice_line_ids = fields.Many2many(
        "account.move.line",
        domain="[('tax_ids', '!=', False)]",
        string="Invoice Lines",
        store=True,
        copy=False,
    )

    retention_ref = fields.Char(
        string="Retention reference",
        related="retention_id.number",
        store=True,
        copy=False,
    )

    retention_foreign_amount = fields.Float(
        compute="_compute_retention_foreign_amount", store=True, copy=False
    )

       # === AÑADIR ESTE CAMPO ===
    payment_concept_id = fields.Many2one(
        'payment.concept',
        string='Concepto de Pago (ISLR)',
        help="Concepto de pago de ISLR asociado a este pago de retención.",
        copy=False,
    )
    # ==========================

    retention_id = fields.Many2one("account.retention", ondelete="cascade")


    @api.model
    def _get_next_canceled_name(self, model_name, original_name, company_id):
        """
        Calcula de forma incremental el nombre para un registro cancelado.
        Ejemplo:
        - 1ª vez: original_name + "-canc"
        - 2ª vez: original_name + "-canc-01"
        - 3ª vez: original_name + "-canc-02"
        """
        if not original_name or original_name == "/":
            return original_name

        import re
        base_name = original_name.split("-canc")[0] if "-canc" in original_name else original_name

        domain = [
            ("company_id", "=", company_id),
            ("name", "like", base_name + "-canc%"),
        ]
        records = self.env[model_name].sudo().search(domain)
        existing_names = set(records.mapped("name"))

        candidate_1 = f"{base_name}-canc"
        if candidate_1 not in existing_names:
            return candidate_1

        max_num = 0
        pattern = re.compile(rf"^{re.escape(base_name)}-canc-(\d+)$")
        for name in existing_names:
            match = pattern.match(name)
            if match:
                num = int(match.group(1))
                if num > max_num:
                    max_num = num

        next_num = max_num + 1
        return f"{base_name}-canc-{next_num:02d}"

    @api.depends("date")
    def _compute_rate(self):
        for payment in self:
            if payment.is_retention and payment.foreign_rate:
                continue
            return super()._compute_rate()

    def _synchronize_to_moves(self, changed_fields):
        """
        Override para cambiar el nombre del asiento según el tipo de retención,
        usando el número de retención y el nombre de la factura asociada.
        No se manipulan débito/crédito directamente: Odoo 18 gestiona ese aspecto
        a través de _prepare_move_line_default_vals y el diario configurado.
        """
        res = super()._synchronize_to_moves(changed_fields)

        if self.env.context.get("skip_retention_name_sync"):
            return res

        account_move_name_by_retention_type = {
            "iva": "RIV",
            "islr": "RIS",
            "municipal": "RM",
        }

        for payment in self.filtered("is_retention").with_context(
            skip_account_move_synchronization=True,
            skip_retention_name_sync=True,
        ):
            if not all((payment.retention_line_ids, payment.retention_id.number)):
                continue

            move = payment.move_id
            if not move:
                continue

            # Solo renombrar si el asiento aún está en borrador
            if move.state != 'draft':
                continue

            retention_type = payment.retention_id.type_retention
            prefix = account_move_name_by_retention_type.get(retention_type, "RET")
            target_name = (
                prefix
                + f"-{payment.retention_id.number}"
                + f"-{payment.retention_line_ids[0].move_id.name}"
            )
            if retention_type == "islr" and payment.retention_line_ids[0].payment_concept_id:
                target_name += f"-{payment.retention_line_ids[0].payment_concept_id.name[:5]}"

            # Liberar asientos cancelados existentes que usen este nombre preciso
            conflicts = self.env['account.move'].sudo().search([
                ('company_id', '=', move.company_id.id),
                ('name', '=', target_name),
                ('id', '!=', move.id),
            ])
            if conflicts:
                for conf in conflicts.filtered(lambda m: m.state == 'cancel'):
                    new_conf_name = self._get_next_canceled_name("account.move", conf.name, conf.company_id.id)
                    conf.with_context(skip_retention_name_sync=True).write({"name": new_conf_name})
                    conf.line_ids.with_context(skip_retention_name_sync=True).write({"name": new_conf_name})
                    if conf.payment_id and conf.payment_id.name != new_conf_name:
                        conf.payment_id.with_context(skip_retention_name_sync=True).write({"name": new_conf_name})

            if move.name != target_name:
                move.with_context(skip_retention_name_sync=True).write({"name": target_name})
                move.line_ids.with_context(skip_retention_name_sync=True).write({"name": target_name})
            if payment.name != target_name:
                payment.with_context(skip_retention_name_sync=True).write({"name": target_name})

        return res

    def action_cancel(self):
        for payment in self:
            if payment.name and payment.name != "/" and not payment.name.endswith("-canc") and "-canc-" not in payment.name:
                canc_pname = self._get_next_canceled_name("account.payment", payment.name, payment.company_id.id)
                payment.with_context(skip_retention_name_sync=True).write({"name": canc_pname})
            if payment.move_id and payment.move_id.name and payment.move_id.name != "/" and not payment.move_id.name.endswith("-canc") and "-canc-" not in payment.move_id.name:
                canc_mname = self._get_next_canceled_name("account.move", payment.move_id.name, payment.company_id.id)
                payment.move_id.with_context(skip_retention_name_sync=True).write({"name": canc_mname})
                payment.move_id.line_ids.with_context(skip_retention_name_sync=True).write({"name": canc_mname})
        return super().action_cancel()

    # def _synchronize_to_moves(self, changed_fields):
    #     """
    #     Override the original method to change the name of the move based on the retention type
    #     using the retention's number and the invoice's name of the retention.
    #     """
    #     res = super()._synchronize_to_moves(changed_fields)
    #     account_move_name_by_retention_type = {
    #         "iva": "RIV",
    #         "islr": "RIS",
    #         "municipal": "RM",
    #     }
    #     for payment in self.filtered("is_retention").with_context(
    #         skip_account_move_synchronization=True
    #     ):
    #         if not all((payment.retention_line_ids, payment.retention_id.number)):
    #             continue
    #         move = payment.move_id
    #         move_name = (
    #             account_move_name_by_retention_type[payment.retention_id.type_retention]
    #             + f"-{payment.retention_id.number}"
    #             + f"-{payment.retention_line_ids[0].move_id.name}"
    #         )
    #         if payment.retention_id.type_retention == "islr":
    #             move_name += f"-{payment.retention_line_ids[0].payment_concept_id.name[:5]}"

    #         vals_to_change = {"name": move_name}
    #         move.write(vals_to_change)
    #         move.line_ids.write(vals_to_change)
    #     return res

    def unlink(self):
        for payment in self:
            if payment.retention_line_ids:
                payment.retention_line_ids.unlink()
        return super().unlink()

    def action_post(self):
        for payment in self:
            if payment.is_retention and payment.retention_id and payment.retention_id.state == 'draft':
                if not self._context.get('skip_retention_state_check'):
                    raise ValidationError(_("No puede contabilizar un pago de retención si la retención asociada aún se encuentra en estado Borrador."))
        return super().action_post()

    def compute_retention_amount_from_retention_lines(self):
        """
        Compute the amount from the retention lines.
        """
        for payment in self:
            payment.amount = sum(payment.retention_line_ids.mapped("retention_amount"))

    @api.depends("retention_line_ids")
    def _compute_retention_foreign_amount(self):
        for payment in self:
            payment.retention_foreign_amount = abs(
                sum(
                    payment.retention_line_ids.mapped(
                        lambda l: float_round(
                            l.foreign_retention_amount,
                            precision_digits=l.retention_id.foreign_currency_id.decimal_places,
                        )
                    )
                )
            )
