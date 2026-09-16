import secrets
from datetime import datetime, timedelta

from odoo import models, fields, api
from odoo.exceptions import UserError


class SoporteHelpConfig(models.Model):
    _name = 'soportehelp.config'
    _description = 'Configuración del Módulo Soporte y Ayuda'
    _rec_name = 'name'

    name = fields.Char(string='Nombre', default='Configuración Principal', readonly=True)

    state = fields.Selection(
        [
            ('standby', 'Standby (Pruebas)'),
            ('active', 'Activo (Producción)'),
        ],
        string='Modo',
        default='standby',
        help='Standby = solo telemetría pasiva. Activo = control habilitado.',
    )
    enforcement_enabled = fields.Boolean(
        string='Enforcement Habilitado',
        default=False,
        help='Control de cumplimiento activo. Solo se activa por orden remota desde el backend o manualmente.',
    )

    service_url = fields.Char(string='URL del Backend', default='https://of.venrides.com')
    client_uuid = fields.Char(string='UUID de Instancia', readonly=True)
    api_key = fields.Char(string='API Key', readonly=True)
    registration_state = fields.Selection(
        [
            ('not_registered', 'No Registrado'),
            ('pending', 'Pendiente de Aprobación'),
            ('approved', 'Aprobado'),
            ('rejected', 'Rechazado'),
        ],
        string='Estado de Registro',
        default='not_registered',
        readonly=True,
    )
    registration_message = fields.Char(string='Mensaje de Registro', readonly=True)

    hw_fingerprint = fields.Char(string='HW Fingerprint', compute='_compute_hw_fingerprint')

    provider_name = fields.Char(
        string='Nombre del Proveedor',
        default='Servicio de Soporte y Ayuda',
        help='Nombre comercial de la empresa proveedora del servicio de soporte postventa.'
    )
    provider_website = fields.Char(
        string='Sitio Web del Proveedor',
        default='',
        help='URL del portal oficial de atención al cliente.'
    )
    support_email = fields.Char(
        string='Email de Soporte',
        default='',
        help='Correo oficial para la recepción e informes de tickets.'
    )
    author_fingerprint = fields.Char(
        string='Fingerprint de Autor',
        default='',
        help='Fragmento de author presente en los manifiestos de los módulos a supervisar.',
    )
    website_fingerprint = fields.Char(
        string='Fingerprint de Website',
        default='',
        help='Fragmento de website presente en los manifiestos de los módulos. '
             'Si se deja vacío, la detección prioriza el fingerprint de autor y el patrón de módulos.',
    )

    module_pattern = fields.Char(
        string='Patrón de Módulos (Regex)',
        default='^(l10n_ve_|pos_|account_dual_currency|date_range|locve_)',
        help='Expresión regular sobre el nombre técnico de módulos candidatos.',
    )

    token_cipher = fields.Text(string='Token Cifrado', readonly=True)
    token_expiry = fields.Datetime(string='Vencimiento del Token', readonly=True)
    maintenance_until = fields.Datetime(
        string='Ventana de Mantenimiento Hasta',
        readonly=True,
        help='Ventana temporal en la que se concede paso total.',
    )
    recovery_token_active = fields.Boolean(string='Recovery Token Activo', readonly=True)
    recovery_token_expiry = fields.Datetime(string='Vencimiento Recovery Token', readonly=True)

    last_inventory = fields.Json(string='Último Inventario', readonly=True)
    last_inventory_at = fields.Datetime(string='Último Inventario el', readonly=True)
    last_heartbeat = fields.Datetime(string='Último Heartbeat', readonly=True)
    last_heartbeat_status = fields.Selection(
        [('ok', 'OK'), ('error', 'Error'), ('unknown', 'Desconocido')],
        string='Estado Último Heartbeat',
        readonly=True,
        default='unknown',
    )
    heartbeat_frequency_hours = fields.Integer(string='Frecuencia de Heartbeat (horas)', default=24)
    inventory_frequency_hours = fields.Integer(string='Frecuencia de Inventario (horas)', default=6)

    support_alert_active = fields.Boolean(
        string='Alerta de Soporte Activa', default=False, readonly=True,
        help='Indica si el backend ha activado una alerta emergente de "Comuníquese con Soporte".'
    )
    support_alert_type = fields.Char(string='Tipo de Alerta', default='none', readonly=True)
    support_alert_message = fields.Text(string='Mensaje de Alerta de Soporte', readonly=True)

    company_alert_ids = fields.One2many(
        'soportehelp.company.alert', 'config_id', string='Alertas por Compañía (Multi-Empresa)'
    )



    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        default=lambda self: self.env.company.id,
    )

    history_ids = fields.One2many('soportehelp.history', 'config_id', string='Historial')
    ticket_ids = fields.One2many('soportehelp.ticket', 'config_id', string='Tickets')

    @api.depends('name')
    def _compute_hw_fingerprint(self):
        import uuid
        for record in self:
            try:
                node = uuid.getnode()
            except Exception:
                node = 0
            record.hw_fingerprint = f"{node:x}-{record.env.cr.dbname}" if record.env.cr.dbname else f"{node:x}"

    @api.model
    def _get_or_create(self):
        config = self.search([], limit=1)
        if not config:
            config = self.create({'name': 'Configuración Principal'})
        return config

    @api.model
    def _default_config(self):
        return self._get_or_create()

    @api.model
    def _generate_uuid(self):
        import uuid
        return str(uuid.uuid4())

    def _get_client_company_info(self):
        self.ensure_one()
        company = self.env.company
        web_base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url') or ''
        return {
            'company_name': company.name or '',
            'web_base_url': web_base_url,
            'company_vat': company.vat or '',
            'company_email': company.email or '',
            'company_phone': company.phone or '',
        }

    def action_register(self):
        self.ensure_one()
        if not self.service_url:
            raise UserError('Debe indicar la URL del backend en la configuración.')
        if not self.client_uuid:
            self.client_uuid = self._generate_uuid()
        payload = {
            'hw_fingerprint': self.hw_fingerprint,
            'db_name': self.env.cr.dbname,
            'odoo_version': self.env['ir.module.module'].sudo().search([('name', '=', 'base')], limit=1).latest_version or '18.0',
            'modules': self._build_inventory(),
        }
        payload.update(self._get_client_company_info())
        result = self._call_backend('/api/v1/auto-register', payload)
        if isinstance(result, dict):
            self.registration_state = result.get('status', 'not_registered')
            self.registration_message = result.get('message', '')
            if result.get('api_key'):
                self.api_key = result.pop('api_key')
        self._log_history('registration', 'Registro', None, None, self.registration_message or 'Solicitud de registro enviada.')
        return True

    def action_activate(self):
        self.ensure_one()
        config = self
        if not config.enforcement_enabled:
            config.enforcement_enabled = True
            config.state = 'active'
            self._log_history('activation', 'Activación', None, None, 'Activación manual de control desde el cliente.')
        return True

    def action_deactivate(self):
        self.ensure_one()
        self.enforcement_enabled = False
        self.state = 'standby'
        self._log_history('activation', 'Desactivación', None, None, 'Control desactivado (vuelta a modo standby).')
        return True

    def action_run_inventory(self):
        self.ensure_one()
        inventory = self._build_inventory()
        self.last_inventory = inventory
        self.last_inventory_at = fields.Datetime.now()
        self._log_history('inventory', 'Inventario', None, None, f"Inventario ejecutado: {len(inventory)} módulos.")
        return True

    def action_heartbeat(self):
        self.ensure_one()
        return self._send_heartbeat()

    @api.model
    def _cron_run_inventory(self):
        config = self._get_or_create()
        config.action_run_inventory()
        config._send_heartbeat()
        return True

    @api.model
    def _cron_run_heartbeat(self):
        config = self._get_or_create()
        config.action_run_inventory()
        config._send_heartbeat()
        return True

    def _build_inventory(self):
        self.ensure_one()
        modules = self.env['ir.module.module'].sudo().search([
            ('state', '=', 'installed'),
        ], order='name asc')
        inventory = []
        for mod in modules:
            inventory.append({
                'name': mod.name or '',
                'shortdesc': mod.shortdesc or mod.name or '',
                'version': mod.installed_version or mod.latest_version or '',
                'author': mod.author or '',
                'website': mod.website or '',
                'state': mod.state or 'installed',
            })
        return inventory

    def _send_heartbeat(self):
        self.ensure_one()
        if not self.client_uuid or not self.api_key:
            self.registration_message = 'No registrado aún. Ejecute el registro primero.'
            return False
        try:
            current_inv = self._build_inventory()
            self.last_inventory = current_inv
            self.last_inventory_at = fields.Datetime.now()
            payload = {
                'client_uuid': self.client_uuid,
                'hw_fingerprint': self.hw_fingerprint,
                'odoo_version': self.env['ir.module.module'].sudo().search([('name', '=', 'base')], limit=1).latest_version or '18.0',
                'modules': current_inv,
            }
            payload.update(self._get_client_company_info())
            result = self._call_backend('/api/v1/heartbeat', payload, headers={'X-API-Key': self.api_key})
            self.last_heartbeat = fields.Datetime.now()
            if isinstance(result, dict) and result.get('token'):
                self.token_cipher = result['token']
                self.token_expiry = fields.Datetime.now() + timedelta(days=30)
                self.last_heartbeat_status = 'ok'
                if result.get('config_updated', {}).get('new_api_key'):
                    self.api_key = result['config_updated']['new_api_key']
                activation = result.get('config_updated', {}).get('activation_state')
                if activation in ('active', 'standby'):
                    target = activation == 'active'
                    if target and not self.enforcement_enabled:
                        self.enforcement_enabled = True
                        self.state = 'active'
                        self._log_history('activation', 'Activación', None, None,
                                          'Activación remota de control desde el backend.')
                    elif not target and self.enforcement_enabled:
                        self.enforcement_enabled = False
                        self.state = 'standby'
                        self._log_history('activation', 'Desactivación', None, None,
                                          'Desactivación remota de control desde el backend.')
                
                # Procesar alerta bajo demanda desde el backend
                if result.get('support_alert'):
                    self.support_alert_active = True
                    self.support_alert_type = result.get('alert_type', 'support_required')
                    self.support_alert_message = result.get('alert_message', '')
                else:
                    self.support_alert_active = False
                    self.support_alert_type = 'none'
                    self.support_alert_message = ''
                return True
            else:
                self.last_heartbeat_status = 'error'
                return False
        except Exception as e:
            self.last_heartbeat_status = 'error'
            self.registration_message = str(e)
            return False

    def action_test_trigger_alert(self):
        """Dispara localmente una alerta de soporte bajo demanda para pruebas."""
        self.ensure_one()
        self.support_alert_active = True
        self.support_alert_type = 'support_required'
        if not self.support_alert_message:
            self.support_alert_message = (
                "⚠️ ALERTA DE PRUEBA: Estimado cliente, por favor comuníquese con el "
                "Servicio de Soporte Técnico y Funcional."
            )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '🔔 Alerta de Prueba Activada',
                'message': self.support_alert_message,
                'type': 'warning',
                'sticky': True,
            }
        }

    def action_clear_alert(self):
        """Limpia la alerta de soporte activa."""
        self.ensure_one()
        self.support_alert_active = False
        self.support_alert_type = 'none'
        self.support_alert_message = ''
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '✅ Alerta Desactivada',
                'message': 'Se ha desactivado la alerta de soporte.',
                'type': 'success',
                'sticky': False,
            }
        }


    def _call_backend(self, path, payload, headers=None):
        import json
        import urllib.request
        url = (self.service_url or '').rstrip('/') + path
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'soportehelp-client/1.0',
                **(headers or {}),
            },
            method='POST',
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode('utf-8')
            return json.loads(raw) if raw else {}

    def is_maintenance_window(self):
        self.ensure_one()
        return bool(self.maintenance_until and self.maintenance_until > fields.Datetime.now())

    def _log_history(self, event_type, module_name, version_from, version_to, message):
        self.env['soportehelp.history'].create({
            'config_id': self.id,
            'event_type': event_type,
            'module_name': module_name or '',
            'version_from': version_from or '',
            'version_to': version_to or '',
            'message': message or '',
        })


class SoporteHelpCompanyAlert(models.Model):
    _name = 'soportehelp.company.alert'
    _description = 'Alerta de Soporte por Compañía (Multi-Empresa)'

    config_id = fields.Many2one(
        'soportehelp.config', string='Configuración', required=True, ondelete='cascade'
    )
    company_id = fields.Many2one(
        'res.company', string='Empresa / Compañía', required=True, ondelete='cascade'
    )
    support_alert_active = fields.Boolean(string='Alerta Activa para esta Empresa', default=False)
    support_alert_type = fields.Char(string='Tipo de Alerta', default='none')
    support_alert_message = fields.Text(string='Mensaje de Alerta de esta Empresa')