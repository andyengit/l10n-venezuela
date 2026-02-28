from odoo import _, models
from odoo.exceptions import UserError


class AccountTax(models.Model):
    _inherit = "account.tax"

    def write(self, vals):
        if "amount" in vals:
            ve_taxes = self.filtered(lambda t: t.country_code == "VE")
            if ve_taxes:
                raise UserError(
                    _(
                        "No está permitido modificar la alícuota de los "
                        "impuestos del país Venezuela."
                    )
                )
        return super().write(vals)
