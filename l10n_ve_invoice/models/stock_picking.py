# -*- coding: utf-8 -*-
from odoo import models, fields, api

class StockPicking(models.Model):
    _inherit = 'stock.picking'

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
                'default_picking_id': self.id,
                'default_l10n_ve_guide_number': self.l10n_ve_guide_number or self.env['ir.sequence'].next_by_code('stock.picking.delivery.guide') or '',
                'default_l10n_ve_carrier_name': self.l10n_ve_carrier_name,
                'default_l10n_ve_carrier_vat': self.l10n_ve_carrier_vat,
                'default_l10n_ve_vehicle_plate': self.l10n_ve_vehicle_plate,
                'default_l10n_ve_vehicle_brand': self.l10n_ve_vehicle_brand,
                'default_l10n_ve_starting_point': starting_point,
                'default_l10n_ve_ending_point': ending_point,
            }
        }
