from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_round


class ResCurrency(models.Model):
    _inherit = "res.currency"

    l10n_ve_show_in_rates_list = fields.Boolean(
        string="Mostrar en lista de tasas",
        default=True,
        help="Si está activo, la moneda aparecerá en la lista de tasas "
        "del botón Tasas en la barra de navegación.",
    )
    l10n_ve_show_in_systray = fields.Boolean(
        string="Mostrar en barra de navegación",
        default=False,
        help="Si está activo, la tasa de esta moneda se mostrará "
        "directamente en la barra de navegación junto al botón de Tasas.",
    )

    @api.constrains("l10n_ve_show_in_systray")
    def _check_single_systray_currency(self):
        if any(rec.l10n_ve_show_in_systray for rec in self):
            count = self.search_count([("l10n_ve_show_in_systray", "=", True)])
            if count > 1:
                raise ValidationError(
                    _(
                        "Solo una moneda puede estar configurada para "
                        "mostrarse en la barra de navegación."
                    )
                )

    @api.model
    def get_exchange_rates(self):
        company_currency = self.env.company.currency_id
        currencies = self.env["res.currency"].search(
            [
                ("active", "=", True),
                ("id", "!=", company_currency.id),
                ("l10n_ve_show_in_rates_list", "=", True),
            ]
        )

        rates_data = []
        featured = False
        for currency in currencies:
            rate_val = float_round(
                currency.inverse_rate, precision_digits=currency.decimal_places
            )
            rate_info = {
                "name": currency.name,
                "symbol": currency.symbol,
                "rate": rate_val,
                "company_currency_name": company_currency.name,
                "company_currency_symbol": company_currency.symbol,
            }
            rates_data.append(rate_info)
            if currency.l10n_ve_show_in_systray:
                featured = {
                    "name": currency.name,
                    "symbol": currency.symbol,
                    "rate": rate_val,
                    "company_currency_symbol": company_currency.symbol,
                }

        return {
            "company_currency": company_currency.name,
            "rates": rates_data,
            "featured": featured,
        }
