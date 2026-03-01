# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.http import request


class AuditlogHTTPSession(models.Model):
    _inherit = "auditlog.http.session"

    ip_address = fields.Char("IP Address", readonly=True)

    @api.model
    def current_http_session(self):
        """Extend to capture the remote IP address when creating a session."""
        if not request:
            return False
        httpsession = request.session
        if httpsession:
            existing_session = self.search(
                [("name", "=", httpsession.sid), ("user_id", "=", request.uid)],
                limit=1,
            )
            if existing_session:
                # Update IP if it was not set
                if not existing_session.ip_address:
                    ip = self._get_remote_ip()
                    if ip:
                        existing_session.sudo().write({"ip_address": ip})
                return existing_session.id
            ip = self._get_remote_ip()
            vals = {
                "name": httpsession.sid,
                "user_id": request.uid,
                "ip_address": ip,
            }
            httpsession.auditlog_http_session_id = self.create(vals).id
            return httpsession.auditlog_http_session_id
        return False

    @api.model
    def _get_remote_ip(self):
        """Get the real remote IP, considering proxy headers."""
        if not request:
            return False
        httprequest = request.httprequest
        # Check for X-Forwarded-For header (when behind a reverse proxy)
        forwarded_for = httprequest.headers.get("X-Forwarded-For")
        if forwarded_for:
            # The first IP in the list is the client's real IP
            return forwarded_for.split(",")[0].strip()
        # Check for X-Real-IP header
        real_ip = httprequest.headers.get("X-Real-Ip")
        if real_ip:
            return real_ip.strip()
        return httprequest.remote_addr
