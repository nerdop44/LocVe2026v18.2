from odoo import models, api

class ResCurrency(models.Model):
    _inherit = 'res.currency'

    @api.model
    def _load_pos_data(self, data):
        # Pachacutec: v18.0.1.0.94 - SPECIFIC SHIELD
        # Mantenemos sudo() en la carga inicial para garantizar visibilidad multi-empresa.
        return super(ResCurrency, self.sudo())._load_pos_data(data)
