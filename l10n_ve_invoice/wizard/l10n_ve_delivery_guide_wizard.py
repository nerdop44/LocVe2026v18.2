# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class L10nVeDeliveryGuideWizard(models.TransientModel):
    _name = 'l10n_ve.delivery.guide.wizard'
    _description = 'Wizard para ingresar datos de la Guía de Despacho'

    move_id = fields.Many2one('account.move', string="Factura", required=True)
    l10n_ve_guide_number = fields.Char(string="Número de Guía de Despacho", required=True)
    l10n_ve_carrier_name = fields.Char(string="Nombre del Transportista", required=True)
    l10n_ve_carrier_vat = fields.Char(string="RIF/Cédula del Transportista", required=True)
    l10n_ve_vehicle_plate = fields.Char(string="Placa del Vehículo", required=True)
    l10n_ve_vehicle_brand = fields.Char(string="Marca/Modelo del Vehículo", required=True)
    l10n_ve_starting_point = fields.Text(string="Dirección de Salida", required=True)
    l10n_ve_ending_point = fields.Text(string="Dirección de Llegada", required=True)

    @api.model
    def default_get(self, fields_list):
        res = super(L10nVeDeliveryGuideWizard, self).default_get(fields_list)
        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id')
        
        if active_model == 'account.move' and active_id:
            move = self.env['account.move'].browse(active_id)
            res.update({
                'move_id': move.id,
                'l10n_ve_guide_number': move.l10n_ve_guide_number or self.env['ir.sequence'].next_by_code('stock.picking.delivery.guide') or '',
                'l10n_ve_carrier_name': move.l10n_ve_carrier_name,
                'l10n_ve_carrier_vat': move.l10n_ve_carrier_vat,
                'l10n_ve_vehicle_plate': move.l10n_ve_vehicle_plate,
                'l10n_ve_vehicle_brand': move.l10n_ve_vehicle_brand,
            })
            
            starting_point = move.l10n_ve_starting_point
            if not starting_point and move.company_id.partner_id:
                partner = move.company_id.partner_id
                parts = [partner.street or "", partner.street2 or "", partner.city or "", partner.state_id.name if partner.state_id else ""]
                starting_point = ", ".join([p for p in parts if p])
            res['l10n_ve_starting_point'] = starting_point
            
            ending_point = move.l10n_ve_ending_point
            if not ending_point and move.partner_id:
                partner = move.partner_id
                parts = [partner.street or "", partner.street2 or "", partner.city or "", partner.state_id.name if partner.state_id else ""]
                ending_point = ", ".join([p for p in parts if p])
            res['l10n_ve_ending_point'] = ending_point
            
        return res

    def action_confirm(self):
        self.ensure_one()
        # Escribir los valores de vuelta en la factura (account.move)
        self.move_id.write({
            'l10n_ve_guide_number': self.l10n_ve_guide_number,
            'l10n_ve_carrier_name': self.l10n_ve_carrier_name,
            'l10n_ve_carrier_vat': self.l10n_ve_carrier_vat,
            'l10n_ve_vehicle_plate': self.l10n_ve_vehicle_plate,
            'l10n_ve_vehicle_brand': self.l10n_ve_vehicle_brand,
            'l10n_ve_starting_point': self.l10n_ve_starting_point,
            'l10n_ve_ending_point': self.l10n_ve_ending_point,
        })
        # Ejecutar la acción de impresión del reporte de Guía de Despacho
        return self.env.ref('l10n_ve_invoice.action_report_delivery_guide').report_action(self.move_id)
