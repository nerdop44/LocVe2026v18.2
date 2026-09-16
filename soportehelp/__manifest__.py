{
    'name': 'Soporte y Ayuda',
    'version': '18.0.1.2.0',
    'category': 'Services/Helpdesk',
    'summary': 'Soporte y ayuda mediante tickets para sus módulos de Odoo',
    'description': """\
**Soporte y Ayuda** es el canal oficial de soporte técnico para los módulos de Odoo instalados en su empresa.

¿Para qué sirve?
=================
- Crear y dar seguimiento a **solicitudes de soporte** mediante tickets.
- Consultar el estado de cada solicitud: abierta, en proceso, respondida o cerrada.
- Comunicarse con el equipo de soporte de forma ordenada y con historial.
- Recibir asistencia ante dudas, errores o configuraciones de los módulos.

¿Cómo se recibe soporte?
========================
1. Vaya al menú **Soporte y Ayuda** (panel superior).
2. Seleccione **Nuevo Ticket**.
3. Complete la solicitud indicando el asunto y la descripción del problema.
4. Haga clic en **Enviar Ticket**. El equipo de soporte recibirá su solicitud.
5. Desde **Mis Tickets** podrá ver la respuesta y continuar el diálogo hasta
   que su solicitud quede resuelta y cerrada.

Toda la información enviada se usa únicamente para la atención de su solicitud
de soporte técnico. La instalación del módulo es transparente y no interfiere
con el uso normal de su sistema.

Para cualquier duda sobre el uso de este módulo, contacte al soporte técnico
mediante los mismos tickets de **Soporte y Ayuda**.
""",
    'author': 'ING. Nerdo José Pulido Aguirre',
    'website': '',
    'depends': ['base', 'mail'],

    'data': [
        'security/ir.model.access.csv',
        'views/menus.xml',
        'views/config_views.xml',
        'views/history_views.xml',
        'views/ticket_views.xml',
        'data/cron.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'OPL-1',
}