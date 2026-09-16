import logging

_logger = logging.getLogger(__name__)

def migrate(cr, version):
    if not version:
        return

    # Pachacutec: v18.0.2.0.7
    # Espejar todos los registros de res_currency_rate de USD a VEF y VES
    # para que la pestaña "Tasas" en Monedas / VEF y Monedas / VES muestre el historial completo.
    cr.execute("""
        INSERT INTO res_currency_rate (currency_id, company_id, name, rate, create_uid, create_date, write_uid, write_date)
        SELECT vef.id, r.company_id, r.name, r.rate, r.create_uid, NOW(), r.write_uid, NOW()
        FROM res_currency_rate r
        JOIN res_currency usd ON usd.id = r.currency_id AND usd.name = 'USD'
        CROSS JOIN res_currency vef WHERE vef.name IN ('VEF', 'VES')
        ON CONFLICT (currency_id, company_id, name) DO UPDATE SET rate = EXCLUDED.rate;
    """)
    _logger.info("Fase 2 LocVe: Espejamiento masivo de tasas de USD a VEF/VES completado.")
