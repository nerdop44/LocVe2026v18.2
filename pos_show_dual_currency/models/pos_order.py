from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class PosOrder(models.Model):
    _inherit = "pos.order"

    ref_me_currency_id = fields.Many2one('res.currency', related='session_id.ref_me_currency_id',
                                         string="Reference Currency",
                                         store=False)
    session_rate = fields.Float(string="Session Rate", store=True,
                                related='session_id.tax_today',
                                digits=(16, 4))

    amount_tax_ref = fields.Float(string='Ref Taxes', compute='_compute_amount_all_ref', store=True)
    amount_total_ref = fields.Float(string='Ref Total', compute='_compute_amount_all_ref', store=True)
    amount_paid_ref = fields.Float(string='Ref Paid', compute='_compute_amount_all_ref', store=True)
    amount_return_ref = fields.Float(string='Ref Returned', compute='_compute_amount_all_ref', store=True)
    margin_ref = fields.Monetary(string="Ref Margin", compute='_compute_margin_ref', store=True)
    sum_amount_total_ref = fields.Float(string='Total Ref. Sum', compute='_compute_amount_all_ref', store=True)

    @api.depends('session_rate', 'margin')
    def _compute_margin_ref(self):
        for order in self:
            if order.session_rate != 0:
                order.margin_ref = order.margin * order.session_rate

            else:
                order.margin = 0

    @api.depends('amount_tax', 'amount_total', 'session_rate', 'amount_paid')
    def _compute_amount_all_ref(self):
        for order in self:
            if order.session_rate != 0:
                order.amount_paid_ref = order.amount_paid * order.session_rate
                order.amount_return_ref = order.amount_return * order.session_rate
                order.amount_tax_ref = order.amount_tax * order.session_rate
                order.amount_total_ref = order.amount_total * order.session_rate
                order.sum_amount_total_ref = order.amount_total * order.session_rate
            else:
                order.amount_paid_ref = 0
                order.amount_return_ref = 0
                order.amount_tax_ref = 0
                order.amount_total_ref = 0
                order.sum_amount_total_ref = 0
    @api.model
    def _prepare_order_vals(self, values):
        # Pachacutec: v18.0.1.0.99 - GHOST COMPANY UNBINDING
        # Identificamos si el picking_type_id es el ID 12 (Animal Center c.a.) o si es inaccesible.
        # En tal caso, lo desvinculamos y asignamos uno válido de la empresa actual.
        res = super(PosOrder, self)._prepare_order_vals(values)
        
        picking_type_id = res.get('picking_type_id')
        session = self.env['pos.session'].sudo().browse(res.get('session_id'))
        company_id = session.company_id.id if session else self.env.company.id

        # Verificamos si el picking_type actual es válido para el usuario y la empresa
        is_hostile = False
        if picking_type_id == 12:
            is_hostile = True
        else:
            try:
                # Intento de lectura para verificar acceso
                self.env['stock.picking.type'].browse(picking_type_id).name
            except Exception:
                is_hostile = True
        
        if is_hostile:
            _logger.warning("[POS Unbind] Detectada referencia hostil a empresa fantasma (ID: %s). Reasignando...", picking_type_id)
            # Buscamos un sustituto válido en la empresa actual
            substitute = self.env['stock.picking.type'].sudo().search([
                ('company_id', '=', company_id),
                ('code', '=', 'outgoing'),
                ('active', '=', True)
            ], limit=1)
            
            if substitute:
                res['picking_type_id'] = substitute.id
                _logger.info("[POS Unbind] Reasignado exitosamente a picking_type: %s (%s)", substitute.id, substitute.display_name)
            else:
                _logger.error("[POS Unbind] No se encontró un picking_type de salida válido para la empresa %s", company_id)
        
        return res

    @api.model
    def sync_from_ui(self, orders):
        # Pachacutec: v18.0.1.1.0 - MULTI-COMPANY & ACL SHIELD
        # Elevamos privilegios mediante el modelo para asegurar que la sincronización
        # de pedidos pueda escribir en metadatos de moneda (ACL write res.currency) 
        # y leer tipos de picking de otras sucursales en entornos de grupo.
        try:
            return super(PosOrder, self.env['pos.order'].sudo()).sync_from_ui(orders)
        except Exception as e:
            _logger.error("[POS Sync] Error en sync_from_ui (sudo): %s", str(e))
            return super().sync_from_ui(orders)
