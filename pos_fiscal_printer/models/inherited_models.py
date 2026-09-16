import logging
from datetime import datetime

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class PosOrder(models.Model):
    _inherit = "pos.order"

    z_report = fields.Char("Reporte Z", related="session_id.x_pos_z_report_number", store=True)
    num_factura = fields.Char("Num. Factura Fiscal", store=True)
    impresa = fields.Boolean("Impresa Fiscal", default=False)

    def set_num_factura(self, name, number):
        o = self.env['pos.order'].search([('pos_reference','=',name)])
        if o:
            o.write({"num_factura": number, "impresa": True})

    @api.model
    def _order_fields(self, ui_order):
        order_fields = super(PosOrder, self)._order_fields(ui_order)
        order_fields['num_factura'] = ui_order.get('num_factura')
        order_fields['impresa'] = ui_order.get('impresa')
        return order_fields

    def _export_for_ui(self, order):
        result = super(PosOrder, self)._export_for_ui(order)
        result.update({
            'num_factura': order.num_factura,
            'impresa': order.impresa,
        })
        return result

class PosSession(models.Model):
    _inherit = "pos.session"

    x_pos_z_report_number = fields.Char("Número Reporte Z")
    pos_report_z_id = fields.Many2one("pos.report.z", "Reporte Z")

    # Odoo 18 Loader Migration: x_printer_code is now loaded via PosPaymentMethod._load_pos_data_fields

    def set_z_report(self, number):
        z_report = self.env['pos.report.z'].sudo().search([('number','=',number)])
        if z_report:
            z_report.write({"pos_session_ids": [(4, self.id)]})
            z_report._onchange_pos_session_ids()
            self.sudo().write({"x_pos_z_report_number": number, 'pos_report_z_id': z_report.id})
        else:
            z_report = self.env['pos.report.z'].sudo().create({
                "number": number,
                'date': datetime.today(),
                'x_fiscal_printer_id': self.config_id.x_fiscal_printer_id.id,
                "pos_session_ids": [(4, self.id)],
            })
            z_report.sudo()._onchange_pos_session_ids()
            self.sudo().write({"x_pos_z_report_number": number, 'pos_report_z_id': z_report.id})
            
            activity = {
                'res_id': z_report.id,
                'res_model_id': self.env['ir.model'].search([('model', '=', 'pos.report.z')]).id,
                'user_id': self.env.user.id,
                'summary': 'Verificar reporte Z',
                'note': 'Verifica si existe otra sesión para este reporte Z y validar el reporte Z',
                'activity_type_id': 4,
                'date_deadline': datetime.today(),
            }
            self.env['mail.activity'].sudo().create(activity)

class AccountTax(models.Model):
    _inherit = "account.tax"

    x_tipo_alicuota = fields.Selection([
        ("exento", "Exento"),
        ("general", "General"),
        ("reducido", "Reducido"),
        ("adicional", "Adicional"),
    ], "Tipo de alícuota", default="general")

    @api.model
    def _load_pos_data_fields(self, config_id):
        return super()._load_pos_data_fields(config_id) + ['x_tipo_alicuota', 'amount']

class PosConfig(models.Model):
    _inherit = "pos.config"

    x_fiscal_command_baudrate = fields.Integer("Baudrate", default=9600)
    x_fiscal_commands_time = fields.Integer("Tiempo de espera", related="x_fiscal_printer_id.x_fiscal_commands_time")
    x_fiscal_printer_id = fields.Many2one("x.pos.fiscal.printer", "Impresora fiscal")
    x_fiscal_printer_code = fields.Char(related="x_fiscal_printer_id.serial")
    flag_21 = fields.Selection(string="Flag 21", related="x_fiscal_printer_id.flag_21")
    connection_type = fields.Selection(related="x_fiscal_printer_id.connection_type")
    x_fiscal_command_parity = fields.Selection(related="x_fiscal_printer_id.x_fiscal_command_parity")
    api_url = fields.Char(related="x_fiscal_printer_id.api_url")

    @api.model
    def _load_pos_data(self, data):
        # Pachacutec: v218 - Inyectar flag_21 para discriminación de protocolo en JS
        res = super()._load_pos_data(data)
        if isinstance(res, dict) and 'data' in res and len(res['data']) > 0:
            config_id = self.env.context.get('pos_config_id')
            if config_id:
                config = self.browse(config_id)
                res['data'][0]['flag_21'] = config.flag_21
        return res


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    x_printer_code = fields.Char("Código en la impresora")

    @api.model
    def _load_pos_data_fields(self, config_id):
        # Pachacutec: v18 - Método estándar para evitar errores de getIndexMaps
        res = super()._load_pos_data_fields(config_id)
        if 'x_printer_code' not in res:
            res.append('x_printer_code')
        return res

    @api.constrains("x_printer_code")
    def _check_x_printer_code(self):
        for rec in self:
            if rec.x_printer_code and len(rec.x_printer_code) != 2:
                raise ValidationError("El código en la impresora sólo puede tener dos caracteres")

class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def _load_pos_data_fields(self, config_id):
        # Pachacutec: v197 - Odoo 18 Loader Migration
        return super()._load_pos_data_fields(config_id) + [
            'vat', 'prefix_vat', 'full_vat',
            'street', 'city', 'phone', 'mobile', 'email'
        ]

class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model
    def _load_pos_data_fields(self, config_id):
        return super()._load_pos_data_fields(config_id) + ['vat', 'street', 'city', 'phone']

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pos_x_fiscal_command_baudrate = fields.Integer(related="pos_config_id.x_fiscal_command_baudrate", readonly=False)
    pos_x_fiscal_commands_time = fields.Integer(related="pos_config_id.x_fiscal_commands_time", readonly=False)
    pos_x_fiscal_printer_id = fields.Many2one(related="pos_config_id.x_fiscal_printer_id", readonly=False)
    flag_21 = fields.Selection(related="pos_config_id.flag_21", readonly=True)
    connection_type = fields.Selection(related="pos_config_id.connection_type", readonly=True)
    api_url = fields.Char(related="pos_config_id.api_url")
    pos_x_fiscal_command_parity = fields.Selection(related="pos_config_id.x_fiscal_command_parity", readonly=False)

    @api.constrains("pos_x_fiscal_commands_time")
    def _check_x_fiscal_commands_time(self):
        for rec in self:
            if rec.pos_x_fiscal_commands_time < 0:
                raise ValidationError(_("El tiempo entre comandos no puede ser cero"))
