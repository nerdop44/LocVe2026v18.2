# -*- coding: utf-8 -*-
{
    'name': '[LocVe] Reportes Contables Multi-Moneda',
    'version': '18.0.2.0.1',
    'category': 'LocVe [Localization]',
    'license': 'Other proprietary',
    'summary': 'Módulo de reportes contables en doble moneda para la suite LocVe (OPCIONAL).',
    'description': 'Módulo de reportes contables en doble moneda para la suite LocVe (OPCIONAL).\n\nGenera los principales informes contables en moneda local (Bs.) y divisa simultáneamente:\n- Balance General en doble moneda\n- Estado de Resultados en doble moneda\n- Libro Diario con columnas Bs. y Divisa\n- Libro Mayor con saldos en ambas monedas\n- Balance de Comprobación bimoneda\nSolo instalar en empresas que requieran reportes con doble moneda.\nAutor: Ing. Nerdo Jose Pulido Aguirre',
    'author': 'Ing. Nerdo Jose Pulido Aguirre',
    'website': 'https://github.com/nerdop44',
    'depends': ['account_dual_currency', 'account_reports'],
    'data': ['views/search_template_view.xml'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
