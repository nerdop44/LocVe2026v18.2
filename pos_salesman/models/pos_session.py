from odoo import models, api, fields

class PosConfig(models.Model):
    _inherit = 'pos.config'

    @api.model
    def _load_pos_data(self, data):
        # Pachacutec: v18 - Inyectar salesman_ids sin filtrar otros campos
        res = super()._load_pos_data(data)
        config_id = self.env.context.get('pos_config_id')
        if not config_id and data.get('pos.session'):
            try:
                config_id = data['pos.session']['data'][0]['config_id']
            except (KeyError, IndexError):
                pass
        
        if config_id:
            config = self.browse(config_id)
            if isinstance(res, dict) and 'data' in res and len(res['data']) > 0:
                res['data'][0]['salesman_ids'] = config.salesman_ids.ids
        return res

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    @api.model
    def _load_pos_data_fields(self, config_id):
        # Pachacutec: v18 - Usar el método estándar para evitar errores de getIndexMaps
        res = super()._load_pos_data_fields(config_id)
        # No añadimos 'name' porque ya está en el core de pos_hr
        return res

    # Pachacutec: v205 - ELIMINADO filtro de dominio restrictivo.
    # El filtrado de vendedores se debe manejar solo en el frontend (BtnSalesMan.js)
    # para no bloquear la carga de cajeros/managers legítimos en Odoo 18.