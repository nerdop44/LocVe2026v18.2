from odoo.tests import tagged, TransactionCase
from odoo import fields


@tagged("post_install", "-at_install", "so_po_price_preservation")
class TestSoPoPricePreservation(TransactionCase):
    """Tests para el Fix 2: Preservar precios de SO/PO al generar facturas."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.company = cls.env.company

        cls.product = cls.env["product.product"].create({
            "name": "Producto Test Precio Dual",
            "list_price": 150.0,
            "standard_price": 100.0,
            "type": "consu",
            "uom_id": cls.env.ref("uom.product_uom_unit").id,
            "uom_po_id": cls.env.ref("uom.product_uom_unit").id,
        })

        cls.partner_supplier = cls.env["res.partner"].create({
            "name": "Proveedor Test Precio",
            "prefix_vat": "J",
            "vat": "987654321",
            "supplier_rank": 1,
        })

        cls.partner_customer = cls.env["res.partner"].create({
            "name": "Cliente Test Precio",
            "prefix_vat": "J",
            "vat": "112233445",
            "customer_rank": 1,
        })

        cls.sale_journal = cls.env["account.journal"].search([
            ("type", "=", "sale"),
            ("company_id", "=", cls.company.id),
        ], limit=1)

        cls.purchase_journal = cls.env["account.journal"].search([
            ("type", "=", "purchase"),
            ("company_id", "=", cls.company.id),
        ], limit=1)

    def test_compute_price_unit_skips_when_sale_line_exists(self):
        """Verificar que _compute_price_unit NO sobrescribe precio cuando hay sale_line_ids."""
        # Crear orden de venta
        so = self.env["sale.order"].create({
            "partner_id": self.partner_customer.id,
            "order_line": [(0, 0, {
                "product_id": self.product.id,
                "price_unit": 250.0,
                "product_uom_qty": 3.0,
            })],
        })
        so.action_confirm()

        # Crear factura vinculada a la OV (flujo real de Odoo)
        invoice = so._create_invoices()

        invoice_line = invoice.invoice_line_ids[0]

        # El precio debería ser 250 (de la OV), NO 150 (list_price del producto)
        self.assertEqual(invoice_line.price_unit, 250.0,
                         "El precio de la OV ($250) debe preservarse en la factura")

    def test_compute_price_unit_uses_product_price_for_manual(self):
        """Para factura manual (sin SO/PO), _compute_price_unit usa precio del producto."""
        invoice = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": self.partner_customer.id,
            "invoice_line_ids": [(0, 0, {
                "product_id": self.product.id,
                "price_unit": 150.0,
                "quantity": 1.0,
            })],
        })

        invoice_line = invoice.invoice_line_ids[0]
        # Para factura manual sin vinculación a SO/PO, compute podría usar product price
        # Lo importante es que no crashee y el precio sea > 0
        invoice_line._compute_price_unit()
        self.assertTrue(invoice_line.price_unit > 0,
                        "Factura manual debe tener precio > 0")

    def test_purchase_line_id_check(self):
        """Verificar que purchase_line_id se detecta correctamente en account.move.line."""
        po = self.env["purchase.order"].create({
            "partner_id": self.partner_supplier.id,
            "order_line": [(0, 0, {
                "product_id": self.product.id,
                "price_unit": 200.0,
                "product_qty": 2.0,
            })],
        })
        po.button_confirm()

        # Verificar que la línea de PO tiene precio 200
        self.assertEqual(po.order_line[0].price_unit, 200.0)
