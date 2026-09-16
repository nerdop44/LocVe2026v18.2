# -*- coding: utf-8 -*-
{
    "name": "[LocVe] Facturación Digital TFHKA",

    "summary": "Integración con API REST de The Factory HKA (TFHKA) para Facturación Digital en Venezuela",
    "description": """
Localización Venezolana - Módulo de Facturación Digital TFHKA (LocVe)
====================================================================
Permite la emisión de Facturas Digitales, Notas de Crédito, Notas de Débito,
Comprobantes de Retención de IVA/ISLR y Guías de Despacho Digitales a través
de la infraestructura en la nube de The Factory HKA (TFHKA).

Adaptado para Odoo 18 con arquitectura unificada LocVe.
    """,
    "license": "LGPL-3",
    "author": "Remake ING. Nerdo José Pulido Aguirre",
    "website": "https://github.com/nerdop44/LocVe",
    "category": "Accounting/Localizations",
    "version": "18.0.2.0.23",

    "depends": [
        "base",
        "account",
        "account_debit_note",
        "l10n_ve_tax",
        "l10n_ve_igtf",
        "l10n_ve_invoice",
        "l10n_ve_payment_extension",
        "stock",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/res_config_settings.xml",
        "views/account_move_view.xml",
        "views/account_retention_iva.xml",
        "views/account_retention_islr.xml",
        "views/stock_picking.xml",
        "wizard/account_retention_alert_views.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
