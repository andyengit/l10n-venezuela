# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.addons.web.controllers.home import Home


class HomeVersion(Home):
    @http.route()
    def web_login(self, *args, **kw):
        response = super().web_login(*args, **kw)
        if hasattr(response, "qcontext"):
            module = (
                http.request.env["ir.module.module"]
                .sudo()
                .search([("name", "=", "l10n_ve_seniat")], limit=1)
            )
            version = module.installed_version if module else ""
            enterprise = (
                http.request.env["ir.module.module"]
                .sudo()
                .search(
                    [("name", "=", "web_enterprise"), ("state", "=", "installed")],
                    limit=1,
                )
            )
            edition = "Enterprise" if enterprise else "Community"
            response.qcontext["l10n_ve_version"] = (
                f"Odoo {edition} v{version}" if version else ""
            )
        return response
