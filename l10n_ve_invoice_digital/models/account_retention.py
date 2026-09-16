# -*- coding: utf-8 -*-
# Remake ING. Nerdo José Pulido Aguirre - Localización Venezolana (LocVe)

from odoo import models, api, fields, _
from odoo.exceptions import UserError, ValidationError
from pytz import timezone
import logging
import requests
import json
import re
import time as time_mod

_logger = logging.getLogger(__name__)


class EndPoints():
    BASE_ENDPOINTS = {
        "emision": "/api/Emision",
        "ultimo_documento": "/api/UltimoDocumento",
        "consulta_numeraciones": "/api/ConsultaNumeraciones",
    }


class AccountRetention(models.Model):
    _inherit = 'account.retention'

    is_digitalized = fields.Boolean(string="Digitalizado TFHKA", default=False, copy=False, tracking=True)
    show_digital_retention_iva = fields.Boolean(string="Mostrar Retención Digital IVA", compute="_compute_visibility_button", copy=False)
    show_digital_retention_islr = fields.Boolean(string="Mostrar Retención Digital ISLR", compute="_compute_visibility_button", copy=False)
    control_number_tfhka = fields.Char(string="Número Control TFHKA", copy=False)

    def get_base_url(self):
        if self.company_id.url_tfhka:
            return self.company_id.url_tfhka.rstrip("/")
        raise UserError(_("La URL de TFHKA no está configurada en los ajustes de la empresa."))

    def get_token(self):
        if self.company_id.token_auth_tfhka:
            return self.company_id.token_auth_tfhka
        raise ValidationError(_("Error de configuración: El token de autenticación TFHKA está vacío."))

    def call_tfhka_api(self, endpoint_key, payload, _retry=False):
        base_url = self.get_base_url()
        endpoint = EndPoints.BASE_ENDPOINTS.get(endpoint_key)

        if not endpoint:
            raise UserError(_("Endpoint '%(endpoint_key)s' no está definido.") % {'endpoint_key': endpoint_key})

        url = f"{base_url}{endpoint}"
        headers = {"Authorization": f"Bearer {self.get_token()}"}
        time_mod.sleep(2)

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=20)
        
            if response.status_code == 200:
                data = response.json()
                if str(data.get("codigo")) == "200":
                    return data
                elif str(data.get("codigo")) == "203" and data.get("validaciones") and endpoint_key == "ultimo_documento":
                    return 0
                else:
                    _logger.error(_("Error en la respuesta de API TFHKA: %(message)s \n%(validation)s") % {'message': data.get('mensaje'), 'validation': data.get('validaciones')})
                    raise UserError(_("Error en la API de TFHKA: %(message)s \n%(validation)s") % {'message': data.get('mensaje'), 'validation': data.get('validaciones')})
            if response.status_code == 401:
                if not _retry:
                    _logger.error(_("Error 401: Token inválido o expirado. Regenerando token..."))
                    self.company_id.generate_token_tfhka()
                    return self.call_tfhka_api(endpoint_key, payload, _retry=True)
                else:
                    raise UserError(_("Token TFHKA expirado y no se pudo renovar automáticamente."))
            else:
                _logger.error(_("Error HTTP %(status_code)s: %(text)s") % {'status_code': response.status_code, 'text': response.text})
                raise UserError(_("Error HTTP %(status_code)s en TFHKA: %(text)s") % {'status_code': response.status_code, 'text': response.text})
        except requests.exceptions.RequestException as e:
            _logger.error(_("Error conectando con la API de TFHKA: %(error)s") % {'error': e})
            raise UserError(_("Error conectando con la API de TFHKA: %(error)s") % {'error': e})

    def generate_document_digital(self):
        self.ensure_one()
        if not self.company_id.invoice_digital_tfhka:
            return
        if self.is_digitalized:
            raise UserError(_("El documento ya ha sido digitalizado previamente."))
        
        document_type = self.env.context.get('document_type', '05')
        self.query_numbering()
        last_num = self.get_last_document_number(document_type)
        document_number = last_num + 1
        
        document_number_str = str(document_number)
        validation_sequence = self.env.context.get('account_retention_alert', False)

        self.generate_document_data(document_number_str, document_type, validation_sequence)
        return True

    def generate_document_data(self, document_number, document_type, validation_sequence):
        document_identification = self.get_document_identification(document_type, document_number)
        subject_retention = self.get_subject_retention()
        total_retention = self.get_total_retention(document_type)
        retention_details = self.get_retention_details(document_type)

        payload = {
            "DocumentoElectronico": {
                "Encabezado": {
                    "IdentificacionDocumento": document_identification,
                    "SujetoRetenido": subject_retention,
                    "TotalesRetencion": total_retention,
                },
                "DetallesRetencion": retention_details,
            }
        }

        if self.esNegativo:
            payload["DocumentoElectronico"]["Encabezado"]["TotalesRetencion"]["EsNegativo"] = True

        response = self.call_tfhka_api("emision", payload)

        if response:
            self.is_digitalized = True
            resultado = response.get("resultado", {})
            if isinstance(resultado, dict):
                self.control_number_tfhka = resultado.get("numeroControl")
            emission_date = fields.Datetime.now().strftime("%d/%m/%Y")
            self.message_post(
                body=_("Comprobante de Retención digitalizado exitosamente en TFHKA el %(date)s") % {'date': emission_date},
                message_type='comment',
            )
            return

    def get_last_document_number(self, document_type):
        payload = {
            "serie": "",
            "tipoDocumento": document_type,
        }
        response = self.call_tfhka_api("ultimo_documento", payload)
        
        if response == 0:
            return 0
        else:
            if isinstance(response, dict) and "numeroDocumento" in response:
                return int(response["numeroDocumento"]) if response["numeroDocumento"] else 0
            return int(response) if isinstance(response, (int, str)) and str(response).isdigit() else 0

    def query_numbering(self, series=""):
        payload = {
            "serie": series,
            "tipoDocumento": "",
            "prefix": ""
        }
        response = self.call_tfhka_api("consulta_numeraciones", payload)

        if response:
            approves = False
            for numbering in response.get("numeraciones", []):
                start_number = numbering.get("correlativo", 0)
                end_number = numbering.get("hasta", 0)
                if int(start_number) < int(end_number):
                    approves = True
                    break

            if approves:
                return

            raise UserError(_("El rango de numeración digital TFHKA está agotado."))

    def get_document_identification(self, document_type, document_number):
        self.ensure_one()
        now = fields.Datetime.now()
        user_tz_name = self.env.user.tz or 'America/Caracas'
        user_tz = timezone(user_tz_name)
        emission_time = now.astimezone(user_tz).strftime("%I:%M:%S %p").lower()
        emission_date = (self.date or now.date()).strftime("%d/%m/%Y")

        doc_id = {
            "tipoDocumento": document_type,
            "numeroDocumento": document_number,
            "numeroFacturaAfectada": "",
            "fechaEmision": emission_date,
            "horaEmision": emission_time,
            "serie": "",
            "sucursal": "",
            "tipoDeVenta": "Interna",
            "moneda": "VES",
        }

        if self.esNegativo and self.original_retention_id:
            orig = self.original_retention_id
            orig_inv = orig.retention_line_ids[:1].move_id if orig.retention_line_ids else False
            if orig_inv:
                raw_inv_name = orig_inv.name or ""
                doc_id["numeroFacturaAfectada"] = re.sub(r'[^0-9]', '', raw_inv_name)
                doc_id["comentarioFacturaAfectada"] = "Ajuste negativo por reverso de retención"

        return doc_id

    def get_subject_retention(self):
        partner = self.partner_id
        if not partner:
            raise UserError(_("El comprobante de retención debe tener un Proveedor/Cliente asignado."))
        
        vat = partner.vat or ""
        vat_clean = vat.upper().replace("-", "").replace(".", "").strip()
        if not vat_clean:
            raise UserError(_("El RIF del Proveedor/Cliente no puede estar vacío para digitalización."))

        tipo_id = vat_clean[0] if vat_clean[0].isalpha() else "J"
        num_id = vat_clean[1:] if vat_clean[0].isalpha() else vat_clean

        phone = partner.mobile or partner.phone or "02120000000"
        email = partner.email or "proveedor@empresa.com"
        country_code = partner.country_id.code or "VE"

        return {
            "tipoIdentificacion": tipo_id,
            "numeroIdentificacion": num_id,
            "razonSocial": partner.name,
            "direccion": partner.street or partner.city or "Caracas, Venezuela",
            "pais": country_code,
            "telefono": [phone],
            "notificar": "Si",
            "correo": [email],
        }

    def get_total_retention(self, document_type):
        self.ensure_one()
        total_inv = getattr(self, 'total_invoice_amount', 0.0)
        total_ret = getattr(self, 'total_retention_amount', 0.0)
        total_iva = getattr(self, 'total_iva_amount', 0.0)
        raw_number = self.number or ""
        numero_comp = re.sub(r'[^0-9A-Za-z]', '', raw_number) if raw_number else "NA"

        retention_data = {
            "totalBaseImponible": str(round(abs(total_inv), 2)),
            "numeroCompRetencion": numero_comp,
            "fechaEmisionCR": (self.date or fields.Date.today()).strftime("%d/%m/%Y"),
        }
        if document_type != "05":
            retention_data["tipoComprobante"] = "1"
        if document_type == "05":
            retention_data["totalRetenido"] = str(round(abs(total_ret), 2))
            retention_data["totalIVA"] = str(round(abs(total_iva), 2))
        else:
            retention_data["TotalISRL"] = str(round(abs(total_ret), 2))

        if self.esNegativo:
            retention_data["esNegativo"] = True

        return retention_data

    def get_retention_details(self, document_type):
        retention_details = []
        counter = 1
        for line in self.retention_line_ids:
            raw_name = line.move_id.name if line.move_id else ""
            doc_num = re.sub(r'[^0-9]', '', raw_name)[-10:] if raw_name else ""
            raw_ctrl = getattr(line.move_id, 'correlative', '') or ""
            control_num = re.sub(r'[^0-9]', '', raw_ctrl)[-10:] if raw_ctrl else ""
            retention_data = {
                "numeroLinea": str(counter).zfill(4),
                "fechaDocumento": (line.date_accounting or fields.Date.today()).strftime("%d/%m/%Y"),
                "tipoDocumento": "01",
                "numeroDocumento": doc_num,
                "numeroControl": control_num,
                "montoTotal": str(round(getattr(line, 'invoice_total', 0.0), 2)),
                "baseImponible": str(round(getattr(line, 'invoice_amount', 0.0), 2)),
                "moneda": "VES",
                "retenido": str(round(abs(getattr(line, 'retention_amount', 0.0)), 2)),
            }

            if document_type == "05":
                retention_data["montoIVA"] = str(round(getattr(line, 'iva_amount', 0.0), 2))
                retention_data["porcentaje"] = str(round(getattr(line, 'aliquot', 0.0), 2))
                retention_data["porcentajeRetencion"] = str(round(getattr(line, 'retention_percentage', 75.0), 2))
                retention_data["retenidoIVA"] = str(round(getattr(line, 'retention_amount', 0.0), 2))

            if document_type == "06":
                code = getattr(line, 'code', False)
                if code:
                    retention_data["CodigoConcepto"] = str(code).zfill(3)
                retention_data["porcentaje"] = str(round(getattr(line, 'aliquot', 0.0), 2))
                retention_data["porcentajeRetencion"] = str(round(getattr(line, 'retention_percentage', 100.0), 2))

            retention_details.append(retention_data)
            counter += 1

        return retention_details

    def _get_tfhka_currency(self):
        currency = self.company_id.currency_id
        if not currency:
            return "VES"
        name = currency.name.upper()
        tfhka_map = {"VEF": "VES", "VES": "VES", "USD": "USD"}
        return tfhka_map.get(name, name)

    def action_send_retention_email(self):
        """Envía el comprobante de retención por correo electrónico."""
        self.ensure_one()
        if not self.company_id.invoice_digital_tfhka:
            raise UserError(_("La facturación digital TFHKA no está habilitada para esta empresa."))

        template = self.env.ref(
            'l10n_ve_invoice_digital.email_template_retention',
            raise_if_not_found=False,
        ) or self.env['mail.template'].sudo().search([
            ('model', '=', 'account.retention'),
            ('name', 'ilike', 'retencion'),
        ], limit=1)
        if not template:
            raise UserError(_("No se encontró la plantilla de correo para retenciones. "
                              "Por favor, configure la plantilla 'email_template_retention' "
                              "en el módulo l10n_ve_invoice_digital."))

        email_to = self.partner_id.email if self.partner_id else False
        if not email_to:
            raise UserError(_("El cliente no tiene correo electrónico configurado."))

        mail_values = {
            'subject': template.subject or 'Comprobante de Retención',
            'email_to': email_to,
            'model': 'account.retention',
            'res_id': self.id,
        }
        mail = self.env['mail.mail'].create(mail_values)
        mail.send(raise_exception=True)
        _logger.info("Retención %s: correo enviado a %s", self.number, email_to)

    @api.depends('state', 'is_digitalized')
    def _compute_visibility_button(self):
        for record in self:
            record.show_digital_retention_iva = True
            record.show_digital_retention_islr = True
            if record.state in ('emitted', 'posted') and not record.is_digitalized and record.company_id.invoice_digital_tfhka:
                record.show_digital_retention_iva = False
                record.show_digital_retention_islr = False
