{
    'name': "NM Report AI Editor",

    'summary': "Edita los informes PDF de Odoo pidiéndoselo a una IA",

    'description': """
Editor de informes con IA
=========================

Permite modificar los informes QWeb de Odoo (facturas, presupuestos,
albaranes...) describiendo en lenguaje natural el cambio que se quiere,
por ejemplo: "pon el logo a la derecha y añade una columna de descuento".

Funcionalidades
---------------
* Conexión con Claude (Anthropic) usando la clave API propia de la empresa.
* Asistente para pedir cambios sobre cualquier informe.
* Validación del XML generado antes de aplicarlo.
* Los cambios se guardan como vistas heredadas, sin tocar el informe original.
* Historial de versiones para poder volver atrás.

Configuración
-------------
Ajustes > Informes con IA: introducir la clave API y elegir el modelo.
Solo los administradores pueden usar el editor.
    """,

    'author': "Nil Moreno Fernandez",
    'website': "https://github.com/nmf-dev",

    'category': 'Technical',
    'version': '20.0.1.0.0',
    'license': 'LGPL-3',

    'depends': ['base_setup'],

    'data': [
        # 'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/nm_report_ai_wizard_views.xml',
    ],
    'installable': True,
    'application': True,
}