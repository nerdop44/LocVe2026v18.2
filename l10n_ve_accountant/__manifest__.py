# -*- coding: utf-8 -*-
{
    'name': '[LocVe] Contabilidad Venezuela',
    'summary': 'Módulo central de contabilidad venezolana para la suite LocVe.',
    'license': 'LGPL-3',
    'author': 'Ing. Nerdo Jose Pulido Aguirre',
    'website': 'https://github.com/nerdop44',
    'category': 'Accounting/Localizations/Account Chart',
    'version': '18.0.2.0.4',

    'depends': ['base', 'web', 'account', 'l10n_ve_tax', 'l10n_ve_contact', 'l10n_ve_rate'],
    'data': ['security/ir.model.access.csv', 'data/account_data.xml', 'data/ir_actions_server.xml', 'data/paperformats.xml', 'views/account_invoice_report.xml', 'views/account_move_line.xml', 'views/account_payment.xml', 'views/ir_property.xml', 'report/account_invoice_details.xml', 'report/all_payment_report.xml', 'report/account_report_templates.xml', 'report/account_report_document.xml', 'report/account_template_report_views.xml', 'wizard/account_payment_register.xml', 'wizard/invoices_details.xml', 'wizard/payment_report.xml'],
    'images': ['static/description/icon.png'],
    'application': True,
    'description': 'Módulo central de contabilidad venezolana para la suite LocVe.\n\nExtiende la contabilidad de Odoo 18 con requerimientos venezolanos:\n- Asientos contables en doble moneda (Bs. y divisa)\n- Informe de pagos y cobros por banco\n- Conciliación bancaria con campos venezolanos\n- Extractos de cuenta en formato SENIAT\n- Reportes contables: auxiliar de cuentas, balance de comprobación\n- Plan de cuentas venezolano (base SENIAT/IASB)\nAutor: Ing. Nerdo Jose Pulido Aguirre',
    'installable': True,
}
