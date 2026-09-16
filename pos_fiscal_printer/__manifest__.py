# -*- coding: utf-8 -*-
{
    'name': '[LocVe] POS Impresora Fiscal HKA',
    'version': '18.0.2.0.0',
    'category': 'LocVe [Localization]',
    'summary': 'Integración con impresoras fiscales HKA para el POS LocVe (OPCIONAL).',
    'author': 'Ing. Nerdo Jose Pulido Aguirre',
    'website': 'https://github.com/nerdop44',
    'description': 'Integración con impresoras fiscales HKA para el POS LocVe (OPCIONAL).\nPermite emitir facturas fiscales desde el Punto de Venta Odoo a través\nde impresoras fiscales HKA certificadas por el SENIAT:\n- Comunicación TCP/IP con la impresora fiscal\n- Facturas, notas de crédito y reportes Z\n- Soporte de IGTF en el documento fiscal\nSolo instalar en establecimientos con impresora fiscal HKA habilitada.\nAutor: Ing. Nerdo Jose Pulido Aguirre',
    'depends': ['point_of_sale', 'pos_igtf_tax', 'l10n_ve_binaural'],
    'data': ['security/ir.model.access.csv', 'views/inherited_views.xml', 'views/x_pos_fiscal_printer_views.xml', 'views/pos_report_z.xml'],
    'assets': {'point_of_sale._assets_pos': ['pos_fiscal_printer/static/src/scss/**/*', 'pos_fiscal_printer/static/src/app/utils/data_helper.js', 'pos_fiscal_printer/static/src/app/utils/printing_mixin.js', 'pos_fiscal_printer/static/src/app/popup/nota_credito_popup.xml', 'pos_fiscal_printer/static/src/app/popup/nota_credito_popup.js', 'pos_fiscal_printer/static/src/app/popup/close_pos_popup_patch.xml', 'pos_fiscal_printer/static/src/app/popup/close_pos_popup_patch.js', 'pos_fiscal_printer/static/src/app/screens/receipt_screen/receipt_screen_patch.xml', 'pos_fiscal_printer/static/src/app/screens/receipt_screen/receipt_screen_patch.js', 'pos_fiscal_printer/static/lib/js/**/*', 'pos_fiscal_printer/static/lib/css/**/*']},
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
}
