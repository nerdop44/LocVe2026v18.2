# -*- coding: utf-8 -*-
{
    'name': '[LocVe] POS Vendedor',
    'summary': 'Campo de vendedor en el Punto de Venta para la suite LocVe (OPCIONAL).',
    'author': 'Ing. Nerdo Jose Pulido Aguirre',
    'website': 'https://github.com/nerdop44',
    'category': 'Point of Sale',
    'version': '18.0.2.0.0',
    'depends': ['hr', 'point_of_sale', 'pos_hr'],
    'data': ['security/ir.model.access.csv', 'views/pos_config.xml', 'views/pos_order_view.xml', 'views/res_config_settings_views.xml'],
    'assets': {'point_of_sale._assets_pos': ['pos_salesman/static/src/app/**/*']},
    'license': 'LGPL-3',
    'installable': True,
    'description': 'Campo de vendedor en el Punto de Venta para la suite LocVe (OPCIONAL).\nPermite asignar un vendedor a cada orden de POS para seguimiento de comisiones\ny reportes de ventas por vendedor.\nSolo instalar en empresas que manejen esquemas de comisiones por vendedor en POS.\nAutor: Ing. Nerdo Jose Pulido Aguirre',
    'auto_install': False,
}
