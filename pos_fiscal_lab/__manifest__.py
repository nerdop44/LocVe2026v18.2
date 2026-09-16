# -*- coding: utf-8 -*-
{
    'name': '[LocVe] POS Laboratorio Fiscal HKA',
    'version': '18.0.2.0.0',
    'category': 'LocVe [Localization]',
    'summary': 'Herramienta de diagnóstico para la impresora fiscal HKA en el POS LocVe (OPCIONAL).',
    'author': 'Ing. Nerdo Jose Pulido Aguirre',
    'website': 'https://github.com/nerdop44',
    'license': 'LGPL-3',
    'depends': ['base', 'web', 'point_of_sale', 'pos_fiscal_printer'],
    'data': ['security/ir.model.access.csv', 'data/pos_fiscal_command_data.xml', 'views/pos_fiscal_lab_views.xml'],
    'assets': {'web.assets_backend': ['pos_fiscal_lab/static/src/app/**/*']},
    'installable': True,
    'application': False,
    'description': 'Herramienta de diagnóstico para la impresora fiscal HKA en el POS LocVe (OPCIONAL).\nPermite a los técnicos realizar pruebas de conectividad, imprimir documentos\nde prueba y diagnosticar problemas de comunicación con la impresora fiscal.\nMódulo técnico — No instalar en producción sin necesidad de diagnóstico.\nAutor: Ing. Nerdo Jose Pulido Aguirre',
    'auto_install': False,
}
