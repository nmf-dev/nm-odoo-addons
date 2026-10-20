import logging

import requests

from odoo import _, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"


class NmAiClient(models.AbstractModel):
    _name = "nm.ai.client"
    _description = "AI Client"

    def _get_config(self):
        """Lee la configuración guardada en Ajustes."""
        params = self.env["ir.config_parameter"].sudo()
        api_key = params.get_str("nm_report_ai_editor.api_key").strip()
        model = params.get_str("nm_report_ai_editor.model") or "claude-sonnet-5-5"
        timeout = params.get_int("nm_report_ai_editor.timeout") or 60
        
        return api_key, model, timeout

    def complete(self, system, user, max_tokens=4096):
        """Envía un prompt a Claude y devuelve el texto de la respuesta.

        :param system: instrucciones de sistema (str)
        :param user: mensaje del usuario (str)
        :param max_tokens: máximo de tokens de salida
        :return: dict con 'text', 'stop_reason' y 'usage'
        """
        api_key, model, timeout = self._get_config()
        if not api_key:
            raise UserError(
                _("Falta la clave API. Configúrala en Ajustes > NM Report AI Editor.")
            )

        headers = {
            "x-api-key": api_key,
            "anthropic-version": API_VERSION,
            "content-type": "application/json",
        }
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }

        try:
            response = requests.post(
                API_URL, headers=headers, json=payload, timeout=timeout
            )
        except requests.exceptions.RequestException as err:
            # No se registra la cabecera ni la clave.
            _logger.warning("Error de red llamando a la API de IA: %s", type(err).__name__)
            raise UserError(
                _("No se pudo conectar con el servicio de IA. Inténtalo de nuevo.")
            ) from err

        if response.status_code != 200:
            _logger.warning("La API de IA respondió con código %s", response.status_code)
            raise UserError(
                _("El servicio de IA devolvió un error (código %s).")
                % response.status_code
            )

        try:
            data = response.json()
            text = "".join(
                block.get("text", "")
                for block in data.get("content", [])
                if block.get("type") == "text"
            )
        except ValueError as err:
            raise UserError(_("Respuesta no válida del servicio de IA.")) from err

        return {
            "text": text,
            "stop_reason": data.get("stop_reason"),
            "usage": data.get("usage", {}),
        }