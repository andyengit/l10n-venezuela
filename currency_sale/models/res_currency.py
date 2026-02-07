from odoo import api, models


class ResCurrency(models.Model):
    _inherit = "res.currency"

    def _available_models(self):
        res = super()._available_models()
        res.extend([
            "sale.model_sale_order",
            "sale.model_sale_order_line",
        ])
        return res

    def _available_line_models(self):
        res = super()._available_line_models()
        res.append("sale.model_sale_order_line")
        return res

    def _available_report_models(self):
        res = super()._available_report_models()
        res.append("sale.model_sale_report")
        return res

    @api.model
    def _available_fields_depends_on(self, model):
        if model == "sale.order":
            return ["amount_total"]
        if model == "sale.order.line":
            return ["price_subtotal", "price_unit", "product_uom_qty", "discount"]
        return super()._available_fields_depends_on(model)
