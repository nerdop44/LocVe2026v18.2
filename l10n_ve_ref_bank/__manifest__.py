# -*- coding: utf-8 -*-
{
    'name': '[LocVe] Referencias Bancarias Venezuela',
    'summary': 'Módulo de referencias bancarias venezolanas para la suite LocVe.',
    'license': 'LGPL-3',
    'author': 'Ing. Nerdo Jose Pulido Aguirre',
    'website': 'https://github.com/nerdop44',
    'category': 'LocVe [Localization]',
    'version': '18.0.2.0.0',
    'depends': ['l10n_ve_invoice'],
    'data': ['views/account_journal.xml', 'views/res_config_settings.xml'],
    'images': ['static/description/icon.png'],
    'application': True,
    'installable': True,
    'description': 'Módulo de referencias bancarias venezolanas para la suite LocVe.\n\nGestiona y valida las referencias de transferencias bancarias venezolanas:\n- Validación de formato de referencia bancaria (8 dígitos mínimo)\n- Campo de referencia en pagos y facturas\n- Requerido para conciliación bancaria venezolana\nAutor: Ing. Nerdo Jose Pulido Aguirre',
}
