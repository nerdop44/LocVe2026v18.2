import os
import hashlib
import hmac
import json

_MODULE_PATHS = ['l10n_ve_tax', 'l10n_ve_invoice', 'l10n_ve_payment_extension']
_EXCLUDE_FILES = ['__pycache__', '.pyc', '.so', '.pyo']


class SoporteHelpFactorB:

    def __init__(self, get_param_callback, set_param_callback=None):
        self._get_param = get_param_callback
        self._set_param = set_param_callback or (lambda name, value: None)
        self._seed = None

    @property
    def seed_param(self):
        return 'soportehelp.checksum_seed'

    def _load_seed(self):
        if self._seed is None:
            raw = self._get_param(self.seed_param, '')
            if not raw:
                import secrets
                raw = secrets.token_hex(16)
                self._set_param(self.seed_param, raw)
            self._seed = raw.encode('utf-8')
        return self._seed

    def _get_module_files(self, module_name, addons_path):
        module_dir = os.path.join(addons_path, module_name)
        if not os.path.isdir(module_dir):
            return []
        files = []
        for root, dirs, filenames in os.walk(module_dir):
            dirs[:] = [d for d in dirs if d not in _EXCLUDE_FILES]
            for f in filenames:
                if any(f.endswith(ext) for ext in _EXCLUDE_FILES):
                    continue
                files.append(os.path.join(root, f))
        return sorted(files)

    def _compute_file_hash(self, filepath):
        h = hashlib.sha256()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                h.update(chunk)
        return h.hexdigest()

    def compute_checksum(self, addons_path, modules=None):
        if modules is None:
            modules = _MODULE_PATHS
        seed = self._load_seed()
        checksums = {}
        for mod in modules:
            files = self._get_module_files(mod, addons_path)
            for fp in files:
                rel_path = os.path.relpath(fp, addons_path)
                file_hash = self._compute_file_hash(fp)
                combined = f"{rel_path}:{file_hash}"
                sig = hmac.new(seed, combined.encode('utf-8'), hashlib.sha256).hexdigest()
                checksums[rel_path] = sig
        master = hmac.new(
            seed,
            json.dumps(checksums, sort_keys=True).encode('utf-8'),
            hashlib.sha256,
        ).hexdigest()
        return master, checksums

    def verify_checksum(self, addons_path, expected_master, modules=None):
        if modules is None:
            modules = _MODULE_PATHS
        try:
            actual_master, _ = self.compute_checksum(addons_path, modules)
            return hmac.compare_digest(actual_master, expected_master)
        except Exception:
            return False


def check(env):
    """Factor B dentro del contexto Odoo. Fail-open controlado ante errores internos."""
    try:
        params = env['ir.config_parameter'].sudo()

        def get_param(name, default=''):
            return params.get_param(name, default)

        def set_param(name, value):
            return params.set_param(name, value)

        addons_path = env['ir.config_parameter'].sudo().get_param('soportehelp.addons_path', '')
        expected = params.get_param('soportehelp.factor_b_master', '')
        if not addons_path:
            from odoo.tools import config as odoo_config
            addons_path = odoo_config.get('addons_path', '') or ''
        paths = [p for p in str(addons_path).split(',') if p.strip()]
        if not expected and paths:
            b = SoporteHelpFactorB(get_param, set_param)
            master, _ = b.compute_checksum(paths[0].strip(), _MODULE_PATHS)
            params.set_param('soportehelp.factor_b_master', master)
            return True
        b = SoporteHelpFactorB(get_param, set_param)
        for p in paths:
            if b.verify_checksum(p.strip(), expected, _MODULE_PATHS):
                return True
        return bool(expected == '')
    except Exception:
        return True