# -*- coding: utf-8 -*-
{
    'name': '[LocVe] Facturación Venezuela',
    'summary': 'Módulo de facturación venezolana conforme al SENIAT para la suite LocVe.',
    'version': '18.0.2.0.33',

















    'license': 'LGPL-3',
    'author': 'Ing. Nerdo Jose Pulido Aguirre',
    'website': 'https://github.com/nerdop44',
    'category': 'Accounting/Localizations/Account Chart',
    'depends': ['l10n_ve_base', 'l10n_ve_contact', 'l10n_ve_tax', 'stock'],
    'data': [
        'security/l10n_ve_invoice_groups.xml',
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'data/account_data.xml',
        'data/stock_picking_data.xml',
        'data/invoice_free_form_paperformat.xml',
        'data/invoice_sale_note_paperformat.xml',
        'report/report_invoice_free_form.xml',
        'report/report_invoice_free_form_dual.xml',
        'report/report_invoice_sale_note.xml',
        'report/report_invoice.xml',
        'report/report_delivery_guide.xml',
        'views/account_journal_views.xml',
        'views/account_move.xml',
        'views/res_config_settings.xml',
        'views/menu.xml',
        'wizard/accounting_reports_views.xml',
        'wizard/l10n_ve_delivery_guide_wizard_views.xml',
        'wizard/l10n_ve_void_control_wizard_views.xml',
    ],
    'images': ['static/description/icon.png'],
    'application': True,
    'description': 'Módulo de facturación venezolana conforme al SENIAT para la suite LocVe.\n\nAdapta el módulo de facturación de Odoo 18 a la normativa venezolana:\n- Número de control de factura (SENIAT)\n- Fecha y número de control para facturas de proveedor\n- Reporte de factura en formato libre (sin preimpreso)\n- Reporte de factura en doble moneda (Bs. / Divisa)\n- Nota de entrega con formato venezolano\n- Libro de compras y ventas (base)\nAutor: Ing. Nerdo Jose Pulido Aguirre',
    'installable': True,
}
