{
    'name': 'Soporte y Ayuda — Extensión Contable',
    'version': '18.0.1.0.0',
    'category': 'Services/Helpdesk',
    'summary': 'Extensión contable de Soporte y Ayuda para módulos con contabilidad',
    'description': """\
**Soporte y Ayuda — Extensión Contable** es una extensión opcional del
módulo *Soporte y Ayuda* que se activa cuando el cliente utiliza
contabilidad en Odoo.

¿Para qué sirve?
=================
Proporciona asistencia técnica especializada para los módulos
contables (`account.tax`, `account.move`, `account.move.line` y
`account.payment`) integrados en el sistema. Permite que las
solicitudes de soporte relacionadas con contabilidad sean atendidas
con pleno contexto respecto a las operaciones y estados de los
documentos fiscales.

Características
================
- Integración con el sistema de tickets de **Soporte y Ayuda**.
- Seguimiento de incidencias sobre documentos contables.
- Compatibilidad con entornos multi-empresa.

Este módulo se instala de forma automática al estar presente el
aplicativo de Contabilidad. No realiza cambios en la operación
contable ni en los datos existentes.
""",
    'author': 'Ing. Nerdo Jose Pulido Aguirre',
    'depends': ['soportehelp', 'account'],
    'data': [],
    'installable': True,
    'application': False,
    'auto_install': True,
    'license': 'OPL-1',
}