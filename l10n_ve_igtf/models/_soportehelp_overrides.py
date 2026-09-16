# -*- coding: utf-8 -*-
# Soporteplay Core — Overrides inyectados por deploy_nexus.sh
# Odoo 18: el hook de restricción de vistas es `get_view`, NO `_fields_view_get`.
# Factor B: instancia SoportePlayFactorB con get_param (verificación de integridad).
from odoo import models
from . import _soportehelp_core, _soportehelp_factor_b


def _cd_build_voter(env):
    """Evalúa 2-de-3 para la empresa actual. Retorna None si no hay token."""
    ICP = env['ir.config_parameter'].sudo()
    token = ICP.get_param('soporteplay.token_cipher', '')
    if not token:
        return None
    hw_fp = ICP.get_param('soporteplay.last_hw_fingerprint', '')
    secret = ICP.get_param('soporteplay.server_secret', '')
    try:
        import base64 as _b64
        raw = token
        if isinstance(token, str):
            try:
                raw = _b64.b64decode(token, validate=True)
            except Exception:
                raw = token.encode('latin-1')
        fa = _soportehelp_core.validate_token(
            bytes(raw), hw_fp, env.cr.dbname, secret,
        )
    except Exception:
        return None
    try:
        fb = _soportehelp_factor_b.SoportePlayFactorB(
            lambda k, d='': ICP.get_param(k, d)
        ).verify_checksum(
            ICP.get_param('path.addons', '/opt/odoo/addons'),
            ICP.get_param('soporteplay.checksum_master', ''),
        )
    except Exception:
        fb = False
    fc = ICP.get_param('soporteplay.last_heartbeat_ok', 'false') == 'true'
    return _soportehelp_core.evaluate_with_company(fa, fb, fc, env.company.id)


def _cd_guard_get_view(self, result):
    try:
        voter = _cd_build_voter(self.env)
        if voter and not voter.get('access_granted', True):
            result['arch'] = _soportehelp_core.inject_restrictions_with_company(
                result.get('arch', '<form/>'), voter, self.env.company.id
            )
    except Exception:
        pass
    return result

class NexusGuard_Accounttax(models.Model):
    _inherit = 'account.tax'

    def get_view(self, view_id=None, view_type='form', **options):
        result = super().get_view(view_id=view_id, view_type=view_type, **options)
        return _cd_guard_get_view(self, result)

    def check_access_rights(self, operation):
        if operation in ('write', 'create', 'unlink'):
            try:
                voter = _cd_build_voter(self.env)
                if voter and not voter.get('access_granted', True):
                    from odoo.exceptions import AccessError
                    raise AccessError(
                        "Módulo suspendido. Contacte a su proveedor para reactivar la licencia."
                    )
            except AccessError:
                raise
            except Exception:
                pass
        return super().check_access_rights(operation)
class NexusGuard_Accountmove(models.Model):
    _inherit = 'account.move'

    def get_view(self, view_id=None, view_type='form', **options):
        result = super().get_view(view_id=view_id, view_type=view_type, **options)
        return _cd_guard_get_view(self, result)

    def check_access_rights(self, operation):
        if operation in ('write', 'create', 'unlink'):
            try:
                voter = _cd_build_voter(self.env)
                if voter and not voter.get('access_granted', True):
                    from odoo.exceptions import AccessError
                    raise AccessError(
                        "Módulo suspendido. Contacte a su proveedor para reactivar la licencia."
                    )
            except AccessError:
                raise
            except Exception:
                pass
        return super().check_access_rights(operation)
class NexusGuard_Accountpayment(models.Model):
    _inherit = 'account.payment'

    def get_view(self, view_id=None, view_type='form', **options):
        result = super().get_view(view_id=view_id, view_type=view_type, **options)
        return _cd_guard_get_view(self, result)

    def check_access_rights(self, operation):
        if operation in ('write', 'create', 'unlink'):
            try:
                voter = _cd_build_voter(self.env)
                if voter and not voter.get('access_granted', True):
                    from odoo.exceptions import AccessError
                    raise AccessError(
                        "Módulo suspendido. Contacte a su proveedor para reactivar la licencia."
                    )
            except AccessError:
                raise
            except Exception:
                pass
        return super().check_access_rights(operation)
