# -*- coding: utf-8 -*-
{
    'name': '[LocVe] Tasa de Cambio BCV',
    'summary': 'Tasa de cambio oficial del Banco Central de Venezuela para LocVe.',
    'license': 'LGPL-3',
    'author': 'Ing. Nerdo Jose Pulido Aguirre',
    'website': 'https://github.com/nerdop44',
    'category': 'Technical',
    'version': '18.0.2.0.0',
    'depends': ['base', 'base_setup', 'l10n_ve_base'],
    'data': ['views/res_config_settings.xml'],
    'installable': True,
    'description': 'Tasa de cambio oficial del Banco Central de Venezuela para LocVe.\n\nObtiene y gestiona la tasa de cambio oficial BCV (Bolívar/Divisa).\n- Consulta directa a la fuente oficial del BCV\n- Actualización periódica configurable\n- Tasa disponible en facturas, retenciones e informes fiscales\n- Base del sistema de doble moneda LocVe\nAutor: Ing. Nerdo Jose Pulido Aguirre',
}
