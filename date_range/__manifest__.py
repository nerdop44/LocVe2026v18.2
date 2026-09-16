# -*- coding: utf-8 -*-
{
    'name': '[LocVe] Rangos de Fechas Fiscales',
    'summary': 'Rangos de fechas fiscales para la Localización Venezolana LocVe.',
    'version': '18.0.2.0.0',
    'category': 'Uncategorized',
    'website': 'https://github.com/nerdop44',
    'author': 'Ing. Nerdo Jose Pulido Aguirre',
    'license': 'LGPL-3',
    'installable': True,
    'depends': ['web'],
    'data': ['data/ir_cron_data.xml', 'security/ir.model.access.csv', 'security/date_range_security.xml', 'views/date_range_view.xml', 'wizard/date_range_generator.xml'],
    'assets': {'web.assets_backend': ['date_range/static/src/js/*']},
    'development_status': 'Mature',
    'maintainers': ['lmignon'],
    'description': 'Rangos de fechas fiscales para la Localización Venezolana LocVe.\n\nPermite definir y gestionar períodos contables y rangos de fechas\nutilizados en reportes y cierres del ejercicio fiscal venezolano.\nRequerido por el módulo de cierre de año fiscal LocVe.\nAutor: Ing. Nerdo Jose Pulido Aguirre',
}
