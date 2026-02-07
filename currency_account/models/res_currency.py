from odoo import api, fields, models


class ResCurrency(models.Model):
    _inherit = "res.currency"

    def _available_models(self):
        return ["account.model_account_move_line", "account.model_account_move"]

    def _prepare_currency_field(self, model, field_name):
        return {
            "name": field_name,
            "field_description": f"Moneda {self.name}",
            "model_id": self.env.ref(model).id,
            "ttype": "many2one",
            "on_delete": "cascade",
            "relation": "res.currency",
            "store": True,
            "compute": f"""for record in self:
    record['{field_name}'] = {self.id}
            """,
        }

    @api.model
    def _available_fields_depends_on_account_move(self):
        return ["total_currencies","amount_total"]

    @api.model
    def _available_fields_depends_on(self, model):
        if model == "account.move":
            return self._available_fields_depends_on_account_move()
        if model == "account.move.line":
            return ["price_unit", "quantity", "discount"]
        return []

    def _prepare_currency_amount_field(self, model, field_name):
        model_record = self.env.ref(model)
        return {
            "name": field_name,
            "field_description": f"Monto en {self.name}",
            "model_id": model_record.id,
            "ttype": "monetary",
            "store": True,
            "depends": ", ".join(
                self._available_fields_depends_on(model_record.model)
            ),
            "compute": f"""for record in self:
    record['{field_name}'] = record._compute_currency_field({self.id})
            """,
        }

    def _available_line_models(self):
        return ["account.model_account_move_line"]

    def _prepare_price_unit_currency_field(self, model, field_name):
        model_record = self.env.ref(model)
        return {
            "name": field_name,
            "field_description": f"Precio Unit. en {self.name}",
            "model_id": model_record.id,
            "ttype": "monetary",
            "store": True,
            "depends": "price_unit",
            "compute": f"""for record in self:
    record['{field_name}'] = record._compute_price_unit_currency_field({self.id})
            """,
        }

    def _available_report_models(self):
        return ["account.model_account_invoice_report"]

    def _prepare_report_currency_field(self, model, field_name):
        return {
            "name": field_name,
            "field_description": f"Moneda {self.name}",
            "model_id": self.env.ref(model).id,
            "ttype": "many2one",
            "on_delete": "cascade",
            "relation": "res.currency",
            "store": True,
            "readonly": True,
        }

    def _prepare_report_amount_field(self, model, field_name):
        return {
            "name": field_name,
            "field_description": f"Monto en {self.name}",
            "model_id": self.env.ref(model).id,
            "ttype": "monetary",
            "store": True,
            "readonly": True,
        }

    def action_create_fields(self):
        self.ensure_one()
        field_model = self.env["ir.model.fields"]
        currency_field_name = f"x_currency_id_{self.id}"
        currency_amount_field_name = f"x_amount_currency_{self.id}"

        fields_to_delete = [currency_field_name, currency_amount_field_name]
        for model in self._available_models():
            field_model.sudo().search(
                [
                    ("name", "in", fields_to_delete),
                    ("model_id", "=", self.env.ref(model).id),
                ]
            ).unlink()

            currency_field_vals = self._prepare_currency_field(
                model, currency_field_name
            )
            currency_amount_field_vals = self._prepare_currency_amount_field(
                model, currency_amount_field_name
            )
            currency_amount_field_vals["currency_field"] = currency_field_vals["name"]

            self.env["ir.model.fields"].create(currency_field_vals)
            self.env["ir.model.fields"].create(currency_amount_field_vals)

        price_unit_field_name = f"x_price_unit_currency_{self.id}"
        for model in self._available_line_models():
            field_model.sudo().search(
                [
                    ("name", "=", price_unit_field_name),
                    ("model_id", "=", self.env.ref(model).id),
                ]
            ).unlink()

            price_unit_vals = self._prepare_price_unit_currency_field(
                model, price_unit_field_name
            )
            price_unit_vals["currency_field"] = currency_field_name
            self.env["ir.model.fields"].create(price_unit_vals)

        for model in self._available_report_models():
            field_model.sudo().search(
                [
                    ("name", "in", fields_to_delete),
                    ("model_id", "=", self.env.ref(model).id),
                ]
            ).unlink()

            currency_field_vals = self._prepare_report_currency_field(
                model, currency_field_name
            )
            currency_amount_field_vals = self._prepare_report_amount_field(
                model, currency_amount_field_name
            )
            currency_amount_field_vals["currency_field"] = currency_field_vals["name"]

            self.env["ir.model.fields"].create(currency_field_vals)
            self.env["ir.model.fields"].create(currency_amount_field_vals)
