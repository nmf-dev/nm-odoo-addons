from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    nm_ai_api_key = fields.Char(
        string="API Key",
        config_parameter="nm_report_ai_editor.api_key",
    )
    nm_ai_model = fields.Char(
        string="AI Model",
        config_parameter="nm_report_ai_editor.model",
        default="claude-sonnet-5-5",
    )
    nm_ai_timeout = fields.Integer(
        string="Timeout (s)",
        config_parameter="nm_report_ai_editor.timeout",
        default=60,
    )