from odoo.tests import tagged, TransactionCase
from odoo import fields


@tagged("post_install", "-at_install", "retention_reversal")
class TestRetentionReversal(TransactionCase):
    """Tests para el Fix 1: Reverso de retenciones con comprobante negativo.
    Usa TransactionCase directo para evitar dependencia de common.py roto."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.company = cls.env.company

        # Partner (con formato LocVe: prefix_vat + vat numérico)
        cls.partner = cls.env["res.partner"].create({
            "name": "Proveedor Retención Test",
            "prefix_vat": "J",
            "vat": "123456789",
            "supplier_rank": 1,
        })

        # Producto
        cls.product = cls.env["product.product"].create({
            "name": "Servicio Test Retención",
            "list_price": 1000.0,
            "standard_price": 800.0,
            "type": "consu",
            "uom_id": cls.env.ref("uom.product_uom_unit").id,
            "uom_po_id": cls.env.ref("uom.product_uom_unit").id,
        })

        # Diario de compra
        cls.purchase_journal = cls.env["account.journal"].search([
            ("type", "=", "purchase"),
            ("company_id", "=", cls.company.id),
        ], limit=1)

        # Buscar impuesto de compra IVA 16%
        cls.tax_iva_16 = cls.env["account.tax"].search([
            ("type_tax_use", "=", "purchase"),
            ("amount", "=", 16),
            ("company_id", "=", cls.company.id),
        ], limit=1)

    def _create_invoice_with_retention(self, rate=23.57):
        """Helper: crear factura de compra con retención emitida."""
        invoice = self.env["account.move"].create({
            "move_type": "in_invoice",
            "partner_id": self.partner.id,
            "invoice_date": fields.Date.today(),
            "journal_id": self.purchase_journal.id,
            "invoice_line_ids": [(0, 0, {
                "product_id": self.product.id,
                "price_unit": 5000.0,
                "quantity": 1.0,
            })],
        })
        invoice.action_post()

        # Crear retención IVA
        retention = self.env["account.retention"].create({
            "type_retention": "iva",
            "type": "in_invoice",
            "partner_id": self.partner.id,
            "date": fields.Date.today(),
            "date_accounting": fields.Date.today(),
        })

        # Crear línea de retención
        self.env["account.retention.line"].create({
            "name": "Retención IVA 16%",
            "retention_id": retention.id,
            "move_id": invoice.id,
            "aliquot": 16.0,
            "invoice_amount": 5000.0,
            "iva_amount": 800.0,
            "invoice_total": 5800.0,
            "retention_amount": 600.0,
            "foreign_invoice_amount": 5000.0 * rate,
            "foreign_iva_amount": 800.0 * rate,
            "foreign_invoice_total": 5800.0 * rate,
            "foreign_retention_amount": 600.0 * rate,
            "foreign_currency_rate": rate,
            "foreign_currency_inverse_rate": 1.0 / rate,
            "related_percentage_tax_base": 75.0,
        })

        # Marcar como emitida con número (action_post requiere permisos admin)
        retention.write({"state": "emitted", "number": "000-001-00000001"})

        return invoice, retention

    def test_esNegativo_field_exists(self):
        """Verificar que el campo esNegativo existe."""
        retention = self.env["account.retention"].create({
            "type_retention": "iva",
            "type": "in_invoice",
            "partner_id": self.partner.id,
        })
        self.assertFalse(retention.esNegativo)
        self.assertFalse(retention.original_retention_id)

    def test_esNegativo_set_on_creation(self):
        """Verificar que esNegativo se puede crear como True."""
        retention = self.env["account.retention"].create({
            "type_retention": "iva",
            "type": "in_invoice",
            "partner_id": self.partner.id,
            "esNegativo": True,
        })
        self.assertTrue(retention.esNegativo)

    def test_action_create_negative_retention(self):
        """Test que action_create_negative_retention crea correctamente."""
        invoice, retention = self._create_invoice_with_retention()

        # Crear retención negativa
        neg_retention = self.env["account.retention"].action_create_negative_retention(retention)

        # Verificar campos
        self.assertTrue(neg_retention.esNegativo)
        self.assertEqual(neg_retention.original_retention_id, retention)
        self.assertEqual(neg_retention.type_retention, retention.type_retention)
        self.assertEqual(neg_retention.type, retention.type)
        self.assertEqual(neg_retention.partner_id, retention.partner_id)
        self.assertEqual(neg_retention.company_id, retention.company_id)
        self.assertEqual(neg_retention.state, "draft")

        # Verificar que tiene las mismas líneas con montos invertidos
        self.assertEqual(len(neg_retention.retention_line_ids), len(retention.retention_line_ids))
        for neg_line, orig_line in zip(neg_retention.retention_line_ids, retention.retention_line_ids):
            self.assertEqual(neg_line.aliquot, orig_line.aliquot)
            self.assertEqual(neg_line.invoice_amount, orig_line.invoice_amount)
            self.assertEqual(neg_line.retention_amount, -orig_line.retention_amount)
            self.assertEqual(neg_line.move_id, orig_line.move_id)

    def test_reverse_invoice_creates_negative_retention(self):
        """Test completo: factura con retención → reversar → NC + retención negativa."""
        invoice, retention = self._create_invoice_with_retention()

        # Verificar estado inicial
        self.assertEqual(retention.state, "emitted")
        self.assertFalse(retention.esNegativo)

        # Revertir la factura
        reversed_moves = invoice._reverse_moves(default_values_list=[{
            "invoice_date": fields.Date.today(),
            "ref": "Reversión de prueba",
        }])

        # Verificar que se creó la NC
        self.assertTrue(reversed_moves)
        self.assertEqual(reversed_moves[0].move_type, "in_refund")

        # Verificar que se creó la retención negativa
        negative_retentions = self.env["account.retention"].search([
            ("esNegativo", "=", True),
            ("original_retention_id", "=", retention.id),
        ])
        self.assertTrue(negative_retentions, "Debería existir una retención negativa")
        neg_ret = negative_retentions[0]
        self.assertEqual(neg_ret.type_retention, "iva")
        self.assertEqual(neg_ret.partner_id, self.partner)
        self.assertEqual(neg_ret.state, "draft")

    def test_no_duplicate_negative_retention(self):
        """No crear retención negativa duplicada si ya existe una."""
        invoice, retention = self._create_invoice_with_retention()

        # Crear retención negativa manualmente primero
        neg1 = self.env["account.retention"].action_create_negative_retention(retention)
        self.assertTrue(neg1.esNegativo)

        # Revertir la factura
        invoice._reverse_moves(default_values_list=[{
            "invoice_date": fields.Date.today(),
            "ref": "Reversión de prueba 2",
        }])

        # Verificar que NO se creó segunda retención negativa
        negative_count = self.env["account.retention"].search_count([
            ("esNegativo", "=", True),
            ("original_retention_id", "=", retention.id),
        ])
        self.assertEqual(negative_count, 1, "Solo debería existir 1 retención negativa")

    def test_negative_retention_preserves_original_data(self):
        """Verificar que la retención negativa conserva todos los datos de la original."""
        invoice, retention = self._create_invoice_with_retention(rate=36.5)

        neg = self.env["account.retention"].action_create_negative_retention(retention)

        # Verificar datos de la retención original
        orig_data = {
            "type_retention": retention.type_retention,
            "type": retention.type,
            "partner_id": retention.partner_id.id,
            "company_id": retention.company_id.id,
        }
        neg_data = {
            "type_retention": neg.type_retention,
            "type": neg.type,
            "partner_id": neg.partner_id.id,
            "company_id": neg.company_id.id,
        }
        self.assertEqual(orig_data, neg_data)

        # Verificar líneas
        self.assertEqual(len(neg.retention_line_ids), 1)
        neg_line = neg.retention_line_ids[0]
        self.assertEqual(neg_line.aliquot, 16.0)
        self.assertEqual(neg_line.invoice_amount, 5000.0)
        self.assertEqual(neg_line.retention_amount, -600.0)
        self.assertEqual(neg_line.foreign_currency_rate, 36.5)

    def test_negative_retention_name_references_original(self):
        """El nombre de la retención negativa debe referenciar la original."""
        invoice, retention = self._create_invoice_with_retention()

        neg = self.env["account.retention"].action_create_negative_retention(retention)
        self.assertIn(retention.number or str(retention.id), neg.name)
