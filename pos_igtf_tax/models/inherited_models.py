
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools import float_round
import logging

_logger = logging.getLogger(__name__)

class PosSession(models.Model):
    _inherit = 'pos.session'

    @api.model
    def _load_pos_data(self, data):
        result = super()._load_pos_data(data)
        
        # Inyectar dinámicamente el producto IGTF en la caché del POS (product.product)
        pos_config = self.env['pos.config'].browse(self.env.context.get('pos_config_id'))
        if pos_config and pos_config.x_igtf_product_id:
            igtf_product = pos_config.x_igtf_product_id
            
            if 'product.product' not in result:
                result['product.product'] = {'data': []}
                
            product_list = result['product.product'].get('data', [])
            product_ids = {p['id'] for p in product_list}
            
            if igtf_product.id not in product_ids:
                _logger.info("[IGTF] Inyectando producto IGTF '%s' (ID %s) en los datos del POS", igtf_product.name, igtf_product.id)
                fields_to_read = self.env['product.product']._load_pos_data_fields(pos_config.id)
                fields_to_read = list(set(fields_to_read + ['id', 'display_name', 'lst_price']))
                
                igtf_product_data = igtf_product.sudo().search_read(
                    [('id', '=', igtf_product.id)],
                    fields_to_read
                )
                if igtf_product_data:
                    product_list.append(igtf_product_data[0])
                    result['product.product']['data'] = product_list
                    
        return result

    # Pachacutec: v18 - Odoo 18 usa _load_pos_data_fields en el modelo.
    # Eliminamos _loader_params obsoletos de Odoo 17/16.

    def _get_igtf_fallback_account(self, type='income'):
        """
        Pachacutec: v187 - PUENTE DE EMERGENCIA ODOO 18
        Eliminamos company_id explícito del dominio para evitar ValueError.
        Odoo aplicará el filtro de compañía automáticamente por contexto.
        """
        account_type = 'income' if type == 'income' else 'asset_current'
        domain = [('account_type', '=', account_type)]
        fallback = self.env['account.account'].search(domain, limit=1)
        if not fallback:
            # Búsqueda desesperada: cualquier cuenta disponible
            fallback = self.env['account.account'].search([], limit=1)
        return fallback

    def _prepare_payment_line_vals(self, payment):
        """
        Pachacutec: v185 - ASEGURAR CUENTA EN PAGO (ZELLE Fix)
        Si el método de pago no tiene cuenta, Odoo 18 intenta insertar NULL.
        Aquí forzamos una cuenta válida para evitar el error de base de datos.
        """
        res = super()._prepare_payment_line_vals(payment)
        if not res.get('account_id'):
            fallback = self._get_igtf_fallback_account(type='asset_current')
            if fallback:
                _logger.warning("[IGTF] v185/v186 - Usando cuenta de EMERGENCIA (%s) para pago %s", fallback.code, payment.payment_method_id.name)
                res['account_id'] = fallback.id
        return res

    def _get_receivable_account(self, payment_method):
        """
        Pachacutec: v186 - ASEGURAR CUENTA POR COBRAR
        Captura el caso donde el método de pago (ZELLE) no tiene cuenta y Odoo 18 retorna False.
        """
        res = super()._get_receivable_account(payment_method)
        if not res:
            fallback = self._get_igtf_fallback_account(type='asset_current')
            if fallback:
                _logger.warning("[IGTF] v186 - Usando cuenta de EMERGENCIA (%s) para cobro de %s", fallback.code, payment_method.name)
                return fallback
        return res

    def _accumulate_amounts(self, data):
        """
        Override para agregar el monto IGTF de las órdenes POS al diccionario 'sales'.
        El IGTF se cobra como pago recibible pero su línea de crédito de ventas no se
        genera automáticamente por _prepare_tax_base_line_values. Sin esta corrección,
        el move de sesión queda desbalanceado por el monto IGTF total.
        NOTA: La corrección real se aplica en _fix_igtf_imbalance_in_session_move.
        """
        data = super()._accumulate_amounts(data)

        # Solo aplicar si el POS está configurado para IGTF y la compañía es contribuyente especial
        igtf_product = self.config_id.x_igtf_product_id
        if not igtf_product or not self.config_id.aplicar_igtf or self.config_id.company_id.taxpayer_type != 'special':
            return data

        # Cuenta de ingresos del producto IGTF: buscar via jerarquía template→categoría
        product_accounts = igtf_product._get_product_accounts()
        igtf_account = (
            igtf_product.property_account_income_id
            or product_accounts.get('income')
        )
        if not igtf_account:
            _logger.warning("[IGTF] v185 - Producto IGTF '%s' no tiene cuenta. Buscando EMERGENCIA...", igtf_product.name)
            igtf_account = self._get_igtf_fallback_account(type='income')
            
        if not igtf_account:
            _logger.error("[IGTF] v185 - NO SE HALLÓ NINGUNA CUENTA DE INGRESOS PARA EL CIERRE.")
            return data

        sales = data.get('sales')
        currency_rounding = self.currency_id.rounding
        closed_orders = self._get_closed_orders()

        for order in closed_orders:
            if order.is_invoiced:
                continue
            igtf_amount = order.x_igtf_amount
            if not igtf_amount:
                continue
            igtf_amount_rounded = float_round(igtf_amount, precision_rounding=currency_rounding)
            if igtf_amount_rounded == 0.0:
                continue

            igtf_key = (
                igtf_account.id,
                1,
                tuple(),
                tuple(),
                igtf_product.id if self.config_id.is_closing_entry_by_product else False,
            )
            sales[igtf_key] = self._update_amounts(
                sales[igtf_key],
                {
                    'amount': igtf_amount_rounded,
                    'amount_converted': igtf_amount_rounded,
                },
                order.date_order,
            )

        return data


