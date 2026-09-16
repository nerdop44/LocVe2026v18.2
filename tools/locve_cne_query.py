# -*- coding: utf-8 -*-
# LocVe — Módulo de consulta al CNE (Consejo Nacional Electoral) de Venezuela
# Autor: Ing. Nerdo Jose Pulido Aguirre
#
# Obtiene el nombre de un elector venezolano a partir de su número de cédula
# consultando directamente la página oficial del CNE.
# La consulta está controlada por el parámetro de configuración
# 'l10n_ve_contact.cne_query_enabled' para respetar la privacidad y la
# disponibilidad de la red del cliente.

import logging
import requests
from bs4 import BeautifulSoup
from odoo import _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


def get_default_name_by_vat(self, prefix_vat, vat):
    """Retorna el nombre del elector por su cédula consultando el CNE.

    Args:
        prefix_vat (str): Prefijo del RIF/Cédula (V, E, J, G, P, C).
        vat (str): Número de cédula/RIF (solo dígitos).

    Returns:
        tuple: (nombre: str, encontrado: bool)
               Si hay error de conexión o no se encuentra, retorna ('', False).
    """
    URL = (
        "http://www.cne.gov.ve/web/registro_electoral/ce.php?nacionalidad="
        + str(prefix_vat)
        + "&cedula="
        + str(vat)
    )
    try:
        response = requests.get(URL, timeout=5)
        soup = BeautifulSoup(response.text, "html.parser")
        info_table = soup.find_all("tr")
        for row in info_table:
            cne_info = row.find("td")
            for data in cne_info.find_all("b"):
                if not data.find("font"):
                    info = data.text.split(":")
                    if not info[0] == "DATOS DEL ELECTOR":
                        name = info.pop(0)
                        return (name, True)
    except Exception as e:
        _logger.warning("LocVe CNE Query: No se pudo obtener datos del CNE — %s", e)
        return ('', False)
    return ('', False)
