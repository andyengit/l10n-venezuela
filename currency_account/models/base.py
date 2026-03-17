from odoo import api, models


class Base(models.AbstractModel):
    _inherit = "base"

    @api.model
    def _compute_subtotal_currency_field(self, currency_id):
        if hasattr(self, "_compute_currency_field"):
            return self._compute_currency_field(currency_id)
        return 0.0
