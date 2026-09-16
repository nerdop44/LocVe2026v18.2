from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class RevaluationWizard(models.TransientModel):
    _name = 'l10n_ve.revaluation.wizard'
    _description = 'Wizard de Revaluación Cambiaria al Cierre Fiscal'

    closing_id = fields.Many2one(
        'account.fiscalyear.closing',
        string="Cierre Fiscal",
        required=True,
    )
    closing_date = fields.Date(
        string="Fecha de Cierre",
        required=True,
    )
    closing_rate = fields.Float(
        string="Tasa BCV al Cierre (Bs/USD)",
        digits=(16, 6),
        help="Tasa oficial del BCV vigente al último día del ejercicio fiscal.",
    )
    use_closing_rate = fields.Boolean(
        string="Aplicar tasa de cierre BCV a cuentas en divisas",
        default=False,
        help="Si se activa, las cuentas de balance con saldos en moneda extranjera "
             "(Bancos, CxC, CxP) serán revaluadas a la tasa de cierre BCV, generando "
             "asientos de ganancia/pérdida cambiaria no realizada.\n\n"
             "Si se desactiva, se mantendrán las tasas históricas de cada operación.",
    )
    preview_line_ids = fields.One2many(
        'l10n_ve.revaluation.preview.line',
        'wizard_id',
        string="Vista previa de revaluación",
    )
    state = fields.Selection([
        ('draft', 'Configuración'),
        ('preview', 'Vista Previa'),
        ('done', 'Asientos Generados'),
    ], default='draft')

    @api.onchange('closing_date')
    def _onchange_closing_date(self):
        """Intentar obtener la tasa BCV de la fecha de cierre automáticamente."""
        if self.closing_date:
            rate = self.env['res.currency.rate'].search([
                ('currency_id.name', '=', 'USD'),
                ('name', '<=', self.closing_date),
            ], order='name desc', limit=1)
            if rate:
                # rate.rate es 1/tasa_bcv, invertimos
                self.closing_rate = 1.0 / rate.rate if rate.rate else 0.0

    def action_preview(self):
        """Calcula la vista previa de revaluación sin generar asientos."""
        self.ensure_one()
        if not self.closing_rate or self.closing_rate <= 0:
            raise UserError(_("Debe ingresar una tasa de cierre BCV válida."))

        # Limpiar preview anterior
        self.preview_line_ids.unlink()

        if not self.use_closing_rate:
            # Sin revaluación: simplemente marcar como ejecutado
            self.state = 'preview'
            return self._reopen()

        # Buscar cuentas con saldo en moneda extranjera
        company = self.closing_id.company_id
        foreign_currency = company.currency_foreign_id
        if not foreign_currency:
            raise UserError(_("No se ha configurado una moneda extranjera en la compañía."))

        # Buscar accounts con saldos en moneda extranjera (bank, receivable, payable)
        account_types = [
            'asset_cash',
            'asset_receivable',
            'liability_payable',
            'asset_current',
            'liability_current',
        ]
        accounts = self.env['account.account'].search([
            ('company_id', '=', company.id),
            ('account_type', 'in', account_types),
        ])

        odoo_closing_rate = 1.0 / self.closing_rate  # Rate en formato Odoo
        preview_vals = []

        for account in accounts:
            # Obtener saldo actual en moneda empresa
            lines = self.env['account.move.line'].search([
                ('account_id', '=', account.id),
                ('company_id', '=', company.id),
                ('parent_state', '=', 'posted'),
                ('date', '<=', self.closing_date),
            ])
            if not lines:
                continue

            balance = sum(lines.mapped('balance'))
            foreign_balance = sum(lines.mapped('amount_currency'))

            if abs(foreign_balance) < 0.01:
                continue

            # Calcular saldo revaluado
            if company.currency_id.name in ('VES', 'VEF'):
                # Moneda empresa es Bs, foreign_balance está en USD
                revalued_balance = foreign_balance * self.closing_rate
            else:
                # Moneda empresa es USD, calcular equivalente
                revalued_balance = foreign_balance * odoo_closing_rate

            difference = revalued_balance - balance

            if abs(difference) < 0.01:
                continue

            preview_vals.append({
                'wizard_id': self.id,
                'account_id': account.id,
                'current_balance': balance,
                'foreign_balance': foreign_balance,
                'revalued_balance': revalued_balance,
                'difference': difference,
                'diff_type': 'gain' if difference > 0 else 'loss',
            })

        if preview_vals:
            self.env['l10n_ve.revaluation.preview.line'].create(preview_vals)

        self.state = 'preview'
        return self._reopen()

    def action_generate(self):
        """Genera los asientos de revaluación cambiaria."""
        self.ensure_one()
        closing = self.closing_id
        company = closing.company_id

        if not self.use_closing_rate:
            # Sin revaluación: simplemente marcar como ejecutado y continuar
            closing.write({'revaluation_executed': True})
            return {'type': 'ir.actions.act_window_close'}

        if not self.preview_line_ids:
            closing.write({'revaluation_executed': True})
            return {'type': 'ir.actions.act_window_close'}

        # Obtener cuentas de ganancia/pérdida cambiaria
        gain_account = company.income_currency_exchange_account_id
        loss_account = company.expense_currency_exchange_account_id

        if not gain_account or not loss_account:
            raise UserError(_(
                "Debe configurar las cuentas de Ganancia y Pérdida por Diferencia "
                "de Cambio en la configuración de la compañía."
            ))

        # Buscar o crear diario de ajuste
        journal = self.env['account.journal'].search([
            ('company_id', '=', company.id),
            ('type', '=', 'general'),
            ('code', '=', 'AJCAM'),
        ], limit=1)
        if not journal:
            journal = self.env['account.journal'].create({
                'name': 'Ajuste Cambiario',
                'code': 'AJCAM',
                'type': 'general',
                'company_id': company.id,
            })

        move_lines = []
        for line in self.preview_line_ids:
            counterpart = gain_account if line.diff_type == 'gain' else loss_account
            # Línea de ajuste en la cuenta de balance
            move_lines.append((0, 0, {
                'account_id': line.account_id.id,
                'name': f'Revaluación cambiaria al cierre - {line.account_id.code}',
                'debit': line.difference if line.difference > 0 else 0.0,
                'credit': abs(line.difference) if line.difference < 0 else 0.0,
            }))
            # Contrapartida
            move_lines.append((0, 0, {
                'account_id': counterpart.id,
                'name': f'Revaluación cambiaria al cierre - {line.account_id.code}',
                'debit': abs(line.difference) if line.difference < 0 else 0.0,
                'credit': line.difference if line.difference > 0 else 0.0,
            }))

        move = self.env['account.move'].create({
            'journal_id': journal.id,
            'date': self.closing_date,
            'ref': f'Revaluación cambiaria al cierre fiscal {self.closing_date.year}',
            'line_ids': move_lines,
            'company_id': company.id,
        })
        move.action_post()

        closing.write({
            'revaluation_executed': True,
            'revaluation_move_ids': [(4, move.id)],
        })

        self.state = 'done'
        return self._reopen()

    def action_skip(self):
        """Permite saltar la revaluación manteniendo tasas históricas."""
        self.ensure_one()
        self.closing_id.write({'revaluation_executed': True})
        return {'type': 'ir.actions.act_window_close'}

    def _reopen(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }


class RevaluationPreviewLine(models.TransientModel):
    _name = 'l10n_ve.revaluation.preview.line'
    _description = 'Línea de Vista Previa de Revaluación'

    wizard_id = fields.Many2one('l10n_ve.revaluation.wizard', ondelete='cascade')
    account_id = fields.Many2one('account.account', string="Cuenta")
    current_balance = fields.Float(string="Saldo Actual (Bs.)", digits=(16, 2))
    foreign_balance = fields.Float(string="Saldo en Divisas", digits=(16, 2))
    revalued_balance = fields.Float(string="Saldo Revaluado (Bs.)", digits=(16, 2))
    difference = fields.Float(string="Diferencia", digits=(16, 2))
    diff_type = fields.Selection([
        ('gain', 'Ganancia'),
        ('loss', 'Pérdida'),
    ], string="Tipo")
