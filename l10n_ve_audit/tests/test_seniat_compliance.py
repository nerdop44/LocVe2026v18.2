# -*- coding: utf-8 -*-
from odoo import Command, fields
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import ValidationError, UserError

@tagged("post_install", "-at_install", "seniat")
class TestSeniatCompliance(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref="l10n_ve.ve_chart_template_amd"):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.group_auditor = cls.env.ref('l10n_ve_audit.group_fiscal_auditor')
        # Crear un usuario de auditoría
        cls.auditor_user = cls.env['res.users'].create({
            'name': 'Auditor SENIAT',
            'login': 'auditor_seniat',
            'email': 'auditor@seniat.gob.ve',
            'groups_id': [Command.set([cls.env.ref('base.group_user').id, cls.group_auditor.id])],
        })

    def test_price_unit_positive(self):
        """Probar que el precio unitario en las líneas de factura de productos reales deba ser positivo."""
        with self.assertRaises(ValidationError):
            self.env['account.move'].create({
                'partner_id': self.partner_a.id,
                'move_type': 'out_invoice',
                'invoice_date': fields.Date.today(),
                'invoice_line_ids': [
                    Command.create({
                        'product_id': self.product_a.id,
                        'quantity': 1,
                        'price_unit': 0.0,
                    })
                ]
            })

    def test_single_tax_constraint(self):
        """Probar que solo se permita un impuesto por línea de producto."""
        tax1 = self.env['account.tax'].create({
            'name': 'IVA 16%',
            'amount': 16,
            'type_tax_use': 'sale',
        })
        tax2 = self.env['account.tax'].create({
            'name': 'IGTF 3%',
            'amount': 3,
            'type_tax_use': 'sale',
        })
        with self.assertRaises(ValidationError):
            self.env['account.move'].create({
                'partner_id': self.partner_a.id,
                'move_type': 'out_invoice',
                'invoice_date': fields.Date.today(),
                'invoice_line_ids': [
                    Command.create({
                        'product_id': self.product_a.id,
                        'quantity': 1,
                        'price_unit': 100.0,
                        'tax_ids': [Command.set([tax1.id, tax2.id])],
                    })
                ]
            })

    def test_control_number_formatting(self):
        """Probar que el número de control sea formateado automáticamente a 00-XXXXXXXX."""
        move = self.env['account.move'].create({
            'partner_id': self.partner_a.id,
            'move_type': 'out_invoice',
            'invoice_date': fields.Date.today(),
            'correlative': '12345',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'quantity': 1,
                    'price_unit': 10.0,
                })
            ]
        })
        self.assertEqual(move.correlative, '00-00012345')

    def test_auditor_read_only_restriction(self):
        """Probar que un auditor fiscal no pueda crear, modificar ni eliminar documentos fiscales."""
        move = self.env['account.move'].create({
            'partner_id': self.partner_a.id,
            'move_type': 'out_invoice',
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'quantity': 1,
                    'price_unit': 10.0,
                })
            ]
        })

        # Auditor intenta modificar factura
        with self.assertRaises(UserError):
            move.with_user(self.auditor_user).write({'ref': 'Intento auditor'})

        # Auditor intenta eliminar factura
        with self.assertRaises(UserError):
            move.with_user(self.auditor_user).unlink()

        # Auditor intenta crear factura
        with self.assertRaises(UserError):
            self.env['account.move'].with_user(self.auditor_user).create({
                'partner_id': self.partner_a.id,
                'move_type': 'out_invoice',
                'invoice_date': fields.Date.today(),
                'invoice_line_ids': [
                    Command.create({
                        'product_id': self.product_a.id,
                        'quantity': 1,
                        'price_unit': 10.0,
                    })
                ]
            })

    def test_audit_log_immutability(self):
        """Probar que los registros de auditoría fiscal sean inmutables (no modificables ni eliminables)."""
        log = self.env['l10n_ve.audit.log'].sudo().create({
            'datetime': fields.Datetime.now(),
            'action': 'create',
            'res_model': 'account.move',
            'res_id': 1,
            'record_name': 'Factura Test',
            'details': 'Detalles de creación',
        })
        with self.assertRaises(UserError):
            log.write({'details': 'Editado'})
        with self.assertRaises(UserError):
            log.unlink()
