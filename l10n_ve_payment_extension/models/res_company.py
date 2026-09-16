import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    tax_authorities_logo = fields.Image(max_width=128, max_height=128)
    tax_authorities_name = fields.Char()
    economic_activity_number = fields.Char()

    iva_supplier_retention_journal_id = fields.Many2one(
        "account.journal",
        string="Journal for Supplier I.V.A Retentions",
    )
    iva_customer_retention_journal_id = fields.Many2one(
        "account.journal",
        string="Journal for Customer I.V.A Retentions",
    )

    islr_supplier_retention_journal_id = fields.Many2one(
        "account.journal",
        string="Journal for Supplier I.S.L.R Retentions",
    )
    islr_customer_retention_journal_id = fields.Many2one(
        "account.journal",
        string="Journal for Customer I.S.L.R Retentions",
    )

    municipal_supplier_retention_journal_id = fields.Many2one(
        "account.journal",
        string="Journal for Supplier Municipal Retentions",
    )
    municipal_customer_retention_journal_id = fields.Many2one(
        "account.journal",
        string="Journal for Customer Municipal Retentions",
    )

    condition_withholding_id = fields.Many2one(
        "account.withholding.type",
        string="The condition of this taxpayer requires the withholding of",
    )
    code_visible=fields.Boolean(string="See payment concept code")

    signature_stamp_signature = fields.Binary(string="Firma de la Empresa (Rúbrica)")
    signature_stamp_stamp = fields.Binary(string="Sello de la Empresa (Húmedo)")

    retention_sequence_annual_reset = fields.Boolean(
        string="Reiniciar correlativos de retención anualmente",
        default=False,
        help="Si está activo, los correlativos de comprobantes de retención (IVA, ISLR, Municipal) "
             "se reiniciarán a 00001 al inicio de cada año fiscal. Si está inactivo, la numeración "
             "será continua (comportamiento actual).",
    )
    islr_subtract_once_per_month = fields.Boolean(
        string="Aplicar sustraendo ISLR una sola vez por RIF/mes",
        default=False,
        help="Si está activo, el sustraendo del Art. 9 del Decreto 1808 se aplicará UNA SOLA VEZ "
             "por cada proveedor (RIF) dentro del mismo mes calendario. Las retenciones subsiguientes "
             "al mismo proveedor en el mismo mes NO descontarán el sustraendo nuevamente.\n\n"
             "Si está inactivo, el sustraendo se descontará en cada línea de retención "
             "individualmente (comportamiento actual).",
    )

    def _register_hook(self):
        super()._register_hook()
        try:
            self.env.cr.execute("""
                ALTER TABLE res_company 
                ADD COLUMN IF NOT EXISTS retention_sequence_annual_reset BOOLEAN DEFAULT FALSE,
                ADD COLUMN IF NOT EXISTS islr_subtract_once_per_month BOOLEAN DEFAULT FALSE;
            """)
        except Exception as e:
            _logger.warning("Error asegurando columnas res_company en l10n_ve_payment_extension: %s", e)

