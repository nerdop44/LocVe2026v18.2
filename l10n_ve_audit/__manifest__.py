# -*- coding: utf-8 -*-
{
    'name': '[LocVe] Auditoría Fiscal (SENIAT)',

    'version': '18.0.1.0.2',

    'author': 'Ing. Nerdo Jose Pulido Aguirre',
    'website': 'https://github.com/nerdop44',
    'category': 'Accounting/Localizations/Account Chart',
    'summary': 'Control y logs de auditoría inmutables para cumplimiento de normas SENIAT.',
    'description': """
Módulo de Auditoría Fiscal para la Localización Venezolana (LocVe).
- Crea el rol 'Auditor Fiscal (SENIAT)' con acceso estrictamente de solo lectura a la contabilidad y logs.
- Registra de forma inmutable todas las acciones clave (creación, publicación, reversión, eliminación) sobre facturas y pagos.
- Mantiene una Tabla de Auditoría inalterable accesible por el auditor fiscal.
    """,
    'depends': ['account', 'l10n_ve_base', 'l10n_ve_invoice', 'sale', 'purchase', 'account_dual_currency'],
    'data': [
        'security/res_groups.xml',
        'security/ir.model.access.csv',
        'views/l10n_ve_audit_log_views.xml',
        'views/menu_views.xml',
        'views/seniat_compliance_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'l10n_ve_audit/static/src/css/seniat_compliance.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
