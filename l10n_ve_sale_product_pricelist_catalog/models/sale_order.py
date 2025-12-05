import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _get_product_catalog_order_data(self, products, **kwargs):
        res = super()._get_product_catalog_order_data(products, **kwargs)
        pricelists = self.env["product.pricelist"].search(
            [
                ("active", "=", True),
            ]
        )
        for pricelist in pricelists:
            prices = pricelist._get_products_price(
                products,
                quantity=1.0,
                date=self.date_order or fields.Datetime.now(),
            )

            currency = pricelist.currency_id

            for product in products:
                price = prices.get(product.id, 0.0)

                company_curency_price = currency._convert(
                    price,
                    self.company_id.currency_id,
                    self.company_id or self.env.company,
                    self.date_order or fields.Datetime.now(),
                )

                if "pricelists" not in res[product.id]:
                    res[product.id]["pricelists"] = []

                res[product.id]["pricelists"].append(
                    {
                        "id": pricelist.id,
                        "name": pricelist.name + f" ({pricelist.currency_id.symbol})",
                        "price": price,
                        "company_currency_price": company_curency_price,
                        "currency_id": pricelist.currency_id.id,
                        "currency_symbol": pricelist.currency_id.symbol,
                        "company_currency_id": self.company_id.currency_id.id,
                        "company_currency_symbol": self.company_id.currency_id.symbol,
                    }
                )
        return res
