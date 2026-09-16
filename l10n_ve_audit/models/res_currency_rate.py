# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ResCurrencyRate(models.Model):
    _inherit = 'res.currency.rate'

    def _check_rate_permission(self):
        """
        Valida que el usuario tenga el rol de Administrador de Contabilidad.
        Bypass para superusuario (su).
        """
        if self.env.su:
            return
        if not self.env.user.has_group('account.group_account_manager'):
            raise UserError(_("No tiene privilegios suficientes para crear tasas de cambio. Esta acción está reservada para Administradores de Contabilidad."))

    @api.model_create_multi
    def create(self, vals_list):
        # Aplicar restricciones de seguridad del ORM
        for vals in vals_list:
            self._check_rate_permission()
            
        rates = super(ResCurrencyRate, self).create(vals_list)
        
        # Registrar evento en auditoría
        for rate in rates:
            orig = "Ingreso Manual"
            if self.env.context.get('from_cron'):
                orig = "Cron (Sincronización Automática)"
            elif self.env.context.get('from_button'):
                orig = "Botón de Actualización Manual"

            bcv_rate = round(1.0 / rate.rate, 4) if rate.rate > 0 else 'N/A'
            details = (f"Creación de Tasa de Cambio. "
                       f"Moneda: {rate.currency_id.name}. "
                       f"Fecha Tasa: {rate.name}. "
                       f"Valor Tasa (Directo): {rate.rate}. "
                       f"Tasa BCV (Bs. por USD/EUR): {bcv_rate}. "
                       f"Origen: {orig}.")
            self.env['l10n_ve.audit.log'].log_event('rate_create', rate, details)
            
        return rates

    def write(self, vals):
        # Bloquear modificación manual por completo bajo regulación SENIAT
        if not self.env.su:
            raise UserError(_("Está prohibido modificar las tasas de cambio ya establecidas en el histórico por regulación del SENIAT."))
        
        # Capturar datos anteriores para detallar el log
        old_data = {rate.id: (rate.name, rate.rate, rate.currency_id.name) for rate in self}
        
        res = super(ResCurrencyRate, self).write(vals)
        
        # Registrar evento en auditoría (para acciones automáticas del sistema que usen write)
        for rate in self:
            old_name, old_rate, curr_name = old_data.get(rate.id, (None, None, None))
            orig = "Cron/Procedimiento del Sistema"
            new_bcv = round(1.0 / rate.rate, 4) if rate.rate > 0 else 'N/A'
            old_bcv = round(1.0 / old_rate, 4) if old_rate and old_rate > 0 else 'N/A'
            
            details = (f"Modificación de Tasa de Cambio (Sistema). "
                       f"Moneda: {rate.currency_id.name}. "
                       f"Fecha Tasa: {rate.name} (Antes: {old_name}). "
                       f"Valor Tasa Nuevo: {rate.rate} (Antes: {old_rate}). "
                       f"Tasa BCV Nueva: {new_bcv} (Antes: {old_bcv}). "
                       f"Origen: {orig}.")
            self.env['l10n_ve.audit.log'].log_event('rate_write', rate, details)
            
        return res

    def unlink(self):
        # Bloquear eliminación manual por completo bajo regulación SENIAT
        if not self.env.su:
            raise UserError(_("Está prohibido eliminar las tasas de cambio históricas por regulación del SENIAT."))
        
        # Registrar evento antes de la eliminación física del registro
        for rate in self:
            bcv_rate = round(1.0 / rate.rate, 4) if rate.rate > 0 else 'N/A'
            details = (f"ELIMINACIÓN DE TASA DE CAMBIO. "
                       f"ID Registro: {rate.id}. "
                       f"Moneda: {rate.currency_id.name}. "
                       f"Fecha Tasa: {rate.name}. "
                       f"Valor Tasa: {rate.rate}. "
                       f"Tasa BCV: {bcv_rate}.")
            self.env['l10n_ve.audit.log'].log_event('rate_unlink', rate, details)
            
        return super(ResCurrencyRate, self).unlink()

class ResCurrency(models.Model):
    _inherit = 'res.currency'

    def _compute_can_edit_rates(self):
        for rec in self:
            rec.can_edit_rates = False
