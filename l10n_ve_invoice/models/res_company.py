import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    max_product_invoice = fields.Integer(default=23)
    group_sales_invoicing_series = fields.Boolean()
    show_total_on_usd_invoice = fields.Boolean(default=True)
    show_tag_on_usd_invoice = fields.Boolean(default=True)
    activate_custom_margin = fields.Boolean(default=False)
    forma_libre_top_margin = fields.Float(string="Margen Superior Forma Libre (cm)", default=0.0)
    
    invoice_font_family = fields.Selection([
        ('Courier', 'Courier'),
        ('Arial', 'Arial'),
        ('Times New Roman', 'Times New Roman'),
        ('Helvetica', 'Helvetica'),
        ('sans-serif', 'Sans-Serif')
    ], string="Fuente de la Factura", default='sans-serif')
    invoice_font_size = fields.Integer(string="Tamaño de Fuente de la Factura (px)", default=12)
    invoice_line_height = fields.Float(string="Interlineado de la Factura", default=1.0)

