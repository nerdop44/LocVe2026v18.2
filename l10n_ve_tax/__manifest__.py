# -*- coding: utf-8 -*-
{
    'name': '[LocVe] Impuestos Venezuela (IVA/SENIAT)',
    'summary': 'Módulo de impuestos venezolanos conforme al SENIAT para la suite LocVe.',
    'license': 'LGPL-3',
    'author': 'Ing. Nerdo Jose Pulido Aguirre',
    'website': 'https://github.com/nerdop44',
    'category': 'Accounting/Localizations/Account Chart',
    'version': '18.0.2.0.23',


















    'depends': ['base', 'account', 'l10n_ve_rate'],
    'data': ['views/res_config_settings.xml', 'views/account_move.xml'],
    'images': ['static/description/icon.png'],
    'application': True,
    'assets': {'web.assets_backend': ['l10n_ve_tax/static/src/components/**/*']},
    'description': 'Módulo de impuestos venezolanos conforme al SENIAT para la suite LocVe.\n\nImplementa el tratamiento fiscal venezolano en Odoo 18:\n- IVA estándar (16%) y alícuota reducida (8%) según normativa SENIAT\n- Manejo de exenciones y exoneraciones de IVA\n- Visualización de totales de impuesto en moneda base y divisa (doble moneda)\n- Componente web para mostrar totales fiscales en facturas\n- Base para los módulos de IGTF y retenciones LocVe\nAutor: Ing. Nerdo Jose Pulido Aguirre',
    'installable': True,
}
