import logging

_logger = logging.getLogger(__name__)

def migrate(cr, version):
    if not version:
        return

    # Pachacutec: v18.0.2.0.10
    # Eliminar registros de res_currency_rate creados para VEF/VES que alteraban la tasa base de la compañía en Odoo
    cr.execute("""
        DELETE FROM res_currency_rate 
        WHERE currency_id IN (SELECT id FROM res_currency WHERE name IN ('VEF', 'VES'));
    """)
    _logger.info("Fase 2 LocVe: Limpieza de registros res_currency_rate sobre VEF/VES completada exitosamente.")
