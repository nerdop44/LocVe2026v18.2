from odoo import api, fields, models, _
from datetime import date, timedelta, datetime
from bs4 import BeautifulSoup
import requests
import logging
from odoo.tools import SQL
from odoo.tools.misc import get_lang

_logger = logging.getLogger(__name__)
import urllib3
urllib3.disable_warnings()

class ResCurrencyRate(models.Model):
    _inherit = 'res.currency.rate'

    bcv_rate = fields.Float(
        string='Unidad por USD',
        compute='_compute_bcv_rates',
        digits=(12, 4),
        help="Muestra el valor de la tasa en bolívares por dólar (ej: 744.2264)."
    )
    inverse_bcv_rate = fields.Float(
        string='USD por unidad',
        compute='_compute_bcv_rates',
        digits=(12, 12),
        help="Muestra la tasa técnica decimal (ej: 0.001343677139)."
    )

    @api.depends('rate', 'currency_id')
    def _compute_bcv_rates(self):
        for rec in self:
            if rec.currency_id.name in ['VEF', 'VES']:
                rec.bcv_rate = rec.rate
                rec.inverse_bcv_rate = 1.0 / rec.rate if rec.rate > 0.0 else 0.0
            else:
                rec.bcv_rate = 1.0 / rec.rate if rec.rate > 0.0 else 0.0
                rec.inverse_bcv_rate = rec.rate

