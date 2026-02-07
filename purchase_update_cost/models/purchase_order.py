from odoo import fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    update_product_cost = fields.Boolean(
        string="Actualizar Coste",
        default=True,
        copy=False,
        tracking=True,
    )

    def action_toggle_update_cost(self):
        for order in self:
            order.update_product_cost = not order.update_product_cost

    def button_confirm(self):
        res = super().button_confirm()
        for order in self:
            if order.state in ("purchase", "done") and order.update_product_cost:
                order._update_product_cost()
        return res

    def _update_product_cost(self):
        for line in self.order_line.filtered(
            lambda l: not l.display_type and l.product_id
        ):
            price_unit = line.price_unit
            if line.discount:
                price_unit = price_unit * (1 - line.discount / 100.0)
            if line.product_uom and line.product_uom != line.product_id.uom_id:
                price_unit = line.product_uom._compute_price(
                    price_unit, line.product_id.uom_id
                )
            product_cost_currency = line.product_id.cost_currency_id
            if line.currency_id and line.currency_id != product_cost_currency:
                date = line.order_id.date_order or fields.Date.context_today(line)
                price_unit = line.currency_id._convert(
                    price_unit,
                    product_cost_currency,
                    line.company_id,
                    date,
                )
            line.product_id.standard_price = price_unit
