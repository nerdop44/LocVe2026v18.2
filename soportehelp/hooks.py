import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Ejecutado automáticamente al finalizar la instalación del módulo soportehelp.

    Configura la URL por defecto del backend (https://of.venrides.com) y
    dispara el auto-registro hacia ControlDes para que el cliente quede en
    estado 'pending' (esperando aprobación) de forma inmediata.
    """
    _logger.info('Iniciando post_init_hook de soportehelp...')
    try:
        config = env['soportehelp.config'].sudo()._get_or_create()
        if not config.service_url:
            config.service_url = 'https://of.venrides.com'
        if config.registration_state == 'not_registered':
            config.action_register()
            _logger.info('Auto-registro de soportehelp enviado exitosamente a %s', config.service_url)
    except Exception as e:
        _logger.warning('No se pudo completar el auto-registro en post_init_hook: %s', e)
