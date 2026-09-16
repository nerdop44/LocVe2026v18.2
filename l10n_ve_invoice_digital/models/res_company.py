# -*- coding: utf-8 -*-
# Remake ING. Nerdo José Pulido Aguirre - Localización Venezolana (LocVe)

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
import requests
import logging

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"
    
    username_tfhka = fields.Char(string="Usuario TFHKA")
    password_tfhka = fields.Char(string="Contraseña TFHKA")
    url_tfhka = fields.Char(string="URL API TFHKA")
    token_auth_tfhka = fields.Char(string="Token de Autenticacion TFHKA")
    invoice_digital_tfhka = fields.Boolean(string="Facturación Digital TFHKA Activa")
    sequence_validation_tfhka = fields.Boolean(string="Validar Secuencias con TFHKA", default=True)
    ocultar_forma_libre_digital = fields.Boolean(string="Ocultar impresión Forma Libre", help="Oculta la opción de imprimir en Forma Libre cuando la facturación digital TFHKA está activa.")

    def _register_hook(self):
        super()._register_hook()
        try:
            self.env.cr.execute("""
                ALTER TABLE res_company 
                ADD COLUMN IF NOT EXISTS username_tfhka VARCHAR,
                ADD COLUMN IF NOT EXISTS password_tfhka VARCHAR,
                ADD COLUMN IF NOT EXISTS url_tfhka VARCHAR,
                ADD COLUMN IF NOT EXISTS token_auth_tfhka VARCHAR,
                ADD COLUMN IF NOT EXISTS invoice_digital_tfhka BOOLEAN DEFAULT FALSE,
                ADD COLUMN IF NOT EXISTS sequence_validation_tfhka BOOLEAN DEFAULT TRUE,
                ADD COLUMN IF NOT EXISTS ocultar_forma_libre_digital BOOLEAN DEFAULT FALSE;
            """)
        except Exception as e:
            _logger.warning("Error asegurando columnas res_company en l10n_ve_invoice_digital: %s", e)

    
    def generate_token_tfhka(self):
        self.ensure_one()
        self._validate_tfhka_credentials()

        url = self.url_tfhka.rstrip("/") + "/Autenticacion"
        payload = {
            "usuario": self.username_tfhka,
            "clave": self.password_tfhka
        }

        try:
            response = requests.post(url, json=payload, timeout=15)
            self._handle_tfhka_response(response)
        except requests.exceptions.RequestException as e:
            _logger.error(f"Error conectando a la API de TFHKA (LocVe): {e}")
            raise ValidationError(_("Error conectando a la API de TFHKA (LocVe): %s") % e)

    def _validate_tfhka_credentials(self):
        if not self.username_tfhka:
            raise UserError(_("Debe registrar el Usuario para TFHKA."))
        if not self.password_tfhka:
            raise UserError(_("Debe registrar la Contraseña para TFHKA."))
        if not self.url_tfhka:
            raise UserError(_("Debe registrar la URL para TFHKA."))
        _logger.info("Credenciales de TFHKA validadas exitosamente (LocVe).")

    def _handle_tfhka_response(self, response):
        try:
            data = response.json()
        except Exception:
            _logger.error(f"Error decodificando respuesta JSON: {response.text}")
            raise ValidationError(_("Error al procesar la respuesta de la API de TFHKA."))

        if response.status_code == 200 and (data.get("codigo") == 200 or data.get("codigo") == "200"):
            self._process_tfhka_response_data(data)
        else:
            self._handle_tfhka_http_error(response, data)

    def _process_tfhka_response_data(self, data):
        if "token" in data:
            self.token_auth_tfhka = data["token"]
            _logger.info("Token de TFHKA generado exitosamente en LocVe.")
        else:
            _logger.error(f"El campo 'token' no se encuentra en la respuesta: {data}")
            raise ValidationError(_("La respuesta de la API de TFHKA no contiene un 'token' válido."))

    def _handle_tfhka_http_error(self, response, data):
        message = data.get("mensaje")
        if message:
            raise ValidationError(_("Error de autenticación TFHKA: %(message)s") % {'message': message})
        else:
            raise ValidationError(_("Error en la API de TFHKA: %(status_code)s") % {'status_code': response.status_code})