class ResCurrency(models.Model):
    _inherit = 'res.currency'

    bcv_rate_ids = fields.One2many('res.currency.rate', compute='_compute_bcv_rate_ids', string='Tasas BCV')

    def _compute_bcv_rate_ids(self):
        usd_currency = self.env['res.currency'].search([('name', '=', 'USD')], limit=1)
        company = self.env.company
        for rec in self:
            if rec.name in ['VEF', 'VES']:
                if company.currency_id.name in ['VEF', 'VES']:
                    rec.bcv_rate_ids = usd_currency.rate_ids if usd_currency else rec.rate_ids
                else:
                    rec.bcv_rate_ids = rec.rate_ids
            else:
                rec.bcv_rate_ids = rec.rate_ids





    @api.model
    def _normalize_to_company_recordset(self, data):
        """ Helper to force any input into a res.company recordset. """
        if hasattr(data, 'currency_id'): # Already a recordset
            return data
        
        c_ids = []
        if isinstance(data, list):
            c_ids = [c['id'] if isinstance(c, dict) else (c.id if hasattr(c, 'id') else c) for c in data]
        elif isinstance(data, dict):
            if 'id' in data:
                c_ids = [data['id']]
            else:
                c_ids = [int(k) for k, v in data.items() if v and str(k).isdigit()]
        elif isinstance(data, (int, str)):
            try:
                c_ids = [int(data)]
            except:
                pass
        elif hasattr(data, 'ids'):
            c_ids = data.ids
            
        if c_ids:
            return self.env['res.company'].browse(c_ids)
        return self.env.company

    @api.model
    def _get_query_currency_table(self, options):
        """ Final Resolution V7.0: Universal Enterprise Compatibility.
        Provides all 6 standard Enterprise columns + custom 'precision' column.
        Columns: company_id, period_key, date_from, date_next, rate_type, rate, precision
        """
        companies = self._normalize_to_company_recordset(options.get('companies') if isinstance(options, dict) else options)
        
        rows = []
        for company in companies:
            # Standard Odoo 18 columns: company_id, period_key, date_from, date_next, rate_type, rate
            # Our custom addition: precision
            rows.append(SQL("(%(company_id)s, NULL, NULL, NULL, NULL, 1.0, %(precision)s)", 
                company_id=company.id, 
                precision=company.currency_id.decimal_places or 2
            ))
        
        if not rows:
            rows = [SQL("(%(company_id)s, NULL, NULL, NULL, NULL, 1.0, 2)", company_id=self.env.company.id)]

        return SQL("(VALUES %(rows)s) AS currency_table(company_id, period_key, date_from, date_next, rate_type, rate, precision)", 
            rows=SQL(', ').join(rows)
        )

    @api.model
    def _check_currency_table_monocurrency(self, companies):
        # Override to ensure it uses our normalized recordsets
        companies_rs = self._normalize_to_company_recordset(companies)
        return super()._check_currency_table_monocurrency(companies_rs)

    # --- Business Logic (Restored) ---

    facturas_por_actualizar = fields.Boolean(compute="_facturas_por_actualizar")
    sincronizar = fields.Boolean(string="Sincronizar", default=False)
    # Pachacutec: DolarToday removido, solo se permite BCV.
    # server = fields.Selection([('bcv', 'BCV'), ('dolar_today', 'Dolar Today Promedio')], string='Servidor', default='bcv')
    act_productos = fields.Boolean(string="Actualizar Productos", default=False)
    can_edit_rates = fields.Boolean(compute='_compute_can_edit_rates')

    def _compute_can_edit_rates(self):
        is_manager = self.env.user.has_group('account.group_account_manager')
        for rec in self:
            rec.can_edit_rates = is_manager

    def _convert(self, from_amount, to_currency, company=None, date=None, round=True, custom_rate=0.0):
        self, to_currency = self or to_currency, to_currency or self
        assert self, "convert amount from unknown currency"
        to_currency = to_currency or self
        if not company:
            company = self.env.company
        if not date:
            date = fields.Date.context_today(self)
        
        if self == to_currency:
            to_amount = from_amount
        else:
            if custom_rate > 0:
                to_amount = from_amount * custom_rate
            elif self.env.context.get('tasa_factura'):
                if to_currency == self.env.company.currency_id_dif:
                    to_amount = from_amount / self.env.context.get('tasa_factura')
                else:
                    to_amount = from_amount * self.env.context.get('tasa_factura')
            else:
                to_amount = from_amount * self._get_conversion_rate(self, to_currency, company, date)
        
        return to_currency.round(to_amount) if round else to_amount

    def _facturas_por_actualizar(self):
        for rec in self:
            if rec.name == self.env.company.currency_id_dif.name:
                if self.env['account.move'].search_count([('state', 'in', ['draft','posted'])]):
                    rec.facturas_por_actualizar = True
                else:
                    rec.facturas_por_actualizar = False
            else:
                rec.facturas_por_actualizar = False

    def actualizar_facturas(self):
        for rec in self:
            facturas = self.env['account.move'].search([('acuerdo_moneda', '=', True)])
            if facturas:
                for f in facturas:
                    f.tax_today = round(rec.inverse_rate, 4)
                    for l in f.line_ids:
                        l.tax_today = round(rec.inverse_rate, 4)
                        l._debit_usd()
                        l._credit_usd()
                    for d in f.invoice_line_ids:
                        d.tax_today = round(rec.inverse_rate, 4)
                        d._price_unit_usd()
                        d._price_subtotal_usd()
                    f._amount_all_usd()
                    f._compute_payments_widget_reconciled_info_USD()

    def actualizar_productos(self, tasa_fresca=None):
        """ Actualización masiva de list_price (Bs) basada en list_price_usd y la tasa actual.
        Uso de SQL para evitar Timeouts en catálogos grandes. Pachacutec.
        Acepta tasa_fresca para usar la tasa BCV recién obtenida sin depender del caché ORM.
        """
        usd_currency = self.env['res.currency'].search([('name', 'in', ['USD', 'US$'])], limit=1)
        if not usd_currency:
            _logger.warning(">>>>>> Pachacutec: No se encontró la moneda USD en la base de datos. Se cancela la actualización de productos.")
            return

        for rec in self:
            if tasa_fresca and tasa_fresca > 1.0:
                tasa = tasa_fresca
            else:
                # Priorizar la tasa de la moneda USD sobre la configurada en la compañía activa
                tasa = usd_currency.inverse_rate
                if tasa <= 1.0:
                    tasa = usd_currency.get_trm_systray()
            try:
                tasa = float(tasa)
            except (TypeError, ValueError):
                tasa = 0.0
            if tasa <= 1.0:
                _logger.warning(">>>>>> Pachacutec: Tasa inválida o igual a 1.0 (%s). Se omite la actualización de precios de productos para evitar corrupción.", tasa)
                continue
            
            _logger.info(">>>>>> Pachacutec: Iniciando actualización masiva de precios (Tasa: %s)", tasa)
            
            # Actualizar Templates (diferenciado por moneda base de la compañía)
            company = self.env.company
            if company.currency_id.name == 'USD':
                query_tmpl = """
                    UPDATE product_template 
                    SET list_price = list_price_usd,
                        list_price_bs = list_price_usd * %s 
                    WHERE list_price_usd > 0
                """
                self.env.cr.execute(query_tmpl, (tasa,))
            else:
                query_tmpl = """
                    UPDATE product_template 
                    SET list_price = list_price_usd * %s,
                        list_price_bs = list_price_usd * %s 
                    WHERE list_price_usd > 0
                """
                self.env.cr.execute(query_tmpl, (tasa, tasa))
            
            # Nota: Odoo 18 maneja variantes. Las variantes heredan list_price de product_template.
            # El campo lst_price no existe en la tabla product_product, por lo que esta consulta es redundante y errónea.
            # Pachacutec: Remoción de query_prod para evitar RPC_ERROR.
            
            _logger.info(">>>>>> Pachacutec: Precios actualizados vía SQL.")

    def action_fix_astronomical_prices(self):
        """ Método de emergencia para restaurar precios inflados trillonarios """
        company = self.env.company
        tasa = company.currency_id_dif.get_trm_systray() if company.currency_id_dif else 0.0
        if tasa <= 1:
            return
            
        # Umbral de sanidad: 50,000 (ajustable). Cualquier cosa por encima es sospechosa de inflación.
        threshold = 50000.0
        
        # Corregir Templates
        templates = self.env['product.template'].search([('list_price', '>', threshold)])
        _logger.info(">>>>>>>> Pachacutec: Corrigiendo %s templates con precios altos", len(templates))
        for t in templates:
            price = t.list_price
            # Si el precio es más de 100 veces el umbral, es definitivamente corrupto
            while price > threshold * 10:
                price = price / tasa
            t.list_price = price
            
        # Corregir Variantes
        variants = self.env['product.product'].search([('lst_price', '>', threshold)])
        _logger.info(">>>>>>>> Pachacutec: Corrigiendo %s variantes con precios altos", len(variants))
        for v in variants:
            price = v.lst_price
            while price > threshold * 10:
                price = price / tasa
            v.lst_price = price

            list_product_ids = self.env['product.pricelist.item'].search([('currency_id', '=', self.id)])

            for lp in list_product_ids:
                if lp.pricelist_id.pricelist_bs_id:
                    dominio = [('pricelist_id', '=', lp.pricelist_id.pricelist_bs_id.id)]
                    if lp.product_id:
                        dominio.append((('product_id', '=', lp.product_id.id)))
                    elif lp.product_tmpl_id:
                        dominio.append((('product_tmpl_id', '=', lp.product_tmpl_id.id)))
                    product_id_bs = self.env['product.pricelist.item'].search(dominio)
                    for p in product_id_bs:
                        p.fixed_price = lp.fixed_price * rec.inverse_rate
                else:
                    dominio = [('currency_id', '=', lp.company_id.currency_id.id or self.env.company.currency_id.id)]
                    if lp.product_id:
                        dominio.append((('product_id', '=', lp.product_id.id)))
                    elif lp.product_tmpl_id:
                        dominio.append((('product_tmpl_id', '=', lp.product_tmpl_id.id)))
                    product_id_bs = self.env['product.pricelist.item'].search(dominio)
                    for p in product_id_bs:
                        p.fixed_price = lp.fixed_price * rec.inverse_rate

            channel_id = self.env.ref('account_dual_currency.trm_channel')
            channel_id.message_post(
                body="Todos los productos han sido actualizados con la nueva tasa de cambio",
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
            )

    def get_bcv(self):
        url = "https://www.bcv.org.ve/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
        }
        try:
            # Pachacutec: Incrementamos timeout a 25s para mejorar resiliencia al BCV
            req = requests.get(url, headers=headers, verify=False, timeout=25)
        except Exception as e:
            return False

        status_code = req.status_code
        if status_code == 200:
            html = BeautifulSoup(req.text, "html.parser")
            dolar_tag = html.find('div', {'id': 'dolar'})
            if not dolar_tag:
                return False
            try:
                # Extraemos el texto del tag strong directamente, limpiamos y convertimos
                val_usd_str = dolar_tag.find('strong').text.strip()
                val_usd = float(val_usd_str.replace('.', '').replace(',', '.'))
            except Exception:
                return False

            euro_tag = html.find('div', {'id': 'euro'})
            if not euro_tag:
                val_eur = 0.0
            else:
                try:
                    val_eur_str = euro_tag.find('strong').text.strip()
                    val_eur = float(val_eur_str.replace('.', '').replace(',', '.'))
                except Exception:
                    val_eur = 0.0

            # Parsear fecha de vigencia BCV
            parsed_date = None
            try:
                fecha_el = html.find('div', class_='pull-right')
                if not fecha_el:
                    fecha_el = html.find(class_='fecha-valor')
                if not fecha_el:
                    fecha_el = html.find('span', class_='date-display-single')
                
                if fecha_el:
                    date_str = fecha_el.text.strip().lower()
                    meses = {
                        'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
                        'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
                        'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
                    }
                    parts = date_str.replace(',', '').split()
                    d = m = y = None
                    for part in parts:
                        if part.isdigit():
                            if len(part) <= 2:
                                d = int(part)
                            elif len(part) == 4:
                                y = int(part)
                        elif part in meses:
                            m = meses[part]
                    if d and m and y:
                        parsed_date = date(y, m, d)
            except Exception as e:
                pass

            curr_name = self.name
            if curr_name == 'USD':
                return {'rate': val_usd, 'date': parsed_date}
            elif curr_name == 'EUR':
                return {'rate': val_eur, 'date': parsed_date}
            elif curr_name in ['VES', 'VEF']:
                company = self.env.company
                if company.currency_id.name == 'USD':
                    return {'rate': val_usd, 'date': parsed_date}
                return {'rate': 1.0, 'date': parsed_date}
            else:
                return False
        else:
            return False

    # Pachacutec: get_dolar_today_promedio removido.

    def actualizar_tasa(self):
        for rec in self:
            # Si rec es VEF o VES (monedas locales/alternas), delegamos a las extranjeras
            # pero SOLO si la moneda base de la compañía es VEF o VES!
            if rec.name in ['VES', 'VEF']:
                company = self.env.company
                if company.currency_id.name in ['VES', 'VEF']:
                    monedas_ext = self.env['res.currency'].search([('name', 'in', ['USD', 'EUR']), ('active', '=', True)])
                    # Propagar contexto de origen (cron o botón)
                    for m in monedas_ext.with_context(self.env.context):
                        m.actualizar_tasa()
                    continue

            # Para monedas extranjeras (USD, EUR), se calcula su tasa BCV (ej: 523.675)
            result = rec.get_bcv()
            
            # Gestionar reintento
            if not result:
                for c in self.env['res.company'].search([('bcv_retry_enabled', '=', True)]):
                    c.bcv_retry_pending = True
            
            if result:
                for c in self.env['res.company'].search([('bcv_retry_enabled', '=', True)]):
                    c.bcv_retry_pending = False
                
                nueva_tasa_bcv = result['rate']
                fecha_bcv = result.get('date') or fields.Date.context_today(self)

                channel_id = self.env.ref('account_dual_currency.trm_channel')
                company_ids = self.env['res.company'].search([])
                
                # Definir contexto origen para auditoría
                orig_ctx = 'from_button' if not self.env.context.get('from_cron') else 'from_cron'
                
                for c in company_ids:
                    # Determinar el destino de la tasa y el valor de la tasa
                    if rec.name == c.currency_id.name:
                        target_currency = c.currency_id_dif
                        if not target_currency:
                            continue
                        if target_currency.name in ['VES', 'VEF']:
                            odoo_rate = nueva_tasa_bcv
                        else:
                            odoo_rate = 1.0 / nueva_tasa_bcv
                    else:
                        target_currency = rec
                        if c.currency_id.name == 'USD':
                            odoo_rate = nueva_tasa_bcv
                        else:
                            odoo_rate = 1.0 / nueva_tasa_bcv

                    if not target_currency:
                        continue
                    
                    tasa_actual = self.env['res.currency.rate'].sudo().search(
                        [('name', '=', fecha_bcv), ('currency_id', '=', target_currency.id), ('company_id', '=', c.id)], limit=1)
                    
                    nueva = False
                    if not tasa_actual:
                        self.env['res.currency.rate'].sudo().with_context({orig_ctx: True}).create({
                                'currency_id': target_currency.id,
                                'name': fecha_bcv,
                                'rate': odoo_rate,
                                'company_id': c.id,
                        })
                        nueva = True
                    else:
                        if abs(tasa_actual.rate - odoo_rate) > 0.000001:
                            tasa_actual.sudo().with_context({orig_ctx: True}).write({
                                'rate': odoo_rate
                            })
                            nueva = True

                    if nueva:

                        channel_id.message_post(
                            body="Tasa de cambio actualizada para %s (%s): %s (en %s), BCV a las %s." % (
                                target_currency.name, c.name, odoo_rate, c.currency_id.name,
                                datetime.strftime(fields.Datetime.context_timestamp(self, datetime.now()),
                                                  "%d-%m-%Y %H:%M:%S")),
                            message_type='notification',
                            subtype_xmlid='mail.mt_comment',
                        )
                if rec.act_productos:
                    rec.actualizar_productos()

    @api.model
    def _cron_actualizar_tasa(self):
        # Pasar contexto from_cron=True para el registro de auditoría
        monedas = self.env['res.currency'].with_context(from_cron=True).search([('active', '=', True), ('sincronizar', '=', True)])
        for m in monedas:
            m.actualizar_tasa()

    @api.model
    def _cron_retry_bcv_sync(self):
        """Reintento de sincronización BCV. Solo ejecuta si hay un reintento pendiente."""
        companies = self.env['res.company'].search([
            ('bcv_retry_enabled', '=', True),
            ('bcv_retry_pending', '=', True),
        ])
        if not companies:
            return  # Nada que reintentar
        monedas = self.env['res.currency'].with_context(from_cron=True).search([
            ('active', '=', True), ('sincronizar', '=', True)
        ])
        for m in monedas:
            m.actualizar_tasa()

    def recuperar_tasas_historicas(self):
        for rec in self:
            # Si rec es VEF o VES (monedas locales/alternas), delegamos a las extranjeras
            # pero SOLO si la moneda base de la compañía es VEF o VES!
            if rec.name in ['VES', 'VEF']:
                company = self.env.company
                if company.currency_id.name in ['VES', 'VEF']:
                    monedas_ext = self.env['res.currency'].search([('name', 'in', ['USD', 'EUR']), ('active', '=', True)])
                    for m in monedas_ext.with_context(self.env.context):
                        m.recuperar_tasas_historicas()
                    continue

            if rec.name not in ['USD', 'EUR', 'VES', 'VEF']:
                continue

            today = fields.Date.context_today(self)
            company_ids = self.env['res.company'].search([])
            channel_id = self.env.ref('account_dual_currency.trm_channel')
            
            # 1. Determinar URL histórica según moneda
            if rec.name in ['USD', 'VES', 'VEF']:
                url = 'https://ve.dolarapi.com/v1/historicos/dolares/oficial'
            elif rec.name == 'EUR':
                url = 'https://ve.dolarapi.com/v1/historicos/euros/oficial'
            else:
                continue
                
            # 2. Consultar historial de tasas
            historical_rates = {}
            try:
                req = requests.get(url, verify=False, timeout=15)
                if req.status_code == 200:
                    data = req.json()
                    for entry in data:
                        fecha_str = entry.get('fecha')
                        promedio = entry.get('promedio')
                        if fecha_str and promedio:
                            historical_rates[fecha_str] = float(promedio)
            except Exception as e:
                _logger.error("Error al obtener histórico de tasas de DolarApi: %s", e)
                continue

            if not historical_rates:
                continue

            # Forzar contexto from_button para indicar que fue una recuperación manual/asistente
            ctx = dict(self.env.context, from_button=True)

            for c in company_ids:
                # Determinar la moneda destino para la tasa
                if rec.name == c.currency_id.name:
                    target_currency = c.currency_id_dif
                else:
                    target_currency = rec

                if not target_currency:
                    continue

                last_rate_rec = self.env['res.currency.rate'].sudo().search([
                    ('currency_id', '=', target_currency.id),
                    ('company_id', '=', c.id)
                ], order='name desc', limit=1)
                
                dates_to_update = []
                if last_rate_rec:
                    last_date = last_rate_rec.name
                    current_date = last_date + timedelta(days=1)
                    max_past_date = today - timedelta(days=30)
                    if current_date < max_past_date:
                        current_date = max_past_date
                    
                    while current_date <= today:
                        dates_to_update.append(current_date)
                        current_date += timedelta(days=1)
                else:
                    dates_to_update.append(today)

                for d in dates_to_update:
                    # 3. Buscar tasa en el historial (retrocediendo hasta 5 días para fines de semana/feriados)
                    rate_val = None
                    for offset in range(5):
                        check_date = d - timedelta(days=offset)
                        check_date_str = check_date.strftime("%Y-%m-%d")
                        if check_date_str in historical_rates:
                            rate_val = historical_rates[check_date_str]
                            break
                    
                    if not rate_val:
                        continue  # Si no hay registro histórico, ignoramos
                    
                    if c.currency_id.name == 'USD':
                        odoo_rate = rate_val
                    else:
                        odoo_rate = 1.0 / rate_val
                    
                    tasa_actual = self.env['res.currency.rate'].sudo().search([
                        ('name', '=', d),
                        ('currency_id', '=', target_currency.id),
                        ('company_id', '=', c.id)
                    ], limit=1)
                    
                    nueva = False
                    if not tasa_actual:
                        self.env['res.currency.rate'].sudo().with_context(ctx).create({
                            'currency_id': target_currency.id,
                            'name': d,
                            'rate': odoo_rate,
                            'company_id': c.id,
                        })
                        nueva = True
                    else:
                        if abs(tasa_actual.rate - odoo_rate) > 0.000001:
                            tasa_actual.sudo().with_context(ctx).write({
                                'rate': odoo_rate
                            })
                            nueva = True

                    if nueva:
                        channel_id.message_post(
                            body="Tasa HISTÓRICA recuperada para %s (%s): %s para la fecha %s." % (
                                target_currency.name, c.name, odoo_rate, d.strftime("%d-%m-%Y")),
                            message_type='notification',
                            subtype_xmlid='mail.mt_comment',
                        )
            if rec.act_productos:
                rec.actualizar_productos()

    @api.model
    def get_trm_systray(self):
        company_id = self.env.company
        
        # Intentar obtener la tasa calculada de la moneda alterna de la compañía
        if hasattr(company_id, 'currency_id_dif') and company_id.currency_id_dif:
            tasa = company_id.currency_id_dif.rate
        else:
            # Fallback en caso de que no esté configurada
            usd_currency = self.env['res.currency'].search([('name', 'in', ['USD', 'US$'])], limit=1)
            ves_currency = self.env['res.currency'].search([('name', 'in', ['VES', 'VEF'])], limit=1)
            
            if not usd_currency or not ves_currency:
                return 1.0
                
            if company_id.currency_id.id == usd_currency.id:
                tasa = ves_currency.rate
            else:
                tasa = usd_currency.rate
            
        if tasa < 1.0 and tasa > 0.0:
            tasa = 1.0 / tasa
            
        return round(tasa, 4) if tasa else 1.0

    # LocVe: promedio ponderado de la tasa BCV del día
    def get_dolar_bcv_promedio(self):
        url = "https://s3.amazonaws.com/dolartoday/data.json"
        response = requests.get(url)
        status_code = response.status_code

        if status_code == 200:
            response = response.json()
            usd = float(response['USD']['transferencia'])
            eur = float(response['EUR']['transferencia'])
            if self.name == 'USD':
                data = usd
            elif self.name == 'EUR':
                data = eur
            else:
                data = False

            return data
        else:
            return False
