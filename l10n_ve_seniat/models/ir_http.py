# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    def session_info(self):
        session = super().session_info()
        module = (
            self.env["ir.module.module"]
            .sudo()
            .search([("name", "=", "l10n_ve_seniat")], limit=1)
        )
        version = module.installed_version if module else ""
        enterprise = (
            self.env["ir.module.module"]
            .sudo()
            .search(
                [("name", "=", "web_enterprise"), ("state", "=", "installed")],
                limit=1,
            )
        )
        edition = "Enterprise" if enterprise else "Community"
        session["l10n_ve_version"] = f"Odoo {edition} v{version}" if version else ""
        return session
