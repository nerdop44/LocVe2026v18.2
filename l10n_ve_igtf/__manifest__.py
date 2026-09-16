# -*- coding: utf-8 -*-
{
    'name': '[LocVe] IGTF (Impuesto a Grandes Transacciones Financieras)',
    'summary': 'Módulo IGTF para la Localización Venezolana LocVe — Odoo 18.',
    'license': 'AGPL-3',
    'description': 'Módulo IGTF para la Localización Venezolana LocVe — Odoo 18.\n\nImplementa el Impuesto a las Grandes Transacciones Financieras (IGTF)\nsegún la Ley venezolana vigente:\n- Alícuota del 3% sobre pagos en divisas o criptomonedas\n- Cálculo automático al registrar pagos en moneda extranjera\n- Visualización en el comprobante de pago y la factura\n- Configuración de diario de IGTF y cuentas contables\n- Integración con el módulo POS para punto de venta\nCumplimiento: Decreto-Ley IGTF y providencias del SENIAT.\nAutor: Ing. Nerdo Jose Pulido Aguirre',
    'author': 'Ing. Nerdo Jose Pulido Aguirre',
    'website': 'https://github.com/nerdop44',
    'category': 'Accounting/Accounting',
    'version': '18.0.2.0.6',
    'depends': ['base', 'l10n_ve_rate', 'l10n_ve_tax', 'l10n_ve_invoice', 'l10n_ve_tax_payer', 'l10n_ve_base', 'l10n_ve_payment_extension'],
    'data': ['security/ir.model.access.csv', 'views/account_journal.xml', 'views/account_payment.xml', 'views/res_config_settings.xml', 'views/res_company.xml', 'report/invoice_free_form.xml', 'report/report_igtf_consolidated.xml', 'wizard/account_payment_register.xml', 'wizard/igtf_report_wizard_views.xml'],
    'images': ['static/description/icon.png'],
    'assets': {'web.assets_backend': ['l10n_ve_igtf/static/src/components/**/*']},
    'pre_init_hook': 'pre_init_hook',
    'application': True,
    'installable': True,
}
