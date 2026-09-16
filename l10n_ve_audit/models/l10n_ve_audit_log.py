# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class L10nVeAuditLog(models.Model):
    _name = 'l10n_ve.audit.log'
    _description = 'Registro de Auditoría Fiscal'
    _order = 'datetime desc, id desc'

    datetime = fields.Datetime(string="Fecha y Hora", default=fields.Datetime.now, readonly=True, required=True)
    user_id = fields.Many2one('res.users', string="Usuario", default=lambda self: self.env.user, readonly=True, required=True)
    action = fields.Selection([
        ('create', 'Creación'),
        ('post', 'Asentado / Publicación'),
        ('draft', 'Volver a Borrador'),
        ('cancel', 'Cancelación'),
        ('reversal', 'Reversión (Nota de Crédito/Débito)'),
        ('unlink', 'Eliminación Directa'),
        ('rate_create', 'Creación de Tasa BCV'),
        ('rate_write', 'Modificación de Tasa BCV'),
        ('rate_unlink', 'Eliminación de Tasa BCV'),
        ('control_void', 'Anulación de Control de Forma Libre'),
    ], string="Acción", readonly=True, required=True)
    res_model = fields.Char(string="Modelo Técnico", readonly=True, required=True)
    res_id = fields.Integer(string="ID del Registro", readonly=True, required=True)
    record_name = fields.Char(string="Nombre/Nro. Control", readonly=True)
    details = fields.Text(string="Detalles del Evento", readonly=True)
    company_id = fields.Many2one('res.company', string="Compañía", default=lambda self: self.env.company, readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.su and self.env.user.has_group('l10n_ve_audit.group_fiscal_auditor'):
            raise UserError(_("Los auditores fiscales del SENIAT tienen acceso estrictamente de solo lectura."))
        return super(L10nVeAuditLog, self).create(vals_list)

    # Inmutabilidad: Impedir cualquier tipo de edición sobre los registros existentes
    def write(self, vals):
        raise UserError(_("Los registros de auditoría fiscal son inmutables y no pueden ser modificados bajo ninguna circunstancia."))

    # Inmutabilidad: Impedir la eliminación de registros de auditoría
    def unlink(self):
        raise UserError(_("Los registros de auditoría fiscal son inmutables y no pueden ser eliminados del sistema."))

    @api.model
    def log_event(self, action, record, details=None):
        """Método helper para registrar eventos contables rápidamente."""
        # Se ejecuta con sudo() para que los triggers de auditoría funcionen incluso si el usuario tiene restricciones
        # Pero el user_id asignado sigue siendo el usuario real de la sesión (self.env.user)
        name = getattr(record, 'name', '')
        if hasattr(record, 'correlative') and record.correlative:
            name += f" (Control: {record.correlative})"
        elif hasattr(record, 'l10n_ve_guide_number') and record.l10n_ve_guide_number:
            name += f" (Guía: {record.l10n_ve_guide_number})"

        self.sudo().create({
            'datetime': fields.Datetime.now(),
            'user_id': self.env.user.id,
            'action': action,
            'res_model': record._name,
            'res_id': record.id,
            'record_name': name or f"ID: {record.id}",
            'details': details or f"Acción '{action}' ejecutada sobre {record._name} (ID: {record.id}).",
            'company_id': record.company_id.id if hasattr(record, 'company_id') and record.company_id else self.env.company.id
        })
