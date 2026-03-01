# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Venezuela SENIAT - Auditoria",
    "version": "18.0.1.0.0",
    "author": "Anderson Armeya",
    "category": "Tools",
    "depends": ["auditlog", "l10n_ve_seniat", "l10n_ve_withholding"],
    "data": [
        "security/ir.model.access.csv",
        "views/menus.xml",
        "views/http_session_views.xml",
        "views/login_attempt_views.xml",
        "data/auditlog_rule_data.xml",
    ],
    "license": "AGPL-3",
    "installable": True,
}
