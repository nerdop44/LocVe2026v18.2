from odoo import http


class SoporteHelpController(http.Controller):

    @http.route('/soporte-ayuda/info', type='json', auth='user', methods=['POST'], csrf=False)
    def get_info(self, **kwargs):
        config = http.request.env['soportehelp.config'].sudo()._get_or_create()
        return {
            'registration_state': config.registration_state,
            'client_uuid': config.client_uuid,
            'client_name': config.client_name,
            'control_mode': config.control_mode,
            'service_url': config.service_url,
            'terms_accepted': config.terms_accepted,
            'maintenance_active': config.maintenance_active,
            'maintenance_until': config.maintenance_until,
        }

    @http.route('/soporte-ayuda/apply-maintenance', type='json', auth='user', methods=['POST'], csrf=False)
    def apply_maintenance(self, token=None, **kwargs):
        if not token:
            return {'ok': False, 'error': 'token_required'}
        return http.request.env['soportehelp.core'].apply_maintenance_token(token)

    @http.route('/api/v1/soportehelp/push_message', type='json', auth='none', methods=['POST'], csrf=False)
    def receive_push_message(self, **kwargs):
        data = kwargs or getattr(http.request, 'params', {})
        api_key = http.request.httprequest.headers.get('X-API-Key')
        config = http.request.env['soportehelp.config'].sudo()._get_or_create()
        if not api_key or api_key != config.api_key:
            return {'status': 'error', 'message': 'unauthorized'}
        
        ticket_ref = data.get('ticket_ref')
        message_content = data.get('content')
        author = data.get('author') or 'Soporte Técnico'
        state = data.get('state')
        assigned_agent_name = data.get('assigned_agent_name') or author
        assigned_team_name = data.get('assigned_team_name')
        
        if not ticket_ref or not message_content:
            return {'status': 'error', 'message': 'missing parameters'}
            
        ticket = http.request.env['soportehelp.ticket'].sudo().search([('ticket_ref', '=', ticket_ref)], limit=1)
        if not ticket:
            return {'status': 'error', 'message': 'ticket not found'}
            
        vals = {}
        if state:
            vals['state'] = state
        if assigned_agent_name:
            vals['assigned_agent_name'] = assigned_agent_name
        if assigned_team_name:
            vals['assigned_team_name'] = assigned_team_name
        if vals:
            ticket.sudo().write(vals)

        import re
        from markupsafe import Markup
        clean_content = re.sub('<[^<]+?>', '', message_content).strip()
        already_exists = False
        if clean_content:
            for m in ticket.message_ids:
                m_clean = re.sub('<[^<]+?>', '', m.body or '').strip()
                if m_clean and (clean_content == m_clean or clean_content in m_clean or m_clean in clean_content):
                    already_exists = True
                    break
                
        if not already_exists:
            agent_partner = http.request.env['res.partner'].sudo().search([('name', '=', author)], limit=1)
            if not agent_partner:
                agent_partner = http.request.env['res.partner'].sudo().create({
                    'name': author,
                    'email': data.get('assigned_agent_email', 'soporte@control-des.com'),
                    'comment': 'Especialista de atención técnica ControlDes',
                })
            ticket.sudo().with_context(
                mail_create_nosubscribe=True,
                mail_auto_delete=False,
                skip_remote_sync=True,
            ).message_post(
                body=Markup(message_content),
                subject=f"Respuesta de soporte ({author})",
                author_id=agent_partner.id,
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
            )
            try:
                http.request.env['bus.bus'].sudo()._sendone(
                    'mail.record/soportehelp.ticket',
                    'mail.record/insert',
                    {'id': ticket.id}
                )
            except Exception:
                pass
        return {'status': 'ok'}

    @http.route('/api/v1/soportehelp/push_calendar_event', type='json', auth='none', methods=['POST'], csrf=False)
    def receive_push_calendar_event(self, **kwargs):
        data = kwargs or getattr(http.request, 'params', {})
        api_key = http.request.httprequest.headers.get('X-API-Key')
        config = http.request.env['soportehelp.config'].sudo()._get_or_create()
        if not api_key or api_key != config.api_key:
            return {'status': 'error', 'message': 'unauthorized'}
        
        name = data.get('name', 'Reunión de Soporte Técnico')
        start_str = data.get('start')
        stop_str = data.get('stop')
        videocall_location = data.get('videocall_location')
        description = data.get('description', '')

        if not start_str or not stop_str:
            return {'status': 'error', 'message': 'missing parameters'}

        try:
            # 1. Alarm 15 mins popup
            alarm = http.request.env['calendar.alarm'].sudo().search([('alarm_type', '=', 'notification'), ('duration', '=', 15)], limit=1)
            alarm_ids = [(4, alarm.id)] if alarm else []

            # 2. Attach default active users as attendees
            users = http.request.env['res.users'].sudo().search([('active', '=', True), ('share', '=', False)])
            partner_ids = [(6, 0, users.mapped('partner_id').ids)]

            event = http.request.env['calendar.event'].sudo().create({
                'name': name,
                'description': description,
                'start': start_str,
                'stop': stop_str,
                'videocall_location': videocall_location,
                'location': 'Google Meet (Sesión Remota)',
                'partner_ids': partner_ids,
                'alarm_ids': alarm_ids,
            })
            return {'status': 'ok', 'event_id': event.id}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}