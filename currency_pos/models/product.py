from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields_list = super()._load_pos_data_fields(config_id)
        if "currency_id" not in fields_list:
            fields_list.append("currency_id")
        return fields_list

    def _process_pos_ui_product_product(self, products, config_id):
        products_by_id = {p["id"]: p for p in products}
        product_ids = list(products_by_id.keys())
        product_records = self.browse(product_ids)
        
        company = self.env.company
        company_currency = company.currency_id
        pos_currency = config_id.currency_id
        date = fields.Date.today()
        
        original_prices = {}
        for product_record in product_records:
            product_data = products_by_id[product_record.id]
            product_currency = product_record.currency_id
            
            if product_currency and product_currency != company_currency:
                original_prices[product_record.id] = {
                    "currency": product_currency,
                    "lst_price": product_data.get("lst_price"),
                    "standard_price": product_data.get("standard_price"),
                }
        
        super()._process_pos_ui_product_product(products, config_id)
        
        for product_id, original_data in original_prices.items():
            product_data = products_by_id[product_id]
            product_currency = original_data["currency"]
            
            if original_data.get("lst_price") is not None:
                product_data["lst_price"] = product_currency._convert(
                    original_data["lst_price"], pos_currency, company, date
                )
            
            if original_data.get("standard_price") is not None:
                product_data["standard_price"] = product_currency._convert(
                    original_data["standard_price"], pos_currency, company, date
                )
