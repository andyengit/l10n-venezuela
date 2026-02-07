from odoo import api, models


class ResCurrency(models.Model):
    _inherit = "res.currency"

    def _available_models(self):
        res = super()._available_models()
        res.extend([
            "purchase.model_purchase_order",
            "purchase.model_purchase_order_line",
        ])
        return res

    def _available_line_models(self):
        res = super()._available_line_models()
        res.append("purchase.model_purchase_order_line")
        return res

    def _available_report_models(self):
        res = super()._available_report_models()
        res.append("purchase.model_purchase_report")
        return res

    @api.model
    def _available_fields_depends_on(self, model):
        if model == "purchase.order":
            return ["amount_total"]
        if model == "purchase.order.line":
            return ["price_subtotal", "price_unit", "product_qty", "discount"]
        return super()._available_fields_depends_on(model)
