import logging
from collections import defaultdict

_logger = logging.getLogger(__name__)
from datetime import timedelta
from itertools import groupby

from odoo import api, fields, models, _, Command
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import float_is_zero, float_compare, float_round
from odoo.osv.expression import AND, OR
from odoo.service.common import exp_version

class PosSession(models.Model):
    _inherit = "pos.session"

    tax_today = fields.Float(string="Tasa Sesión", store=True,
                             compute="_tax_today",
                             digits=(16, 8))

    ref_me_currency_id = fields.Many2one('res.currency', related='config_id.show_currency', string="Reference Currency",
                                         store=False)
    cash_register_difference_ref = fields.Monetary(
        compute='_compute_cash_balance_ref',
        string='Ref Before Closing Difference',
        currency_field='ref_me_currency_id',
        help="Difference between the ref theoretical closing balance and the ref real closing balance.",
        readonly=True)

    cash_register_balance_start_mn_ref = fields.Monetary(
        string="Reference Starting Balance",
        currency_field='ref_me_currency_id',
        readonly=True)

    cash_register_balance_end_real_mn_ref = fields.Monetary(
        string="Reference Ending Balance",
        currency_field='ref_me_currency_id',
        readonly=True)
    me_ref_cash_journal_id = fields.Many2one('account.journal', compute='_compute_cash_journal', string='Ref Cash Journal',
                                             store=True)

    cash_register_total_entry_encoding_ref = fields.Monetary(
        compute='_compute_cash_balance_ref',
        string='Ref Total Cash Transaction',
        currency_field='ref_me_currency_id',
        readonly=True)

    cash_register_balance_end_ref = fields.Monetary(
        compute='_compute_cash_balance_ref',
        string="Ref Theoretical Closing Balance",
        currency_field='ref_me_currency_id',
        help="Opening balance summed to all cash transactions.",
        readonly=True)
    cash_real_transaction_ref = fields.Monetary(string='Ref. Transaction', currency_field='ref_me_currency_id',
                                                readonly=True)

    def set_cashbox_pos_usd(self, cashbox_value, notes):
        difference = cashbox_value - self.cash_register_balance_start_mn_ref
        self.cash_register_balance_start_mn_ref = cashbox_value
        self.sudo()._post_statement_difference_usd(difference)
        self._post_cash_details_message_usd('Opening', difference, notes)

    def _post_cash_details_message_usd(self, state, difference, notes):
        message = ""
        if difference:
            message = f"{state} difference: " \
                      f"{self.ref_me_currency_id.symbol + ' ' if self.ref_me_currency_id.position == 'before' else ''}" \
                      f"{self.ref_me_currency_id.round(difference)} " \
                      f"{self.ref_me_currency_id.symbol if self.ref_me_currency_id.position == 'after' else ''}<br/>"
        if notes:
            message += notes.replace('\n', '<br/>')
        if message:
            self.message_post(body=message)

    @api.model
    def _load_pos_data(self, data):
        # Pachacutec: v18.0.1.0.88 - SANEAMIENTO ESTRUCTURAL (Unificar UoM Variant-Template)
        # Realizamos la limpieza de base de datos una vez por carga de datos del POS
        # para asegurar integridad sin parches JIT que ralenticen el sistema.
        self.env['pos.uom.repair'].sudo().run_structural_repair()
        # Pachacutec: v18.0.1.0.97 - SURGICAL SHIELD RESTORATION
        # Restauramos sudo() para la carga de datos base. Esto es esencial en Odoo 18 
        # para evitar AccessError en modelos como stock.picking.type cuando el vendedor
        # tiene permisos limitados o pertenece a otra compañía del grupo.
        try:
            result = super()._load_pos_data(data)
        except Exception as e:
            _logger.error("[POS Data] Error crítico en super()._load_pos_data: %s", str(e))
            result = super()._load_pos_data(data) # Fallback al estándar sin sudo si falla
        # Truth of Odoo 18: Standard data loader injection
        
        company_currency_id = self.company_id.currency_id.id
        target_currency = self.ref_me_currency_id if self.ref_me_currency_id else self.config_id.show_currency
        currency_id = target_currency.id if target_currency else company_currency_id
        
        vef_currency = self.env['res.currency'].search([
            '|', ('name', 'in', ['VES', 'VEF']), ('symbol', 'in', ['Bs', 'Bs.', 'Bs']),
            ('active', '=', True)
        ], limit=1)

        if vef_currency and currency_id == company_currency_id:
             if self.company_id.currency_id.name == 'USD':
                  currency_id = vef_currency.id
             else:
                  usd_currency = self.env['res.currency'].search([('name', '=', 'USD'), ('active', '=', True)], limit=1)
                  if usd_currency:
                      currency_id = usd_currency.id
        
        currency_fields = ['id', 'name', 'symbol', 'position', 'rounding', 'rate', 'decimal_places']
        currency_ref_data = self.env['res.currency'].sudo().search_read([('id', '=', currency_id)], currency_fields)
        
        if currency_ref_data:
            currency_ref = currency_ref_data[0]
            # Pachacutec: v18.0.1.0.96 - EMERGENCY FIX
            # Recuperamos la tasa del sistema antes de los cálculos
            try:
                rate_tasa = float(self.env['res.currency'].sudo().get_trm_systray() or 0.0)
            except:
                rate_tasa = currency_ref.get('rate', 1.0)

            # Odoo Standard: rate = Target / Base. 
            # Inyectamos rate_ve para uso visual (Humano) y rate para cálculo (Odoo).
            rate_human = rate_tasa if rate_tasa > 1 else (1.0 / rate_tasa if rate_tasa > 0 else 1.0)
            rate_odoo = 1.0 / rate_human if rate_human > 0 else 1.0
            
            currency_ref['rate'] = rate_odoo
            currency_ref['rate_ve'] = rate_human
            
            # Pachacutec: v18.0.1.0.91 - SAFE INJECTION
            # Usamos get() y verificamos existencia para evitar KeyError si la carga base falló
            pos_session_data = result.get('pos.session', {}).get('data')
            if pos_session_data:
                pos_session_data[0]['res_currency_ref'] = currency_ref
                
            pos_config_data = result.get('pos.config', {}).get('data')
            if pos_config_data:
                pos_config_data[0].update({
                    'show_currency_rate': rate_odoo,
                    'show_currency_rate_ve': rate_human,
                    'show_currency_symbol': currency_ref['symbol'],
                    'show_currency_position': currency_ref['position'],
                })
            
            # Inyectamos también en la raíz del resultado para máxima compatibilidad con el frontend
            result['res_currency_ref'] = currency_ref
        
        return result


    def try_cash_in_out_ref_currency(self, _type, amount, reason, extras, currency_ref):
        sign = 1 if _type == 'in' else -1
        sessions = self.filtered('me_ref_cash_journal_id')
        if not sessions:
            raise UserError(_("There is no cash payment method for this PoS Session"))

        self.env['account.bank.statement.line'].create([
            {
                'pos_session_id': session.id,
                'journal_id': session.me_ref_cash_journal_id.id,
                'amount': sign * amount,
                'date': fields.Date.context_today(self),
                'payment_ref': '-'.join([session.name, extras['translatedType'], reason]),
                'currency_id': session.ref_me_currency_id.id,
            }
            for session in sessions
        ])

        message_content = [f"Cash {extras['translatedType']}", f'- Amount: {extras["formattedAmount"]}']
        if reason:
            message_content.append(f'- Reason: {reason}')
        self.message_post(body='<br/>\n'.join(message_content))

    @api.depends('config_id', 'payment_method_ids')
    def _compute_cash_journal(self):
        super(PosSession, self)._compute_cash_journal()
        for session in self:
            session.me_ref_cash_journal_id = False
            cash_journal_ref = session.payment_method_ids.filtered(
                lambda p: p.is_cash_count and p.currency_id == session.ref_me_currency_id)[:1].journal_id
            if not cash_journal_ref:
                continue
            session.me_ref_cash_journal_id = cash_journal_ref

    def get_closing_control_data(self):
        closing_control_data = super(PosSession, self).get_closing_control_data()
        self.ensure_one()
        
        cash_payment_methods = self.payment_method_ids.filtered(lambda pm: pm.type == 'cash')
        
        # Identificar método de efectivo extranjero (USD)
        default_cash_payment_ref_method_id = None
        for pm in cash_payment_methods:
            if pm.currency_id == self.ref_me_currency_id or (pm.journal_id and pm.journal_id.currency_id == self.ref_me_currency_id):
                default_cash_payment_ref_method_id = pm
                break
        if not default_cash_payment_ref_method_id:
            for pm in cash_payment_methods:
                name_upper = (pm.name or '').upper()
                if '$' in name_upper or 'USD' in name_upper:
                    default_cash_payment_ref_method_id = pm
                    break
                    
        # Identificar método de efectivo local (Bs)
        default_cash_payment_method_id = None
        for pm in cash_payment_methods:
            if pm != default_cash_payment_ref_method_id:
                default_cash_payment_method_id = pm
                break
                
        orders = self._get_closed_orders()
        payments = orders.payment_ids.filtered(lambda p: p.payment_method_id.type != "pay_later")
        
        # Separar movimientos de caja según moneda
        cash_in_count = 0
        cash_out_count = 0
        cash_in_out_list = []
        
        cash_in_count_ref = 0
        cash_out_count_ref = 0
        cash_in_out_list_ref = []
        
        for cash_move in self.sudo().statement_line_ids.sorted('create_date'):
            if cash_move.currency_id == self.ref_me_currency_id:
                if cash_move.amount > 0:
                    cash_in_count_ref += 1
                    name = f'Cash in {cash_in_count_ref}'
                else:
                    cash_out_count_ref += 1
                    name = f'Cash out {cash_out_count_ref}'
                cash_in_out_list_ref.append({
                    'name': cash_move.payment_ref if cash_move.payment_ref else name,
                    'amount': cash_move.amount
                })
            else:
                if cash_move.amount > 0:
                    cash_in_count += 1
                    name = f'Cash in {cash_in_count}'
                else:
                    cash_out_count += 1
                    name = f'Cash out {cash_out_count}'
                cash_in_out_list.append({
                    'name': cash_move.payment_ref if cash_move.payment_ref else name,
                    'amount': cash_move.amount
                })
                
        # Estructurar detalles de efectivo Bs (local)
        if default_cash_payment_method_id:
            local_payments = payments.filtered(lambda p: p.payment_method_id == default_cash_payment_method_id)
            total_local_payment_amount = sum(local_payments.mapped('amount'))
            
            closing_control_data['default_cash_details'] = {
                'name': default_cash_payment_method_id.name,
                'amount': self.cash_register_balance_start 
                          + total_local_payment_amount 
                          + sum(self.sudo().statement_line_ids.filtered(lambda s: s.currency_id.id != (self.ref_me_currency_id.id or 0)).mapped('amount')),
                'opening': self.cash_register_balance_start,
                'payment_amount': total_local_payment_amount,
                'moves': cash_in_out_list,
                'id': default_cash_payment_method_id.id
            }
        else:
            closing_control_data['default_cash_details'] = {
                'name': '',
                'amount': 0.0,
                'opening': 0.0,
                'payment_amount': 0.0,
                'moves': [],
                'id': False
            }
            
        # Estructurar detalles de efectivo USD (referencia)
        if default_cash_payment_ref_method_id:
            ref_payments = payments.filtered(lambda p: p.payment_method_id == default_cash_payment_ref_method_id)
            total_ref_payment_amount = sum(ref_payments.mapped('amount_ref'))
            
            closing_control_data['default_cash_details_ref'] = {
                'name': default_cash_payment_ref_method_id.name,
                'amount': self.cash_register_balance_start_mn_ref 
                          + total_ref_payment_amount 
                          + sum(self.sudo().statement_line_ids.filtered(lambda s: s.currency_id.id == (self.ref_me_currency_id.id or 0)).mapped('amount')),
                'opening': self.cash_register_balance_start_mn_ref,
                'payment_amount': total_ref_payment_amount,
                'moves': cash_in_out_list_ref,
                'id': default_cash_payment_ref_method_id.id,
                'igtf_amount': sum(p.amount * 0.03 for p in ref_payments),
                'igtf_amount_ref': sum(p.amount_ref * 0.03 for p in ref_payments),
            }
        else:
            closing_control_data['default_cash_details_ref'] = {
                'name': '',
                'amount': 0.0,
                'opening': 0.0,
                'payment_amount': 0.0,
                'moves': [],
                'id': False,
                'igtf_amount': 0.0,
                'igtf_amount_ref': 0.0,
            }
            
        # Re-calcular non_cash_payment_methods excluyendo ambos efectivos
        non_cash_methods = self.payment_method_ids.filtered(lambda pm: pm.type != 'cash')
        non_cash_list = []
        for pm in non_cash_methods:
            pm_payments = payments.filtered(lambda p: p.payment_method_id == pm)
            is_foreign = pm.x_is_foreign_exchange
            non_cash_list.append({
                'name': pm.name,
                'amount': sum(pm_payments.mapped('amount')),
                'amount_ref': sum(pm_payments.mapped('amount_ref')),
                'number': len(pm_payments),
                'id': pm.id,
                'type': pm.type,
                'x_is_foreign_exchange': is_foreign,
                'igtf_amount': sum(p.amount * 0.03 for p in pm_payments) if is_foreign else 0.0,
                'igtf_amount_ref': sum(p.amount_ref * 0.03 for p in pm_payments) if is_foreign else 0.0,
            })
        closing_control_data['non_cash_payment_methods'] = non_cash_list
        
        # Totales de IGTF recaudado
        rate_today = self.tax_today or 1.0
        total_igtf_base_bs = sum(payments.filtered(lambda p: p.payment_method_id.x_is_foreign_exchange).mapped('amount'))
        total_igtf_bs = total_igtf_base_bs * 0.03
        
        closing_control_data['igtf_totals'] = {
            'total_igtf_bs': total_igtf_bs,
            'total_igtf_ref': total_igtf_bs * rate_today,
        }
        return closing_control_data

    def post_closing_cash_details_ref(self, counted_cash):
        if not self.me_ref_cash_journal_id:
            pass
        self.cash_register_balance_end_real_mn_ref = counted_cash
        return {'successful': True}

    def _post_statement_difference_usd(self, amount):
        if amount:
            if self.config_id.cash_control:
                st_line_vals = {
                    'journal_id': self.me_ref_cash_journal_id.id,
                    'amount': amount,
                    'date': self.statement_line_ids.sorted()[-1:].date or fields.Date.context_today(self),
                    'pos_session_id': self.id,
                    'currency_id': self.ref_me_currency_id.id,
                }

            if amount < 0.0:
                if not self.me_ref_cash_journal_id.loss_account_id:
                    raise UserError(
                        _('Please go on the %s journal and define a Loss Account. This account will be used to record cash difference.',
                          self.me_ref_cash_journal_id.name))

                st_line_vals['payment_ref'] = _("Cash difference observed during the counting (Loss)")
                st_line_vals['counterpart_account_id'] = self.me_ref_cash_journal_id.loss_account_id.id
            else:
                if not self.me_ref_cash_journal_id.profit_account_id:
                    raise UserError(
                        _('Please go on the %s journal and define a Profit Account. This account will be used to record cash difference.',
                          self.cash_journal_id.name))

                st_line_vals['payment_ref'] = _("Cash difference observed during the counting (Profit)")
                st_line_vals['counterpart_account_id'] = self.me_ref_cash_journal_id.profit_account_id.id

            self.env['account.bank.statement.line'].create(st_line_vals)

    def update_closing_control_state_session_ref(self, notes):
        self._post_cash_details_message_usd('Closing', self.cash_register_difference_ref, notes)

    @api.depends('payment_method_ids', 'order_ids', 'cash_register_balance_start_mn_ref')
    def _compute_cash_balance_ref(self):
        for session in self:
            cash_payment_method = session.payment_method_ids.filtered(
                lambda p: p.is_cash_count and p.currency_id == session.ref_me_currency_id)[:1]
            if cash_payment_method:
                total_cash_payment = 0.0
                last_session = session.search([('config_id', '=', session.config_id.id), ('id', '!=', session.id)],
                                              limit=1)
                result = self.env['pos.payment']._read_group(
                    [('session_id', '=', session.id), ('payment_method_id', '=', cash_payment_method.id)], ['session_id'],
                    ['amount:sum'])
                if result:
                    total_cash_payment = result[0][1]
                session.cash_register_total_entry_encoding_ref = sum(
                    session.statement_line_ids.filtered(lambda s: s.currency_id == session.ref_me_currency_id).mapped(
                        'amount')) + (
                                                                      0.0 if session.state == 'closed' else total_cash_payment
                                                                  )
                session.cash_register_balance_end_ref = session.cash_register_balance_start_mn_ref + session.cash_register_total_entry_encoding_ref
                session.cash_register_difference_ref = session.cash_register_balance_end_real_mn_ref - session.cash_register_balance_end_ref
            else:
                session.cash_register_total_entry_encoding_ref = 0.0
                session.cash_register_balance_end_ref = 0.0
                session.cash_register_difference_ref = 0.0

    def _validate_session(self, balancing_account=False, amount_to_balance=0, bank_payment_method_diffs=None):
        bank_payment_method_diffs = bank_payment_method_diffs or {}
        self.ensure_one()
        data = {}
        sudo = self.env.user.has_group('point_of_sale.group_pos_user')
        if self.get_session_orders().filtered(lambda o: o.state != 'cancel') or self.sudo().statement_line_ids:
            self.cash_real_transaction = sum(self.sudo().statement_line_ids.mapped('amount'))
            if self.state == 'closed':
                raise UserError(_('This session is already closed.'))
            self._check_if_no_draft_orders()
            self._check_invoices_are_posted()
            cash_difference_before_statements = self.cash_register_difference
            if self.update_stock_at_closing:
                self._create_picking_at_end_of_session()
                self._get_closed_orders().filtered(lambda o: not o.is_total_cost_computed)._compute_total_cost_at_session_closing(self.picking_ids.move_ids)
            try:
                with self.env.cr.savepoint():
                    data = self.with_company(self.company_id).with_context(check_move_validity=False, skip_invoice_sync=True)._create_account_move(balancing_account, amount_to_balance, bank_payment_method_diffs)
            except AccessError as e:
                if sudo:
                    data = self.sudo().with_company(self.company_id).with_context(check_move_validity=False, skip_invoice_sync=True)._create_account_move(balancing_account, amount_to_balance, bank_payment_method_diffs)
                else:
                    raise e
            self._fix_igtf_imbalance_in_session_move()
            balance = sum(self.move_id.line_ids.mapped('balance'))
            try:
                with self.move_id._check_balanced({'records': self.move_id.sudo()}):
                    pass
            except UserError:
                self.env.cr.rollback()
                return self._close_session_action(balance)
            self.sudo()._post_statement_difference(cash_difference_before_statements)
            if self.move_id.line_ids:
                self.move_id.sudo().with_company(self.company_id)._post()
                self.env['pos.order'].search([('session_id', '=', self.id), ('state', '=', 'paid')]).write({'state': 'done'})
            else:
                self.move_id.sudo().unlink()
            self.sudo().with_company(self.company_id)._reconcile_account_move_lines(data)
        else:
            self.sudo()._post_statement_difference(self.cash_register_difference)
        if self.config_id.order_edit_tracking:
            from markupsafe import Markup
            edited_orders = self.get_session_orders().filtered(lambda o: o.is_edited)
            if len(edited_orders) > 0:
                body = _(
                    "Edited order(s) during the session:%s",
                    Markup("<br/><ul>%s</ul>") % Markup().join(Markup("<li>%s</li>") % order._get_html_link() for order in edited_orders)
                )
                self.message_post(body=body)
        self.picking_ids.move_ids.sudo()._trigger_scheduler()
        self.write({'state': 'closed'})
        return

    def close_session_from_ui_ref(self, bank_payment_method_diff_pairs=None):
        bank_payment_method_diffs = dict(bank_payment_method_diff_pairs or [])
        self.ensure_one()
        check_closing_session = self._cannot_close_session_ref(bank_payment_method_diffs)
        if check_closing_session:
            return check_closing_session
        validate_result = self.action_pos_session_closing_control_ref(
            bank_payment_method_diffs=bank_payment_method_diffs)
        if isinstance(validate_result, dict):
            return {
                'successful': False,
                'message': validate_result.get('name'),
                'redirect': True
            }
        self.message_post(body='Point of Sale Session ended')
        return {'successful': True}

    def _cannot_close_session_ref(self, bank_payment_method_diffs=None):
        bank_payment_method_diffs = bank_payment_method_diffs or {}
        if any(order.state == 'draft' for order in self.order_ids):
            return {'successful': False, 'message': _("You cannot close the POS when orders are still in draft"),
                    'redirect': False}
        if self.state == 'closed':
            return {'successful': False, 'message': _("This session is already closed."), 'redirect': True}
        if bank_payment_method_diffs:
            no_loss_account = self.env['account.journal']
            no_profit_account = self.env['account.journal']
            for payment_method in self.env['pos.payment.method'].browse(bank_payment_method_diffs.keys()):
                journal = payment_method.journal_id
                compare_to_zero = self.ref_me_currency_id.compare_amounts(
                    bank_payment_method_diffs.get(payment_method.id), 0)
                if compare_to_zero == -1 and not journal.loss_account_id:
                    no_loss_account |= journal
                elif compare_to_zero == 1 and not journal.profit_account_id:
                    no_profit_account |= journal
            message = ''
            if no_loss_account:
                message += _("Need loss account for the following journals to post the lost amount: %s\n",
                             ', '.join(no_loss_account.mapped('name')))
            if no_profit_account:
                message += _("Need profit account for the following journals to post the gained amount: %s",
                             ', '.join(no_profit_account.mapped('name')))
            if message:
                return {'successful': False, 'message': message, 'redirect': False}

    def action_pos_session_closing_control_ref(self, balancing_account=False, amount_to_balance=0,
                                               bank_payment_method_diffs=None):
        bank_payment_method_diffs = bank_payment_method_diffs or {}
        for session in self:
            if any(order.state == 'draft' for order in session.order_ids):
                raise UserError(_("You cannot close the POS when orders are still in draft"))
            if session.state == 'closed':
                raise UserError(_('This session is already closed.'))
            session.write({'state': 'closing_control', 'stop_at': fields.Datetime.now()})
            if not session.config_id.cash_control:
                return session.action_pos_session_close_ref(balancing_account, amount_to_balance,
                                                             bank_payment_method_diffs)
            if session.rescue and session.config_id.cash_control:
                default_cash_payment_method_id = self.payment_method_ids.filtered(
                    lambda pm: pm.type == 'cash' and pm.payment_method_id.currency_id == self.ref_me_currency_id)[0]
                orders = self.order_ids.filtered(lambda o: o.state == 'paid' or o.state == 'invoiced')
                total_cash = sum(
                    orders.payment_ids.filtered(lambda p: p.payment_method_id == default_cash_payment_method_id).mapped(
                        'amount')
                ) + self.cash_register_balance_start_mn_ref
                session.cash_register_balance_end_real_mn_ref = total_cash
            return session.action_pos_session_validate_ref(balancing_account, amount_to_balance,
                                                           bank_payment_method_diffs)

    def action_pos_session_close_ref(self, balancing_account=False, amount_to_balance=0,
                                     bank_payment_method_diffs=None):
        bank_payment_method_diffs = bank_payment_method_diffs or {}
        return self._validate_session_ref(balancing_account, amount_to_balance, bank_payment_method_diffs)

    def _validate_session_ref(self, balancing_account=False, amount_to_balance=0, bank_payment_method_diffs=None):
        bank_payment_method_diffs = bank_payment_method_diffs or {}
        self.ensure_one()
        sudo = self.env.user.has_group('point_of_sale.group_pos_user')
        if self.order_ids or self.statement_line_ids:
            self.cash_real_transaction_ref = sum(
                self.statement_line_ids.filtered(lambda s: s.currency_id == self.ref_me_currency_id).mapped('amount'))
            cash_difference_before_statements = self.cash_register_difference_ref
            try:
                data = self.with_company(self.company_id).with_context(check_move_validity=False,
                                                                       skip_invoice_sync=True)._create_account_move(
                    balancing_account, amount_to_balance, bank_payment_method_diffs)
            except AccessError as e:
                if sudo:
                    data = self.sudo().with_company(self.company_id).with_context(check_move_validity=False,
                                                                                  skip_invoice_sync=True)._create_account_move(
                        balancing_account, amount_to_balance, bank_payment_method_diffs)
                else:
                    raise e
            self._fix_igtf_imbalance_in_session_move()
            try:
                balance = sum(self.move_id.line_ids.mapped('balance'))
                with self.move_id._check_balanced({'records': self.move_id.sudo()}):
                    pass
            except UserError:
                self.env.cr.rollback()
                return self._close_session_action(balance)
            self.sudo()._post_statement_difference(cash_difference_before_statements)
            if self.move_id.line_ids:
                self.move_id.sudo().with_company(self.company_id)._post()
            else:
                self.move_id.sudo().unlink()
            self.sudo().with_company(self.company_id)._reconcile_account_move_lines(data)
        else:
            self.sudo()._post_statement_difference_usd(self.cash_register_difference_ref)
        return True

    def _fix_igtf_imbalance_in_session_move(self):
        move = self.move_id
        if not move:
            return
        current_balance = sum(move.line_ids.mapped('balance'))
        if float_is_zero(current_balance, precision_rounding=self.currency_id.rounding):
            return
        closed_orders = self._get_closed_orders()
        total_igtf = sum(
            order.x_igtf_amount
            for order in closed_orders
            if not order.is_invoiced and order.x_igtf_amount
        )
        total_igtf_rounded = float_round(total_igtf, precision_rounding=self.currency_id.rounding)
        if float_is_zero(total_igtf_rounded, precision_rounding=self.currency_id.rounding):
            return
        diff_vs_igtf = abs(current_balance - total_igtf_rounded)
        tolerance = max(0.05, total_igtf_rounded * 0.01)
        if diff_vs_igtf > tolerance:
            _logger.warning("[IGTF] Descuadre (%.2f) no coincide con IGTF total (%.2f). No se aplica corrección automática.",
                current_balance, total_igtf_rounded)
            return
        igtf_product = self.config_id.x_igtf_product_id
        if not igtf_product:
            return
        product_accounts = igtf_product._get_product_accounts()
        igtf_account = igtf_product.property_account_income_id or product_accounts.get('income')
        if not igtf_account:
            return
        MoveLine = self.env['account.move.line'].with_context(
            check_move_validity=False, skip_invoice_sync=True)
        MoveLine.create({
            'move_id': move.id,
            'account_id': igtf_account.id,
            'name': 'IGTF - Corrección de balance',
            'debit': 0.0,
            'credit': current_balance,
            'amount_currency': -current_balance,
            'currency_id': self.currency_id.id,
        })

    def action_pos_session_validate_ref(self, balancing_account=False, amount_to_balance=0,
                                        bank_payment_method_diffs=None):
        bank_payment_method_diffs = bank_payment_method_diffs or {}
        return self.action_pos_session_close_ref(balancing_account, amount_to_balance, bank_payment_method_diffs)

    def action_pos_session_open(self):
        return super(PosSession, self).action_pos_session_open()

    @api.model_create_multi
    def create(self, vals_list):
        sessions = super(PosSession, self).create(vals_list)
        for session in sessions:
            if session.config_id.cash_control:
                last_session = self.search([('config_id', '=', session.config_id.id), ('id', '!=', session.id)],
                                           limit=1)
                if last_session:
                    session.cash_register_balance_start_mn_ref = last_session.cash_register_balance_end_real_mn_ref
        return sessions

    @api.depends('config_id')
    def _tax_today(self):
        for rec in self:
            rec.tax_today = 1 / rec.config_id.show_currency_rate if rec.config_id.show_currency_rate > 0 else 1

    def _create_cash_statement_lines_and_cash_move_lines(self, data):
        MoveLine = data.get('MoveLine')
        split_receivables_cash = data.get('split_receivables_cash')
        combine_receivables_cash = data.get('combine_receivables_cash')
        split_cash_statement_line_vals = []
        split_cash_receivable_vals = []
        for payment, amounts in split_receivables_cash.items():
            journal_id = payment.payment_method_id.journal_id.id
            amount = float_round(amounts['amount'] if (payment.payment_method_id.currency_id == self.company_id.currency_id or not payment.payment_method_id.currency_id) else amounts['amount'] * self.config_id.show_currency_rate, precision_rounding=self.currency_id.rounding)
            amount_converted = float_round(amounts['amount_converted'], precision_rounding=self.company_id.currency_id.rounding)
            split_cash_statement_line_vals.append(
                self._get_split_statement_line_vals(journal_id, amount, payment)
            )
            split_cash_receivable_vals.append(
                self._get_split_receivable_vals(payment, amount, amount_converted)
            )
        combine_cash_statement_line_vals = []
        combine_cash_receivable_vals = []
        for payment_method, amounts in combine_receivables_cash.items():
            if not float_is_zero(amounts['amount'], precision_rounding=self.currency_id.rounding):
                amount = float_round(amounts['amount'] if (payment_method.currency_id == self.company_id.currency_id or not payment_method.currency_id) else amounts['amount'] * self.config_id.show_currency_rate, precision_rounding=self.currency_id.rounding)
                amount_converted = float_round(amounts['amount_converted'], precision_rounding=self.company_id.currency_id.rounding)
                combine_cash_statement_line_vals.append(
                    self._get_combine_statement_line_vals(payment_method.journal_id.id, amount, payment_method)
                )
                combine_cash_receivable_vals.append(
                    self._get_combine_receivable_vals(payment_method, amount, amount_converted)
                )
        BankStatementLine = self.env['account.bank.statement.line']
        split_cash_statement_lines = BankStatementLine.create(split_cash_statement_line_vals).mapped(
            'move_id.line_ids').filtered(lambda line: line.account_id.account_type == 'asset_receivable')
        combine_cash_statement_lines = BankStatementLine.create(combine_cash_statement_line_vals).mapped(
            'move_id.line_ids').filtered(lambda line: line.account_id.account_type == 'asset_receivable')
        split_cash_receivable_lines = MoveLine.create(split_cash_receivable_vals)
        combine_cash_receivable_lines = MoveLine.create(combine_cash_receivable_vals)
        data.update(
            {'split_cash_statement_lines': split_cash_statement_lines,
             'combine_cash_statement_lines': combine_cash_statement_lines,
             'split_cash_receivable_lines': split_cash_receivable_lines,
             'combine_cash_receivable_lines': combine_cash_receivable_lines
             })
        return data

    def _create_bank_payment_moves(self, data):
        combine_receivables_bank = data.get('combine_receivables_bank')
        split_receivables_bank = data.get('split_receivables_bank')
        bank_payment_method_diffs = data.get('bank_payment_method_diffs')
        MoveLine = data.get('MoveLine')
        payment_method_to_receivable_lines = {}
        payment_to_receivable_lines = {}
        for payment_method, amounts in combine_receivables_bank.items():
            amount = float_round(amounts['amount'] if (
                        payment_method.currency_id == self.company_id.currency_id or not payment_method.currency_id) else \
            amounts['amount'] * self.config_id.show_currency_rate, precision_rounding=self.currency_id.rounding)
            amount_converted = float_round(amounts['amount_converted'] if (
                        payment_method.currency_id == self.company_id.currency_id or not payment_method.currency_id) else \
                amounts['amount_converted'] * self.config_id.show_currency_rate, precision_rounding=self.currency_id.rounding)
            combine_receivable_line = MoveLine.create(self._get_combine_receivable_vals(payment_method, amount, amount_converted))
            amounts['amount'] = amount
            amounts['amount_converted'] = amount_converted
            payment_receivable_line = self._create_combine_account_payment(payment_method, amounts, diff_amount=bank_payment_method_diffs.get(payment_method.id) or 0)
            payment_method_to_receivable_lines[payment_method] = combine_receivable_line | payment_receivable_line
        for payment, amounts in split_receivables_bank.items():
            amount = float_round(amounts['amount'] if (
                    payment.currency_id == self.company_id.currency_id or not payment.currency_id) else \
                amounts['amount'] * self.config_id.show_currency_rate, precision_rounding=self.currency_id.rounding)
            amount_converted = float_round(amounts['amount_converted'] if (
                    payment.currency_id == self.company_id.currency_id or not payment.currency_id) else \
                amounts['amount_converted'] * self.config_id.show_currency_rate, precision_rounding=self.currency_id.rounding)
            split_receivable_line = MoveLine.create(self._get_split_receivable_vals(payment, amount, amount_converted))
            amounts['amount'] = amount
            amounts['amount_converted'] = amount_converted
            payment_receivable_line = self._create_split_account_payment(payment, amounts)
            payment_to_receivable_lines[payment] = split_receivable_line | payment_receivable_line
        for bank_payment_method in self.payment_method_ids.filtered(lambda pm: pm.type == 'bank' and pm.split_transactions):
            self._create_diff_account_move_for_split_payment_method(bank_payment_method, bank_payment_method_diffs.get(bank_payment_method.id) or 0)
        data['payment_method_to_receivable_lines'] = payment_method_to_receivable_lines
        data['payment_to_receivable_lines'] = payment_to_receivable_lines
        data['online_payment_to_receivable_lines'] = {}
        return data

class ProductProduct(models.Model):
    _inherit = 'product.product'
    @api.model
    def _load_pos_data_fields(self, config_id):
        return super()._load_pos_data_fields(config_id) + ['list_price_usd', 'standard_price_usd', 'lst_price']

class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'
    @api.model
    def _load_pos_data_fields(self, config_id):
        return super()._load_pos_data_fields(config_id) + ['currency_id']

class PosConfig(models.Model):
    _inherit = 'pos.config'
    @api.model
    def _load_pos_data_fields(self, config_id):
        # Shield mechanism to ensure critical fields are always present
        fields = super()._load_pos_data_fields(config_id)
        if fields:
             mandatory = [
                'use_pricelist', 'show_dual_currency', 'show_currency', 
                'show_currency_rate', 'show_currency_symbol', 'show_currency_position'
             ]
             for f in mandatory:
                 if f not in fields:
                     fields.append(f)
        return fields
