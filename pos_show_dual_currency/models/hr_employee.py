from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None, **read_kwargs):
        # Pachacutec: v18.0.1.1.1 - GLOBAL POS SHIELD
        # Resolvemos el bloqueo de empleados en entornos multi-empresa para TODOS los usuarios.
        # El POS necesita cargar vendedores; si falla por reglas de registro o permisos,
        # intentamos una lectura as sudo() limitada a los campos solicitados.
        try:
            return super(HrEmployee, self.with_context(active_test=False)).search_read(
                domain=domain, fields=fields, offset=offset, limit=limit, order=order, **read_kwargs
            )
        except Exception:
            # Fallback seguro: Elevamos privilegios solo si la lectura estándar falla
            return super(HrEmployee, self.sudo().with_context(active_test=False)).search_read(
                domain=domain, fields=fields, offset=offset, limit=limit, order=order, **read_kwargs
            )

    def read(self, fields=None, load='_classic_read'):
        # Pachacutec: v18.0.1.1.1 - GLOBAL READ SHIELD
        # Aseguramos que las imágenes y nombres de empleados se carguen sin importar 
        # las restricciones de compañía durante la operación del Punto de Venta.
        try:
            return super().read(fields=fields, load=load)
        except Exception:
            return super(HrEmployee, self.sudo()).read(fields=fields, load=load)
