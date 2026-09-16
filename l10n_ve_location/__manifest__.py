# -*- coding: utf-8 -*-
{
    'name': '[LocVe] Localización Geográfica Venezuela',
    'summary': 'Maestros geográficos completos de Venezuela para la suite LocVe.',
    'license': 'LGPL-3',
    'author': 'Ing. Nerdo Jose Pulido Aguirre',
    'website': 'https://github.com/nerdop44',
    'category': 'Accounting/Accounting',
    'version': '18.0.2.2.1',
    'depends': ['base', 'contacts'],
    'data': ['security/ir.model.access.csv', 'data/res_country_state_data.xml', 'data/res_country_municipality_data.xml', 'data/res_country_parish_data.xml', 'views/res_country_parish_views.xml', 'views/res_country_municipality_views.xml', 'views/res_country_city_views.xml', 'views/res_partner_views.xml', 'views/menus.xml'],
    'application': True,
    'description': 'Maestros geográficos completos de Venezuela para la suite LocVe.\n\nDatos oficiales de la organización político-territorial venezolana:\n- 24 Estados con sus códigos oficiales\n- Municipios de todos los estados\n- Parroquias por municipio\n- Ciudades principales\nIntegrado con el módulo de contactos para autocompletar direcciones.\nAutor: Ing. Nerdo Jose Pulido Aguirre',
    'installable': True,
}
