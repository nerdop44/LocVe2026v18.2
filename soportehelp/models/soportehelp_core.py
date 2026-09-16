import hashlib
import hmac
import json
from datetime import datetime

from odoo import models, fields, api


class SoporteHelpCore(models.AbstractModel):
    _name = 'soportehelp.core'
    _description = 'Núcleo de validación del Módulo Soporte y Ayuda'

    @api.model
    def _config(self):
        return self.env['soportehelp.config']._get_or_create()

    @api.model
    def check_credentials_status(self):
        config = self._config()
        token_ok = bool(config.token_cipher)
        hb_ok = config.last_heartbeat_status == 'ok'
        b_ok = self._factor_b()
        factors = {
            'factor_a': token_ok,
            'factor_b': b_ok,
            'factor_c': hb_ok,
        }
        votes = [k for k, v in factors.items() if v]
        allows = len(votes) >= 2
        return {
            'factors': factors,
            'votes': votes,
            'allows': allows,
            'needs_registration': not config.registration_state or config.registration_state == 'not_registered',
        }

    @api.model
    def _factor_b(self):
        try:
            from . import _soportehelp_factor_b
            return _soportehelp_factor_b.check(self.env)
        except Exception:
            return False

    @api.model
    def evaluate(self, model_name='', view_type='form'):
        config = self._config()
        if config.state == 'standby' or not config.enforcement_enabled:
            return {'restricted': False, 'reason': 'standby'}
        if config.is_maintenance_window():
            return {'restricted': False, 'reason': 'maintenance_window'}
        if config.recovery_token_active and config.recovery_token_expiry and \
                config.recovery_token_expiry > fields.Datetime.now():
            return {'restricted': False, 'reason': 'recovery_token'}
        creds = self.check_credentials_status()
        if creds['allows']:
            return {'restricted': False, 'reason': 'factors_ok'}
        if creds['needs_registration']:
            return {'restricted': False, 'reason': 'not_registered'}
        if config.registration_state == 'pending':
            return {'restricted': False, 'reason': 'pending_approval'}
        return {
            'restricted': True,
            'reason': 'suspended',
            'factors': creds['factors'],
        }

    @api.model
    def apply_maintenance_token(self, token):
        """Valida un pase de mantenimiento RS256 y abre la ventana temporal."""
        config = self._config()
        payload = self._verify_rs256(token)
        if not payload:
            return {'ok': False, 'error': 'token_invalid'}
        exp_raw = payload.get('exp')
        scope = payload.get('scope')
        client_uuid = payload.get('client_uuid')
        reason = payload.get('reason', '')
        if scope != 'maintenance':
            return {'ok': False, 'error': 'wrong_scope'}
        if client_uuid and config.client_uuid and client_uuid != config.client_uuid:
            return {'ok': False, 'error': 'wrong_client'}
        if exp_raw:
            try:
                exp = self._parse_iso(exp_raw)
            except Exception:
                return {'ok': False, 'error': 'bad_exp'}
            if exp <= datetime.utcnow():
                return {'ok': False, 'error': 'expired'}
            config.maintenance_until = exp
        else:
            return {'ok': False, 'error': 'no_exp'}

        config._log_history('maintenance', 'Mantenimiento', None, None,
                            f"Pase de mantenimiento aplicado. Motivo: {reason}. Expira: {config.maintenance_until}")
        return {
            'ok': True,
            'client_uuid': client_uuid,
            'reason': reason,
            'exp': exp_raw,
        }

    @api.model
    def _verify_rs256(self, token):
        """Verifica firma RS256 con la clave pública embebida. Fallback a HMAC si no hay clave pública."""
        config = self._config()
        pubkey = config.env['ir.config_parameter'].sudo().get_param(
            'soportehelp.maintenance_pubkey', ''
        )
        if not token or '.' not in token:
            return None
        try:
            header_b64, payload_b64, sig_b64 = token.split('.')
            import base64
            def b64d(s):
                pad = '=' * (-len(s) % 4)
                return base64.urlsafe_b64decode(s + pad)
            header = json.loads(b64d(header_b64))
            payload = json.loads(b64d(payload_b64))
            alg = header.get('alg', '')
            message = f"{header_b64}.{payload_b64}".encode()
            signature = b64d(sig_b64)
            if alg == 'RS256' and pubkey:
                from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
                from cryptography.hazmat.primitives import hashes, serialization
                pub = serialization.load_pem_public_key(pubkey.encode())
                pub.verify(signature, message, asym_padding.PKCS1v15(), hashes.SHA256())
                return payload
            elif alg == 'HS256':
                secret = config.env['ir.config_parameter'].sudo().get_param(
                    'soportehelp.maintenance_secret', ''
                )
                expected = hmac.new(secret.encode(), message, hashlib.sha256).digest()
                if hmac.compare_digest(expected, signature):
                    return payload
                return None
            return None
        except Exception:
            return None

    @api.model
    def _parse_iso(self, value):
        value = value.replace('Z', '')
        try:
            return datetime.fromisoformat(value)
        except Exception:
            return datetime.strptime(value, '%Y-%m-%dT%H:%M:%S')

    @api.model
    def _monitor_versions(self):
        """Compara inventario previo vs actual y registra cambios de versión/no autorizados."""
        config = self._config()
        prev = config.last_inventory or []
        current = config._build_inventory()
        prev_map = {m['name']: m for m in prev}
        current_map = {m['name']: m for m in current}
        for name, mod in current_map.items():
            old = prev_map.get(name)
            if not old:
                config._log_history('inventory', name, None, mod.get('version'),
                                    'Nuevo módulo detectado (candidato a control).')
            elif old.get('version') != mod.get('version'):
                config._log_history('version', name, old.get('version'), mod.get('version'),
                                    'Cambio de versión detectado.')
        config.last_inventory = current
        config.last_inventory_at = fields.Datetime.now()
        return True