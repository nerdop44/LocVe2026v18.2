from odoo import models, fields, api
from odoo.exceptions import UserError


class SoporteHelpTicket(models.Model):
    _name = 'soportehelp.ticket'
    _description = 'Ticket de Soporte'
    _rec_name = 'name'
    _order = 'create_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    config_id = fields.Many2one(
        'soportehelp.config',
        string='Configuración',
        default=lambda self: self.env['soportehelp.config']._get_or_create().id,
        ondelete='cascade',
    )
    name = fields.Char(string='Asunto', required=True)
    description = fields.Text(string='Descripción', required=True)
    priority = fields.Selection(
        [('low', 'Baja'), ('normal', 'Normal'), ('high', 'Alta'), ('urgent', 'Urgente')],
        string='Prioridad',
        default='normal',
    )
    state = fields.Selection(
        [
            ('draft', 'Borrador'),
            ('open', 'Abierto'),
            ('in_progress', 'En Progreso'),
            ('answered', 'Respondido'),
            ('pending_client', 'Esperando el Cliente'),
            ('closed', 'Cerrado'),
        ],
        string='Estado',
        default='draft',
        tracking=True,
    )
    ticket_ref = fields.Char(
        string='Ref. Backend',
        readonly=True,
        help='Número de ticket asignado por el backend.',
    )
    assigned_agent_name = fields.Char(string='Agente de Soporte Asignado', readonly=True, help='Especialista de ControlDes asignado a atender su requerimiento.')
    assigned_agent_email = fields.Char(string='Correo de Soporte', readonly=True)
    assigned_team_name = fields.Char(string='Equipo de Soporte', readonly=True, help='Equipo de especialistas asignado en ControlDes.')
    client_user_name = fields.Char(string='Solicitante', readonly=True)
    last_error = fields.Text(string='Último Error de Sincronización', readonly=True)

    # SLA & Timesheets (Backend Sync)
    sla_status = fields.Selection([
        ('in_progress', 'En Tiempo'),
        ('reached', 'Cumplido'),
        ('failed', 'Incumplido / Vencido'),
    ], string='Estado SLA', readonly=True)
    sla_deadline = fields.Datetime(string='Fecha Límite SLA', readonly=True)
    total_hours_spent = fields.Float(string='Horas de Soporte Invertidas', readonly=True)

    # CSAT Customer Rating (Client Interactive)
    csat_rating = fields.Selection([
        ('1', '🙁 Malo'),
        ('3', '😐 Regular'),
        ('5', '😃 Excelente'),
    ], string='Su Calificación', tracking=True)
    csat_comment = fields.Text(string='Comentario / Sugerencia')

    def action_rate_excellent(self):
        return self.action_submit_csat('5')

    def action_rate_neutral(self):
        return self.action_submit_csat('3')

    def action_rate_bad(self):
        return self.action_submit_csat('1')

    def action_submit_csat(self, rating=None, comment=None):
        self.ensure_one()
        r_val = rating or self.csat_rating or '5'
        c_val = comment or self.csat_comment or ''
        self.write({
            'csat_rating': r_val,
            'csat_comment': c_val,
        })
        if self.ticket_ref and self.config_id and self.config_id.api_key:
            try:
                self.config_id._call_backend('/api/v1/helpdesk/rating', {
                    'client_uuid': self.config_id.client_uuid,
                    'ticket_ref': self.ticket_ref,
                    'rating': r_val,
                    'comment': c_val,
                }, headers={'X-API-Key': self.config_id.api_key})
            except Exception:
                pass
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '⭐ Calificación Registrada',
                'message': '¡Muchas gracias por su retroalimentación!',
                'type': 'success',
                'sticky': False,
            }
        }

    @api.model_create_multi
    def create(self, vals_list):
        tickets = super().create(vals_list)
        for ticket in tickets:
            if not ticket.client_user_name:
                ticket.client_user_name = ticket.env.user.name
            if ticket.env.user.partner_id:
                try:
                    ticket.message_subscribe(partner_ids=[ticket.env.user.partner_id.id])
                except Exception:
                    pass
        return tickets

    def message_post(self, **kwargs):
        res = super().message_post(**kwargs)
        if not self.env.context.get('skip_remote_sync'):
            body = kwargs.get('body') or (kwargs.get('message_dict', {}).get('body') if isinstance(kwargs.get('message_dict'), dict) else '')
            if body and self.ticket_ref and self.config_id and self.config_id.api_key:
                try:
                    self.config_id.with_context(skip_remote_sync=True)._call_backend('/api/v1/helpdesk/message', {
                        'client_uuid': self.config_id.client_uuid,
                        'ticket_ref': self.ticket_ref,
                        'content': body,
                        'client_user_name': self.env.user.name,
                    }, headers={'X-API-Key': self.config_id.api_key})
                except Exception:
                    pass
        return res

    def action_send(self):
        self.ensure_one()
        config = self.config_id
        if not config.service_url:
            config.service_url = 'https://of.venrides.com'

        if config.registration_state == 'not_registered':
            try:
                config.action_register()
            except Exception:
                pass

        if config.registration_state != 'approved':
            raise UserError('Por favor comuníquese con el Servicio de Soporte Técnico y Funcional para la atención y activación de su servicio de soporte.')

        user = self.env.user
        partner = user.partner_id
        user_phone = user.phone or user.mobile or partner.phone or partner.mobile or ''
        user_job = partner.function or getattr(user, 'function', False) or ''

        payload = {
            'subject': self.name,
            'description': self.description,
            'priority': self.priority,
            'client_uuid': config.client_uuid,
            'client_user_name': user.name,
            'client_user_email': user.email or partner.email or '',
            'client_user_phone': user_phone,
            'client_user_job': user_job,
        }
        payload.update(config._get_client_company_info())
        payload['modules'] = config._build_inventory()
        try:
            result = config._call_backend('/api/v1/helpdesk/ticket', payload,
                                          headers={'X-API-Key': config.api_key})
            if isinstance(result, dict) and result.get('ticket_ref'):
                self.ticket_ref = result['ticket_ref']
                self.state = 'open'
                if result.get('assigned_agent_name'):
                    self.assigned_agent_name = result['assigned_agent_name']
                if result.get('assigned_team_name'):
                    self.assigned_team_name = result['assigned_team_name']
                self.last_error = ''
                self.message_post(body=(
                    f"Ticket enviado al servicio de soporte. "
                    f"Referencia: <b>{result['ticket_ref']}</b>"
                ))
                config._log_history('ticket', 'Helpdesk', None, None,
                                    f"Ticket enviado: {self.name} ({result['ticket_ref']})")
                return True
            else:
                self.last_error = str(result)
                return False
        except Exception as e:
            # Save locally gracefully
            import secrets
            if not self.ticket_ref:
                self.ticket_ref = f"TRIAL-{secrets.token_hex(3).upper()}"
            self.state = 'open'
            self.last_error = str(e)
            self.message_post(body=(
                "Solicitud de soporte registrada localmente. Por favor comuníquese con el "
                "Servicio de Soporte Técnico y Funcional para el seguimiento."
            ))
            return True

    @api.model
    def _cron_sync_tickets(self):
        tickets = self.search([('ticket_ref', '!=', False)])
        for ticket in tickets:
            try:
                ticket.action_sync()
            except Exception:
                pass
        return True

    def action_sync(self):
        self.ensure_one()
        if not self.ticket_ref:
            return self.action_send()
        config = self.config_id
        try:
            result = config._call_backend('/api/v1/helpdesk/messages', {
                'client_uuid': config.client_uuid,
                'ticket_ref': self.ticket_ref,
            }, headers={'X-API-Key': config.api_key})
            if isinstance(result, dict):
                # 1. Real-time state mapping and synchronization
                b_state = result.get('state')
                if b_state:
                    state_map = {
                        'new': 'open',
                        'in_progress': 'open',
                        'pending_client': 'pending_client',
                        'answered': 'answered',
                        'solved': 'closed',
                        'closed': 'closed',
                        'cancel': 'closed',
                    }
                    mapped_state = state_map.get(b_state, b_state)
                    if self.state != mapped_state and mapped_state in ('draft', 'open', 'answered', 'pending_client', 'closed'):
                        self.state = mapped_state

                if result.get('assigned_agent_name'):
                    self.assigned_agent_name = result['assigned_agent_name']
                if result.get('assigned_team_name'):
                    self.assigned_team_name = result['assigned_team_name']
                if result.get('sla_status'):
                    self.sla_status = result['sla_status']
                if result.get('sla_deadline'):
                    try:
                        self.sla_deadline = fields.Datetime.from_string(result['sla_deadline'].replace('T', ' ')[:19])
                    except Exception:
                        pass
                if result.get('total_hours_spent') is not None:
                    self.total_hours_spent = float(result['total_hours_spent'])
                if result.get('csat_rating'):
                    self.csat_rating = result['csat_rating']
                if result.get('csat_comment'):
                    self.csat_comment = result['csat_comment']

                # 2. Sync chatter messages
                if result.get('messages'):
                    existing = self.message_ids
                    posted = 0
                    import re
                    from markupsafe import Markup
                    for msg in result['messages']:
                        raw_content = msg.get('content', '')
                        if not raw_content:
                            continue
                        clean_content = re.sub('<[^<]+?>', '', raw_content).strip()
                        already_exists = False
                        if clean_content:
                            for m in existing:
                                m_clean = re.sub('<[^<]+?>', '', m.body or '').strip()
                                if m_clean and (clean_content == m_clean or clean_content in m_clean or m_clean in clean_content):
                                    already_exists = True
                                    break
                        if not already_exists:
                            author_name = msg.get('author', 'Soporte Técnico')
                            agent_partner = self.env['res.partner'].sudo().search([('name', '=', author_name)], limit=1)
                            if not agent_partner:
                                agent_partner = self.env['res.partner'].sudo().create({'name': author_name, 'comment': 'Agente ControlDes'})
                            self.with_context(
                                mail_create_nosubscribe=True,
                                mail_auto_delete=False,
                                skip_remote_sync=True,
                            ).message_post(
                                body=Markup(raw_content),
                                subject=f"Respuesta de soporte ({author_name})",
                                author_id=agent_partner.id,
                                message_type='comment',
                                subtype_xmlid='mail.mt_comment',
                            )
                            posted += 1
                    if posted:
                        self.last_error = ''
                        try:
                            self.env['bus.bus'].sudo()._sendone(
                                'mail.record/soportehelp.ticket',
                                'mail.record/insert',
                                {'id': self.id}
                            )
                        except Exception:
                            pass
                return True
            return False
        except Exception as e:
            self.last_error = str(e)
            return False

    def action_close(self):
        self.ensure_one()
        self.state = 'closed'
        res = None
        if self.ticket_ref:
            try:
                res = self.config_id._call_backend('/api/v1/helpdesk/message', {
                    'client_uuid': self.config_id.client_uuid,
                    'ticket_ref': self.ticket_ref,
                    'content': 'El ticket fue cerrado por el cliente.',
                }, headers={'X-API-Key': self.config_id.api_key})
            except Exception:
                res = None
        self.message_post(body="Ticket cerrado por el cliente.")
        return res