# -*- coding: utf-8 -*-
{
    'name': '[LocVe] LocVe Core Facturación',
    'website': 'https://github.com/nerdop44',
    'icon': '/account/static/description/l10n.png',
    'countries': ['ve'],
    'author': 'Ing. Nerdo Jose Pulido Aguirre',
    'category': 'Accounting/Localizations/Account Charts',
    'description': "Módulo core de facturación extendida para la suite LocVe Venezuela.\n\nExtiende el módulo de facturación con funcionalidades avanzadas:\n- Vista unificada de facturas con campos venezolanos (doble moneda, tasas)\n- Asistente de reportes de facturación en Bs. y divisa\n- Integración con el libro de compras y ventas\n- Base para la impresora fiscal del POS LocVe\nNota: El nombre técnico 'l10n_ve_binaural' se mantiene por compatibilidad\ncon instalaciones existentes. El nombre visible es LocVe Core Facturación.\nAutor: Ing. Nerdo Jose Pulido Aguirre",
    'depends': ['account', 'l10n_ve_location', 'l10n_ve_invoice'],
    'demo': ['demo/demo_company.xml'],
    'data': ['security/ir_rule.xml', 'data/ir_sequence.xml', 'views/account_journal_views.xml', 'views/account_move_views.xml', 'views/res_config_settings_views.xml', 'views/res_partner_views.xml', 'views/l10n_ve_menuitems.xml'],
    'version': '18.0.2.0.5',

    'license': 'LGPL-3',
    'summary': 'Módulo core de facturación extendida para la suite LocVe Venezuela.',
    'installable': True,
}
