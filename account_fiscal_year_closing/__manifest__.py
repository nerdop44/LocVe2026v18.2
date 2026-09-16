# -*- coding: utf-8 -*-
{
    'name': '[LocVe] Motor de Cierre de Año Fiscal',
    'summary': 'Motor técnico de cierre de año fiscal para la Localización LocVe.',
    'version': '18.0.2.0.1',

    'category': 'Accounting & Finance',
    'website': 'https://github.com/nerdop44',
    'author': 'Ing. Nerdo Jose Pulido Aguirre',
    'license': 'AGPL-3',
    'installable': True,
    'depends': ['account', 'date_range'],
    'data': ['security/account_fiscalyear_closing_security.xml', 'security/ir.model.access.csv', 'views/account_fiscalyear_closing_views.xml', 'views/account_fiscalyear_closing_template_views.xml', 'views/account_move_views.xml', 'wizards/account_fiscal_year_closing_unbalanced_move_views.xml'],
    'description': 'Motor técnico de cierre de año fiscal para la Localización LocVe.\n\nProporciona la infraestructura base para el proceso de cierre contable:\n- Generación de asientos de cierre de ingresos y gastos\n- Apertura automática del nuevo período fiscal\n- Compatible con el calendario fiscal venezolano\nRequerido por l10n_ve_account_fiscalyear_closing.\nAutor: Ing. Nerdo Jose Pulido Aguirre',
}
