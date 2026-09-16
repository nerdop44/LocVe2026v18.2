# -*- coding: utf-8 -*-
{
    'name': '[LocVe] Doble Moneda Venezuela',
    'version': '18.0.2.0.29',


















    'category': 'LocVe [Localization]',
    'license': 'Other proprietary',
    'summary': 'Módulo de doble moneda para la Localización Venezolana LocVe.',
    'author': 'Ing. Nerdo Jose Pulido Aguirre',
    'website': 'https://github.com/nerdop44',
    'description': 'Módulo de doble moneda para la Localización Venezolana LocVe.\n\nImplementa el sistema de doble moneda requerido por la normativa cambiaria venezolana:\n- Tasa de cambio integrada con la tasa oficial del BCV\n- Todos los movimientos contables en moneda local y divisa simultáneamente\n- Precios de productos en moneda local y divisa con cálculo automático\n- Costo de inventario en ambas monedas\n- Conciliación de saldos en doble moneda\n- Promedio ponderado BCV del día para cálculos fiscales\n- Scripts de migración incluidos para actualización desde versiones anteriores\nCumplimiento: Marco legal cambiario venezolano y SENIAT.\nAutor: Ing. Nerdo Jose Pulido Aguirre',
    'depends': ['base', 'l10n_ve_base', 'l10n_ve_rate', 'l10n_ve_tax', 'account', 'web', 'stock_account', 'analytic', 'stock_landed_costs', 'mail', 'product', 'sale', 'purchase'],
    'data': ['security/ir.model.access.csv', 'security/res_groups.xml', 'views/res_currency.xml', 'views/res_config_settings.xml', 'views/account_move_view.xml', 'views/account_move_line.xml', 'wizard/account_payment_register.xml', 'views/account_payment.xml', 'views/product_template.xml', 'views/stock_landed_cost.xml', 'views/stock_valuation_layer.xml', 'data/decimal_precision.xml', 'data/cron.xml', 'data/cron_bcv_retry.xml', 'data/channel.xml', 'views/effective_date_change.xml', 'views/product_template_attribute_value.xml', 'wizard/generar_retencion_igtf_wizard.xml', 'views/account_analytic_account.xml', 'views/account_analytic_line.xml', 'views/product_pricelist.xml', 'views/sale_order_view.xml', 'views/purchase_order_view.xml', 'views/ir_cron_views.xml'],
    'assets': {'web.assets_backend': ['account_dual_currency/static/src/xml/trm.xml', 'account_dual_currency/static/src/js/trm.js']},
    'images': ['static/description/thumbnail.png'],
    'price': 2990,
    'currency': 'USD',
    'installable': True,
    'application': False,
}
