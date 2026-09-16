# -*- coding: utf-8 -*-
{
    'name': '[LocVe] Retenciones por Intermediación',
    'version': '18.0.2.0.1',
    'summary': 'Módulo de retenciones por intermediación para la suite LocVe (OPCIONAL).',
    'description': 'Módulo de retenciones por intermediación para la suite LocVe (OPCIONAL).\n\nGestiona los casos especiales de retención del SENIAT para empresas intermediarias:\n- Agencias de publicidad y propaganda\n- Empresas de seguros y reaseguros\n- Mandatarios y comisionistas\n- Agencias de viajes y turismo\nCálculo conforme a las alícuotas especiales establecidas en la providencia del SENIAT.\nSolo instalar en empresas que actúen como agentes o intermediarios.\nAutor: Ing. Nerdo Jose Pulido Aguirre',
    'author': 'Ing. Nerdo Jose Pulido Aguirre',
    'category': 'Accounting/Localizations/Accountant',
    'depends': ['l10n_ve_payment_extension', 'account_dual_currency', 'l10n_ve_tax'],
    'data': ['security/ir.model.access.csv', 'data/intermediation_case_data.xml', 'views/intermediation_case_views.xml', 'views/res_partner_views.xml', 'views/account_move_views.xml', 'views/account_retention_views.xml'],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
    'website': 'https://github.com/nerdop44',
}
