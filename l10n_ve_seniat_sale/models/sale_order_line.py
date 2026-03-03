# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models
from odoo.exceptions import ValidationError


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.constrains("tax_id", "order_id")
    def _check_tax_single_required_ve(self):
        for line in self:
            if line.display_type:
                continue
            if line.order_id.state != "sale":
                continue
            if line.order_id.country_code != "VE":
                continue
            if len(line.tax_id) == 0:
                raise ValidationError(
                    _(
                        "No se puede quitar el impuesto de la línea '%s' en un pedido confirmado. "
                        "Cada línea debe tener exactamente un impuesto."
                    )
                    % (line.name or _("Sin nombre"))
                )
            if len(line.tax_id) > 1:
                tax_mapped = ", ".join(line.tax_id.mapped("name"))
                raise ValidationError(
                    _(
                        "No se puede asignar más de un impuesto a la línea '%s' en un pedido confirmado. "
                        "Cree una línea separada para cada impuesto. Impuestos actuales: %s"
                    )
                    % (line.name or _("Sin nombre"), tax_mapped)
                )