class PosOrder(models.Model):
    _inherit = "pos.order"

    x_igtf_amount = fields.Monetary("Monto IGTF", compute="_compute_x_igtf_amount", store=True)

    @api.depends("lines.x_is_igtf_line", "lines.price_subtotal_incl")
    def _compute_x_igtf_amount(self):
        for rec in self:
            rec.x_igtf_amount = sum(rec.lines.filtered("x_is_igtf_line").mapped("price_subtotal_incl"))

    def _get_fields_for_order_line(self):
        fields = super()._get_fields_for_order_line()

        fields.append('x_is_igtf_line')
        
        return fields

    @api.model
    def _complete_values_from_session(self, session, values):
        res = super()._complete_values_from_session(session, values)
        if not res.get('company_id') and session:
            res['company_id'] = session.config_id.company_id.id or session.company_id.id
        return res

    @api.model
    def _process_order(self, order, existing_order):
        if order:
            session_id = order.get('session_id')
            pos_session = self.env['pos.session'].browse(session_id) if session_id else self.env['pos.session']
            if not session_id or not pos_session.exists():
                valid_session = self._get_valid_session(order)
                if valid_session:
                    _logger.warning("[IGTF] Reparando session_id nulo/inválido en el pedido. Asignando sesión: %s", valid_session.id)
                    order['session_id'] = valid_session.id
                    pos_session = valid_session
            
            if pos_session and not order.get('company_id'):
                order['company_id'] = pos_session.company_id.id

        return super()._process_order(order, existing_order)
        
class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    x_is_igtf_line = fields.Boolean("Linea IGTF")

    @api.model
    def _load_pos_data_fields(self, config_id):
        return super()._load_pos_data_fields(config_id) + ['x_is_igtf_line']

    def _order_line_fields(self, line, session_id):
        result = super()._order_line_fields(line, session_id)
        vals = result[2]

        vals["x_is_igtf_line"] = vals.get("x_is_igtf_line", line[2].get("x_is_igtf_line", False))

        return result

    def _export_for_ui(self, orderline):
        res = super()._export_for_ui(orderline)

        res["x_is_igtf_line"] = orderline.x_is_igtf_line

        return res

class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    x_igtf_percentage = fields.Float("Porcentaje de IGTF", compute="_compute_x_igtf_percentage", store=True, readonly=False)
    x_is_foreign_exchange = fields.Boolean("Pago en divisas")

    @api.depends('x_is_foreign_exchange', 'company_id.igtf_percentage')
    def _compute_x_igtf_percentage(self):
        for rec in self:
            if rec.x_is_foreign_exchange and not rec.x_igtf_percentage:
                rec.x_igtf_percentage = rec.company_id.igtf_percentage or 3.0
            elif not rec.x_is_foreign_exchange:
                rec.x_igtf_percentage = 0.0
            else:
                rec.x_igtf_percentage = rec.x_igtf_percentage

    @api.model
    def _load_pos_data_fields(self, config_id):
        return super()._load_pos_data_fields(config_id) + ['x_igtf_percentage', 'x_is_foreign_exchange']

    @api.constrains("x_igtf_percentage")
    def _check_x_igtf_percentage(self):
        for rec in self:
            if rec.x_igtf_percentage < 0 and rec.x_is_foreign_exchange:
                raise ValidationError("El porcentage IGTF debe ser mayor a cero")

class PosConfig(models.Model):
    _inherit = "pos.config"

    x_igtf_product_id = fields.Many2one("product.product", "Producto IGTF")

    aplicar_igtf = fields.Boolean("Aplicar IGTF", default=False)

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pos_x_igtf_product_id = fields.Many2one(
        string="Producto IGTF", 
        related="pos_config_id.x_igtf_product_id",
        readonly=False,
    )

    aplicar_igtf = fields.Boolean(related="pos_config_id.aplicar_igtf", readonly=False)

    @api.constrains("pos_x_igtf_product_id")
    def _check_pos_x_igtf_product_id(self):
        for rec in self.filtered("pos_x_igtf_product_id"):
            if not rec.pos_x_igtf_product_id.property_account_income_id:
                raise ValidationError("El producto IGTF debe tener una cuenta de ingresos configurada")
            if sum(rec.pos_x_igtf_product_id.taxes_id.mapped("amount")) != 0:
                raise ValidationError("El producto IGTF debe ser exento")

class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model
    def _load_pos_data_fields(self, config_id):
        return super()._load_pos_data_fields(config_id) + ['taxpayer_type']
