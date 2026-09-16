# -*- coding: utf-8 -*-
{
    'name': '[LocVe] Cierre de Año Fiscal Venezuela',
    'summary': 'Módulo de cierre de año fiscal venezolano para la suite LocVe.',
    'license': 'LGPL-3',
    'author': 'Ing. Nerdo Jose Pulido Aguirre',
    'website': 'https://github.com/nerdop44',
    'category': 'Accounting/Localizations/Account Chart',
    'version': '18.0.2.0.1',

    'depends': ['account_fiscal_year_closing', 'l10n_ve_contact', 'l10n_ve_rate'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/l10n_ve_revaluation_wizard_views.xml',
        'views/account_fiscalyear_closing.xml',
        'views/account_fiscalyear_closing_template.xml',
    ],
    'images': ['static/description/icon.png'],
    'application': True,
    'description': 'Módulo de cierre de año fiscal venezolano para la suite LocVe.\n\nImplementa el proceso completo de cierre contable conforme a la normativa venezolana:\n- Plantillas de cierre predefinidas (ingresos, gastos, utilidad/pérdida del ejercicio)\n- Generación automática de asientos de cierre y apertura\n- Compatibilidad con el calendario fiscal venezolano (enero-diciembre)\n- Informe de cierre con detalle de cuentas afectadas\n- Configuración de cuentas de resultado y patrimonio según Plan de Cuentas SENIAT\nAutor: Ing. Nerdo Jose Pulido Aguirre',
    'installable': True,
}
