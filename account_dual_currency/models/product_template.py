from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class Productos(models.Model):
    _inherit = 'product.template'

    currency_id_dif = fields.Many2one('res.currency', string='Moneda Diferente', compute='_compute_currency_id_dif')

    def _compute_currency_id_dif(self):
        for rec in self:
            rec.currency_id_dif = self.env.company.currency_id_dif.id

    cost_currency_id = fields.Many2one('res.currency', string="Moneda Local", compute='_compute_cost_currency_id')
    uom_name = fields.Char(related='uom_id.name', string="Nombre UoM")

    def _compute_cost_currency_id(self):
        # LocVe: auto-detección de moneda local (moneda base de la empresa)
        for rec in self:
            rec.cost_currency_id = rec.env.company.currency_id.id

    currency_usd_id = fields.Many2one('res.currency', string="Moneda USD", compute='_compute_currencies_strict')
    currency_bs_id = fields.Many2one('res.currency', string="Moneda Bs", compute='_compute_currencies_strict')

    def _compute_currencies_strict(self):
        usd = self.env.ref('base.USD', raise_if_not_found=False) or self.env['res.currency'].search([('name', '=', 'USD')], limit=1)
        vef = self.env.ref('base.VEF', raise_if_not_found=False) or self.env['res.currency'].search([('name', 'in', ('VEF', 'VES'))], limit=1) or self.env.company.currency_id
        for rec in self:
            rec.currency_usd_id = usd.id if usd else False
            rec.currency_bs_id = vef.id if vef else False

    # Campos maestros en USD
    list_price_usd = fields.Float(string="Precio Venta ($)", default=1.0)
    standard_price_usd = fields.Float(string="Costo en Divisa", default=0.0)

    # Sobreescribir list_price y standard_price nativos como calculados
    list_price = fields.Float(
        string='Sales Price',
        compute='_compute_list_price',
        inverse='_inverse_list_price',
        store=True,
        readonly=False
    )
    
    standard_price = fields.Float(
        string='Cost',
        compute='_compute_standard_price',
        inverse='_inverse_standard_price',
        store=True,
        readonly=False
    )

    @api.depends('list_price_usd', 'company_id.currency_id')
    def _compute_list_price(self):
        for rec in self:
            company = rec.company_id or rec.env.company
            if company.currency_id.name == 'USD':
                rec.list_price = rec.list_price_usd
            else:
                tasa = company.currency_id_dif.get_trm_systray() if company.currency_id_dif else 0.0
                rec.list_price = rec.list_price_usd * tasa if tasa > 0 else rec.list_price_usd

    def _inverse_list_price(self):
        for rec in self:
            company = rec.company_id or rec.env.company
            if company.currency_id.name == 'USD':
                val = rec.list_price
            else:
                tasa = company.currency_id_dif.get_trm_systray() if company.currency_id_dif else 0.0
                val = rec.list_price / tasa if tasa > 0 else rec.list_price
            if abs(rec.list_price_usd - val) > 1e-5:
                rec.list_price_usd = val

    @api.depends('standard_price_usd', 'company_id.currency_id')
    def _compute_standard_price(self):
        for rec in self:
            company = rec.company_id or rec.env.company
            if company.currency_id.name == 'USD':
                rec.standard_price = rec.standard_price_usd
            else:
                tasa = company.currency_id_dif.get_trm_systray() if company.currency_id_dif else 0.0
                rec.standard_price = rec.standard_price_usd * tasa if tasa > 0 else rec.standard_price_usd

    def _inverse_standard_price(self):
        for rec in self:
            company = rec.company_id or rec.env.company
            if company.currency_id.name == 'USD':
                val = rec.standard_price
            else:
                tasa = company.currency_id_dif.get_trm_systray() if company.currency_id_dif else 0.0
                val = rec.standard_price / tasa if tasa > 0 else rec.standard_price
            if abs(rec.standard_price_usd - val) > 1e-5:
                rec.standard_price_usd = val

    # Campos secundarios calculados para visualización (siempre en Bs)
    list_price_bs = fields.Monetary(
        string='Precio Venta (Bs.)',
        currency_field='currency_bs_id',
        compute='_compute_list_price_bs', store=True, readonly=False
    )

    standard_price_bs = fields.Monetary(
        string="Costo en Moneda Local", 
        compute='_compute_standard_price_bs', 
        currency_field='currency_bs_id'
    )

    @api.depends('list_price_usd', 'company_id.currency_id')
    def _compute_list_price_bs(self):
        for rec in self:
            company = rec.company_id or rec.env.company
            tasa = company.currency_id_dif.get_trm_systray() if company.currency_id_dif else 0.0
            rec.list_price_bs = rec.list_price_usd * tasa if tasa > 0 else 0.0

    @api.depends('standard_price_usd', 'company_id.currency_id')
    def _compute_standard_price_bs(self):
        for rec in self:
            company = rec.company_id or rec.env.company
            tasa = company.currency_id_dif.get_trm_systray() if company.currency_id_dif else 0.0
            rec.standard_price_bs = rec.standard_price_usd * tasa if tasa > 0 else 0.0

    price_with_tax_info = fields.Char(compute='_compute_price_with_tax_info')
    price_with_tax_bs = fields.Char(compute='_compute_price_with_tax_bs')

    @api.depends('list_price_usd', 'list_price_bs', 'taxes_id')
    def _compute_price_with_tax_info(self):
        for rec in self:
            total_usd = rec.list_price_usd
            total_bs = rec.list_price_bs
            if rec.taxes_id:
                try:
                    res_usd = rec.taxes_id.compute_all(rec.list_price_usd, quantity=1, product=rec)
                    total_usd = res_usd['total_included']
                    res_bs = rec.taxes_id.compute_all(rec.list_price_bs, quantity=1, product=rec)
                    total_bs = res_bs['total_included']
                except Exception:
                    pass
            rec.price_with_tax_info = f"(= $ {total_usd:,.2f} / Bs. {total_bs:,.2f} impuestos incluidos)".replace(',', 'X').replace('.', ',').replace('X', '.')

    @api.depends('list_price_bs', 'taxes_id')
    def _compute_price_with_tax_bs(self):
        for rec in self:
            total_bs = rec.list_price_bs
            if rec.taxes_id:
                try:
                    res_bs = rec.taxes_id.compute_all(rec.list_price_bs, quantity=1, product=rec)
                    total_bs = res_bs['total_included']
                except Exception:
                    pass
            rec.price_with_tax_bs = f"(= Bs. {total_bs:,.2f} impuestos incluidos)".replace(',', 'X').replace('.', ',').replace('X', '.')

    costo_reposicion_usd = fields.Monetary(string="Costo Reposición Alterno", currency_field='currency_id_dif')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'list_price_usd' in vals and 'list_price' not in vals:
                company = self.env.company
                if company.currency_id.name == 'USD':
                    vals['list_price'] = vals['list_price_usd']
                else:
                    tasa = company.currency_id_dif.get_trm_systray() if company.currency_id_dif else 0.0
                    vals['list_price'] = vals['list_price_usd'] * tasa if tasa > 0 else vals['list_price_usd']
            if 'standard_price_usd' in vals and 'standard_price' not in vals:
                company = self.env.company
                if company.currency_id.name == 'USD':
                    vals['standard_price'] = vals['standard_price_usd']
                else:
                    tasa = company.currency_id_dif.get_trm_systray() if company.currency_id_dif else 0.0
                    vals['standard_price'] = vals['standard_price_usd'] * tasa if tasa > 0 else vals['standard_price_usd']
        return super().create(vals_list)

    def write(self, vals):
        if 'list_price_usd' in vals and 'list_price' not in vals:
            company = self.env.company
            if company.currency_id.name == 'USD':
                vals['list_price'] = vals['list_price_usd']
            else:
                tasa = company.currency_id_dif.get_trm_systray() if company.currency_id_dif else 0.0
                vals['list_price'] = vals['list_price_usd'] * tasa if tasa > 0 else vals['list_price_usd']
        if 'standard_price_usd' in vals and 'standard_price' not in vals:
            company = self.env.company
            if company.currency_id.name == 'USD':
                vals['standard_price'] = vals['standard_price_usd']
            else:
                tasa = company.currency_id_dif.get_trm_systray() if company.currency_id_dif else 0.0
                vals['standard_price'] = vals['standard_price_usd'] * tasa if tasa > 0 else vals['standard_price_usd']
        return super().write(vals)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    currency_id_dif = fields.Many2one(related='product_tmpl_id.currency_id_dif', readonly=True)
    cost_currency_id = fields.Many2one(related='product_tmpl_id.cost_currency_id', readonly=True)
    currency_usd_id = fields.Many2one(related='product_tmpl_id.currency_usd_id', readonly=True)
    currency_bs_id = fields.Many2one(related='product_tmpl_id.currency_bs_id', readonly=True)
    list_price_usd = fields.Float(related='product_tmpl_id.list_price_usd', readonly=False)
    standard_price_usd = fields.Float(related='product_tmpl_id.standard_price_usd', readonly=False)
    costo_reposicion_usd = fields.Monetary(related='product_tmpl_id.costo_reposicion_usd', readonly=False, currency_field='currency_usd_id')
    standard_price_bs = fields.Monetary(related='product_tmpl_id.standard_price_bs', readonly=False, currency_field='currency_bs_id')
