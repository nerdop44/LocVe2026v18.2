# -*- coding: utf-8 -*-
{
    'name': '[LocVe] Contactos Venezuela',
    'summary': 'Módulo de contactos venezolanos para la suite de Localización LocVe.',
    'license': 'LGPL-3',
    'author': 'Ing. Nerdo Jose Pulido Aguirre',
    'website': 'https://github.com/nerdop44',
    'category': 'LocVe [Localization]',
    'version': '18.0.2.0.0',
    'depends': ['base', 'contacts', 'l10n_ve_rate'],
    'data': ['views/res_partner.xml', 'views/res_config_settings.xml'],
    'images': ['static/description/icon.png'],
    'application': True,
    'installable': True,
    'description': 'Módulo de contactos venezolanos para la suite de Localización LocVe.\n\nExtiende el módulo de contactos con campos y validaciones propias de Venezuela:\n- Tipo y número de RIF/Cédula con prefijo (V-, E-, J-, G-, P-)\n- Validación de formato según normas del SENIAT\n- Consulta opcional y configurable al portal del CNE para personas naturales\n- Clasificación de persona natural / jurídica\n- Integración con los módulos de facturación y retenciones LocVe\nAutor: Ing. Nerdo Jose Pulido Aguirre',
}
