# -*- coding: utf-8 -*-
# Remake ING. Nerdo José Pulido Aguirre - Localización Venezolana (LocVe)

from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"
    
    username_tfhka = fields.Char(related="company_id.username_tfhka", readonly=False)
    password_tfhka = fields.Char(related="company_id.password_tfhka", readonly=False)
    url_tfhka = fields.Char(related="company_id.url_tfhka", readonly=False)
    token_auth_tfhka = fields.Char(related="company_id.token_auth_tfhka", readonly=True)
    invoice_digital_tfhka = fields.Boolean(related="company_id.invoice_digital_tfhka", readonly=False)
    sequence_validation_tfhka = fields.Boolean(related="company_id.sequence_validation_tfhka", readonly=False)
    ocultar_forma_libre_digital = fields.Boolean(related="company_id.ocultar_forma_libre_digital", readonly=False)
    
    def action_generate_token_tfhka(self):
        self.company_id.generate_token_tfhka()
