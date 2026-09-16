# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from datetime import timedelta
from functools import partial
from itertools import groupby
from collections import defaultdict

import psycopg2
import pytz
import re

from odoo import api, fields, models, tools, _
from odoo.tools import float_is_zero, float_round, float_repr, float_compare
from odoo.exceptions import ValidationError, UserError
from odoo.osv.expression import AND
import base64

_logger = logging.getLogger(__name__)


class ReportSaleDetails(models.AbstractModel):
    _inherit = 'report.point_of_sale.report_saledetails'

    @api.model
    def get_sale_details(self, date_start=False, date_stop=False, config_ids=False, session_ids=False):
        data = super(ReportSaleDetails, self).get_sale_details(date_start, date_stop, config_ids, session_ids)
        # Odoo 18: data['products'] es una lista de CATEGORÍAS:
        # [{'name': 'Cat', 'qty': N, 'total': T, 'products': [{...}, ...]}, ...]
        # REGLA: NUNCA reemplazar data['products'], data['payments'] ni data['taxes']
        # con estructuras simplificadas. Solo ENRIQUECER con campos _ref.

        pos_session = self.env['pos.session'].search([('id', 'in', session_ids)]) if session_ids else self.env['pos.session']
        rate_today = 1
        if pos_session:
            session = pos_session[0]
            start_date = session.start_at or fields.Datetime.now()
            rate_record = self.env['res.currency.rate'].search([
                ('company_id', '=', session.company_id.id),
                ('currency_id.name', '=', 'USD'),
                ('name', '<=', start_date)
            ], order='name desc', limit=1)
            if rate_record:
                rate_today = (1.0 / rate_record.rate) if rate_record.rate < 1.0 else rate_record.rate
            else:
                rate_today = session.tax_today or 1.0
        else:
            rate_today = self.env.company.currency_id_dif.inverse_rate or 1.0

        currency_id_dif = self.env.company.currency_id_dif
        data['currency_precision_ref'] = currency_id_dif.decimal_places
        data['symbol_ref'] = currency_id_dif.symbol
        data['symbol'] = self.env.company.currency_id.symbol
        data['rate_today'] = rate_today
        data['total_paid_ref'] = currency_id_dif.round(
            data['total_paid'] / rate_today
        ) if rate_today else 0.0

        # Inyectar price_unit_ref DENTRO de cada producto de cada categoría
        for category in data.get('products', []):
            for prod in category.get('products', []):
                price_unit = prod.get('price_unit') or prod.get('price', 0.0)
                prod['price_unit_ref'] = price_unit / rate_today if rate_today else 0.0

        # Enriquecer payments nativos con total_ref (preservar TODA la estructura nativa)
        for payment in data.get('payments', []):
            payment['total_ref'] = payment.get('total', 0.0) / rate_today if rate_today else 0.0

        # Enriquecer taxes nativos con _ref (preservar TODA la estructura nativa)
        for tax in data.get('taxes', []):
            tax['tax_amount_ref'] = tax.get('tax_amount', 0.0) / rate_today if rate_today else 0.0
            tax['base_amount_ref'] = tax.get('base_amount', 0.0) / rate_today if rate_today else 0.0

        return data

    def update_key_values_data(self, date_start=False, date_stop=False, config_ids=False, session_ids=False):
        domain = [('state', 'in', ['paid', 'invoiced', 'done'])]
        if (session_ids):
            domain = AND([domain, [('session_id', 'in', session_ids)]])
        else:
            if date_start:
                date_start = fields.Datetime.from_string(date_start)
            else:
                # start by default today 00:00:00
                user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
                today = user_tz.localize(fields.Datetime.from_string(fields.Date.context_today(self)))
                date_start = today.astimezone(pytz.timezone('UTC'))

            if date_stop:
                date_stop = fields.Datetime.from_string(date_stop)
                # avoid a date_stop smaller than date_start
                if (date_stop < date_start):
                    date_stop = date_start + timedelta(days=1, seconds=-1)
            else:
                # stop by default today 23:59:59
                date_stop = date_start + timedelta(days=1, seconds=-1)

            domain = AND([domain,
                          [('date_order', '>=', fields.Datetime.to_string(date_start)),
                           ('date_order', '<=', fields.Datetime.to_string(date_stop))]
                          ])

            if config_ids:
                domain = AND([domain, [('config_id', 'in', config_ids)]])

        orders = self.env['pos.order'].search(domain)
        user_currency = self.env.company.currency_id
        total = 0.0
        total_ref = 0.0
        products_sold = {}
        taxes = {}
        for order in orders:
            if user_currency != order.pricelist_id.currency_id:
                total += order.pricelist_id.currency_id._convert(
                    order.amount_total, user_currency, order.company_id, order.date_order or fields.Date.today())
            else:
                total += order.amount_total
            total_ref += order.amount_total_ref
            currency = order.session_id.currency_id

            for line in order.lines:
                key = (line.product_id, line.price_unit, line.price_unit_ref, line.discount)
                products_sold.setdefault(key, 0.0)
                products_sold[key] += line.qty

                if line.tax_ids_after_fiscal_position:
                    line_taxes = line.tax_ids_after_fiscal_position.sudo().compute_all(
                        line.price_unit * (1 - (line.discount or 0.0) / 100.0), currency, line.qty,
                        product=line.product_id, partner=line.order_id.partner_id or False)
                    for tax in line_taxes['taxes']:
                        taxes.setdefault(tax['id'], {'name': tax['name'], 'tax_amount': 0.0, 'base_amount': 0.0,
                                                     'tax_amount_ref': 0.0, 'base_amount_ref': 0.0})
                        taxes[tax['id']]['tax_amount'] += tax['amount']
                        taxes[tax['id']]['base_amount'] += tax['base']
                        if order.session_rate != 0:
                            tax_amount_ref = tax['amount']/order.session_rate
                            base_amount_ref = tax['base']/order.session_rate
                            taxes[tax['id']]['tax_amount_ref'] += tax_amount_ref
                            taxes[tax['id']]['base_amount_ref'] += base_amount_ref
                else:
                    taxes.setdefault(0, {'name': _('No Taxes'), 'tax_amount': 0.0, 'base_amount': 0.0,
                                         'tax_amount_ref': 0.0, 'base_amount_ref': 0.0})
                    taxes[0]['base_amount'] += line.price_subtotal_incl
                    taxes[0]['base_amount_ref'] += line.price_subtotal_incl_ref

        payment_ids = self.env["pos.payment"].search([('pos_order_id', 'in', orders.ids)]).ids
        payments = []
        if payment_ids:
            # Pachacutec: v18.0.1.1.4 - Migración a ORM para evitar KeyError: 'name' en traducciones SQL
            payment_groups = self.env['pos.payment'].read_group(
                [('id', 'in', payment_ids)],
                ['payment_method_id', 'amount', 'amount_ref'],
                ['payment_method_id']
            )
            for group in payment_groups:
                method_id, method_name = group['payment_method_id']
                payments.append({
                    'name': method_name,
                    'total': group['amount'],
                    'total_ref': group['amount_ref'],
                })

        return {
            'total_paid_ref': self.env.company.currency_id_dif.round(total_ref),
            'taxes': list(taxes.values()),
            'payments': payments,
            'products': sorted([{
                'product_id': product.id,
                'product_name': product.name,
                'code': product.default_code,
                'quantity': qty,
                'price_unit': price_unit,
                'price_unit_ref': price_unit_ref,
                'discount': discount,
                'uom': product.uom_id.name,
            } for (product, price_unit, price_unit_ref, discount), qty in products_sold.items()],
                key=lambda l: l['product_name'])

        }
