# -*- coding: utf-8 -*-
{
    'name': '[LocVe] Contribuyente Técnico SENIAT',
    'summary': 'Clasificación de contribuyentes según el SENIAT para la suite LocVe.',
    'license': 'LGPL-3',
    'description': 'Clasificación de contribuyentes según el SENIAT para la suite LocVe.\n\nGestiona la condición fiscal del contribuyente venezolano:\n- Contribuyente Ordinario / Especial / No Contribuyente\n- Agente de retención de IVA designado por el SENIAT\n- Clasificación requerida para el cálculo correcto de retenciones de IVA\n- Información visible en la ficha del contacto\nAutor: Ing. Nerdo Jose Pulido Aguirre',
    'author': 'Ing. Nerdo Jose Pulido Aguirre',
    'website': 'https://github.com/nerdop44',
    'category': 'Accounting/Accounting',
    'version': '18.0.2.0.0',
    'depends': ['base', 'l10n_ve_rate', 'l10n_ve_tax'],
    'data': ['views/res_partner.xml'],
    'images': ['static/description/icon.png'],
    'application': True,
    'installable': True,
}
