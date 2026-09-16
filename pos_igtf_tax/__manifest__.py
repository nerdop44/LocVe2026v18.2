# -*- coding: utf-8 -*-
{
    'name': '[LocVe] POS IGTF',
    'version': '18.0.2.0.0',
    'author': 'Ing. Nerdo Jose Pulido Aguirre',
    'website': 'https://github.com/nerdop44',
    'category': 'LocVe [Localization]',
    'summary': 'Impuesto IGTF en el Punto de Venta para la suite LocVe (OPCIONAL).',
    'depends': ['point_of_sale', 'pos_show_dual_currency'],
    'data': ['views/inherited_views.xml'],
    'assets': {'point_of_sale._assets_pos': ['pos_igtf_tax/static/src/scss/**/*', 'pos_igtf_tax/static/src/app/**/*.js']},
    'license': 'LGPL-3',
    'installable': True,
    'description': 'Impuesto IGTF en el Punto de Venta para la suite LocVe (OPCIONAL).\nCalcula y registra automáticamente el IGTF (3%) en pagos del POS\nrealizados en divisas o criptomonedas, conforme a la Ley IGTF venezolana.\nSolo instalar en empresas con Punto de Venta y pagos en divisas.\nAutor: Ing. Nerdo Jose Pulido Aguirre',
    'auto_install': False,
}
