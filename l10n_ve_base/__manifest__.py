# -*- coding: utf-8 -*-
{
    'name': '[LocVe] Base Venezuela',
    'summary': 'Módulo base de la Localización Venezolana LocVe para Odoo 18.',
    'license': 'LGPL-3',
    'author': 'Ing. Nerdo Jose Pulido Aguirre',
    'website': 'https://github.com/nerdop44',
    'category': 'Technical',
    'version': '18.0.2.0.0',
    'depends': ['base', 'base_setup'],
    'auto_install': True,
    'data': ['views/res_config_settings_views.xml'],
    'description': 'Módulo base de la Localización Venezolana LocVe para Odoo 18.\n\nProporciona la estructura fundamental que todos los módulos de la\nlocalización requieren:\n- Configuración de empresa con datos fiscales venezolanos (RIF, SENIAT)\n- Moneda base y moneda alterna (Doble Moneda)\n- Parámetros de configuración del sistema para Venezuela\n- Campos comunes a todos los módulos LocVe\n\nEste módulo es la base requerida por toda la suite LocVe.\nAutor: Ing. Nerdo Jose Pulido Aguirre',
}
