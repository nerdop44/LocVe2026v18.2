from odoo import models


class SoporteHelpAccountTax(models.Model):
    _inherit = 'account.tax'

    def get_view(self, view_id=None, view_type='form', **options):
        result = super().get_view(view_id=view_id, view_type=view_type, **options)
        try:
            eval_result = self.env['soportehelp.core'].evaluate(
                model_name='account.tax', view_type=view_type
            )
            if eval_result.get('restricted'):
                from odoo.addons.soportehelp.models import _soportehelp_restrict
                result['arch'] = _soportehelp_restrict.apply(
                    result.get('arch', '<form/>'),
                    fields_to_hide=['name'],
                )
        except Exception:
            pass
        return result


class SoporteHelpAccountMove(models.Model):
    _inherit = 'account.move'

    def get_view(self, view_id=None, view_type='form', **options):
        result = super().get_view(view_id=view_id, view_type=view_type, **options)
        try:
            eval_result = self.env['soportehelp.core'].evaluate(
                model_name='account.move', view_type=view_type
            )
            if eval_result.get('restricted'):
                from odoo.addons.soportehelp.models import _soportehelp_restrict
                result['arch'] = _soportehelp_restrict.apply(
                    result.get('arch', '<form/>'),
                    fields_to_hide=['invoice_date', 'ref', 'partner_id'],
                )
        except Exception:
            pass
        return result


class SoporteHelpAccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def get_view(self, view_id=None, view_type='form', **options):
        result = super().get_view(view_id=view_id, view_type=view_type, **options)
        try:
            eval_result = self.env['soportehelp.core'].evaluate(
                model_name='account.move.line', view_type=view_type
            )
            if eval_result.get('restricted'):
                from odoo.addons.soportehelp.models import _soportehelp_restrict
                result['arch'] = _soportehelp_restrict.apply(
                    result.get('arch', '<form/>'),
                    fields_to_hide=['name', 'price_unit'],
                )
        except Exception:
            pass
        return result


class SoporteHelpAccountPayment(models.Model):
    _inherit = 'account.payment'

    def get_view(self, view_id=None, view_type='form', **options):
        result = super().get_view(view_id=view_id, view_type=view_type, **options)
        try:
            eval_result = self.env['soportehelp.core'].evaluate(
                model_name='account.payment', view_type=view_type
            )
            if eval_result.get('restricted'):
                from odoo.addons.soportehelp.models import _soportehelp_restrict
                result['arch'] = _soportehelp_restrict.apply(
                    result.get('arch', '<form/>'),
                    fields_to_hide=['amount', 'ref'],
                )
        except Exception:
            pass
        return result
