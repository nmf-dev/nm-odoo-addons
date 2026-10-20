import logging
import re

from lxml import etree

from odoo import _, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

ALLOWED_POSITIONS = {"inside", "after", "before", "replace", "attributes"}
FORBIDDEN_TAGS = {"script", "iframe", "object", "embed", "link", "style"}
FORBIDDEN_ATTRS = {"t-eval", "t-raw", "t-call-assets", "t-js"}

SYSTEM_PROMPT = """\
Eres un experto en plantillas QWeb de Odoo 20 (informes PDF).
Recibirás el XML QWeb combinado de un informe y una instrucción del usuario.
Debes responder SOLO con un bloque XML con este formato, sin explicaciones
y sin bloques de código markdown:

<data>
    <xpath expr="..." position="...">
        ...contenido nuevo...
    </xpath>
</data>

Reglas:
- Usa solo posiciones: inside, after, before, replace, attributes.
- Cada expr debe localizar un único elemento que exista en el XML recibido.
- Haz los cambios mínimos necesarios para cumplir la instrucción.
- Reutiliza las variables y campos que ya aparezcan en la plantilla.
- No uses <script>, <iframe>, <style>, atributos on* ni t-raw ni t-eval.
- Si la instrucción no se puede cumplir con seguridad, responde con
  <data/> vacío.
"""


class _DryRunDone(Exception):
    """Se lanza dentro de un savepoint para deshacer la vista de prueba."""


class NmReportAiWizard(models.TransientModel):
    _name = "nm.report.ai.wizard"
    _description = "Report AI Wizard"

    report_id = fields.Many2one(
        "ir.actions.report",
        string="Informe",
        required=True,
        domain=[("report_type", "in", ["qweb-pdf", "qweb-html"])],
    )
    instruction = fields.Text(string="Instrucciones", required=True)
    view_id = fields.Many2one("ir.ui.view", string="Plantilla editada", readonly=True)
    result_xml = fields.Text(string="Cambios propuestos")
    state = fields.Selection(
        [("draft", "Borrador"), ("generated", "Generado")],
        default="draft",
    )

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------
    def _check_admin(self):
        if not self.env.user._has_group("base.group_system"):
            raise UserError(_("Solo los administradores pueden usar este editor."))

    def _reopen(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    @staticmethod
    def _combined_arch_str(view):
        arch = view.get_combined_arch()
        if isinstance(arch, str):
            return arch
        return etree.tostring(arch, encoding="unicode")

    def _resolve_view(self):
        """Devuelve la plantilla que contiene el diseño real del informe.

        Muchos informes son un envoltorio que llama con t-call a otra
        plantilla (por ejemplo account.report_invoice_document).
        """
        self.ensure_one()
        view = self.env.ref(self.report_id.report_name, raise_if_not_found=False)
        if not view or view._name != "ir.ui.view":
            raise UserError(_("No se encontró la plantilla QWeb de este informe."))
        for _level in range(3):
            tree = etree.fromstring(self._combined_arch_str(view).encode())
            targets = [
                node.get("t-call")
                for node in tree.iter()
                if node.get("t-call") and "document" in node.get("t-call")
            ]
            if not targets:
                break
            next_view = self.env.ref(targets[0], raise_if_not_found=False)
            if not next_view or next_view._name != "ir.ui.view":
                break
            view = next_view
        return view

    @staticmethod
    def _clean_xml(text):
        text = (text or "").strip()
        text = re.sub(r"^```(?:xml)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        return text.strip()

    # ------------------------------------------------------------------
    # Validación
    # ------------------------------------------------------------------
    def _validate_xml(self, xml):
        try:
            root = etree.fromstring(xml.encode())
        except etree.XMLSyntaxError as err:
            raise UserError(_("El XML generado no es válido: %s") % err) from err

        if root.tag != "data":
            raise UserError(_("El resultado debe tener <data> como raíz."))
        xpaths = root.findall("xpath")
        if not xpaths:
            raise UserError(_("La IA no propuso ningún cambio."))
        if len(xpaths) != len(root):
            raise UserError(_("Solo se permiten elementos <xpath> dentro de <data>."))

        for node in root.iter():
            if node.tag in FORBIDDEN_TAGS:
                raise UserError(_("Elemento no permitido: <%s>.") % node.tag)
            for attr in node.attrib:
                if attr.lower().startswith("on") or attr in FORBIDDEN_ATTRS:
                    raise UserError(_("Atributo no permitido: %s.") % attr)

        for xp in xpaths:
            if not xp.get("expr"):
                raise UserError(_("Hay un <xpath> sin atributo expr."))
            if xp.get("position") not in ALLOWED_POSITIONS:
                raise UserError(
                    _("Posición no permitida en un <xpath>: %s.") % xp.get("position")
                )

    def _create_inherited_view(self, view, xml, active=True):
        return self.env["ir.ui.view"].sudo().create({
            "name": "NM AI: %s" % (self.instruction or "")[:60],
            "type": "qweb",
            "inherit_id": view.id,
            "mode": "extension",
            "priority": 99,
            "active": active,
            "arch_base": xml,
        })

    def _dry_run(self, view, xml):
        """Crea la vista dentro de un savepoint y la deshace siempre.

        Si los xpath no encajan, Odoo lanza un error al crearla.
        """
        try:
            with self.env.cr.savepoint():
                self._create_inherited_view(view, xml)
                raise _DryRunDone()
        except _DryRunDone:
            return
        except (ValidationError, ValueError) as err:
            raise UserError(
                _("Los cambios propuestos no encajan en la plantilla: %s") % err
            ) from err

    # ------------------------------------------------------------------
    # Acciones
    # ------------------------------------------------------------------
    def action_generate(self):
        self.ensure_one()
        self._check_admin()
        view = self._resolve_view()
        combined = self._combined_arch_str(view)

        user_msg = "Instrucción del usuario:\n%s\n\nPlantilla actual:\n%s" % (
            self.instruction,
            combined,
        )
        result = self.env["nm.ai.client"].complete(SYSTEM_PROMPT, user_msg)

        if result.get("stop_reason") == "max_tokens":
            raise UserError(_("La respuesta de la IA se cortó. Pide un cambio más pequeño."))

        xml = self._clean_xml(result["text"])
        self._validate_xml(xml)
        self._dry_run(view, xml)

        self.write({"view_id": view.id, "result_xml": xml, "state": "generated"})
        return self._reopen()

    def action_apply(self):
        self.ensure_one()
        self._check_admin()
        if not self.view_id or not self.result_xml:
            raise UserError(_("Primero genera los cambios."))
        xml = self._clean_xml(self.result_xml)
        # Se revalida porque el usuario puede haber editado el texto.
        self._validate_xml(xml)
        self._dry_run(self.view_id, xml)
        self._create_inherited_view(self.view_id, xml)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Cambios aplicados"),
                "message": _("El informe ya usa los cambios propuestos."),
                "type": "success",
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    def action_back(self):
        self.ensure_one()
        self.write({"state": "draft"})
        return self._reopen()