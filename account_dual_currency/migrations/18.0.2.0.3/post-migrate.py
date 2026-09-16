import logging

def migrate(cr, version):
    if not version:
        return

    # Pachacutec: v18.0.2.0.3
    # Reset product template & product product master prices to USD ($10.00)
    # where previous migrations saved list_price or list_price_usd in Bolívares (>= 1000).
    cr.execute("""
        UPDATE product_template 
        SET list_price = 10.0, list_price_usd = 10.0 
        WHERE list_price >= 1000 OR list_price_usd >= 1000;
    """)

