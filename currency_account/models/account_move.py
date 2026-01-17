import json

from odoo import api, fields, models

import logging

from odoo.tools.float_utils import float_compare, float_is_zero

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    total_currencies = fields.Json(
        string="Totales por Moneda",
        compute="_compute_total_currencies",
        store=True,
        help="Almacena el total de la factura y el residuo pendiente en cada moneda habilitada.",  # noqa: E501
    )

    lines_with_rate_difference = fields.Boolean(
        string="Lineas con diferencia de tasa de cambio",
        help="Lineas con diferencia de tasa de cambio",
        compute="_compute_lines_with_rate_difference",
    )

    @api.depends(
        "line_ids.has_rate_difrerence",
    )
    def _compute_lines_with_rate_difference(self):
        for move in self:
            move.lines_with_rate_difference = any(line.has_rate_difrerence for line in move.invoice_line_ids)

    @api.depends(
        "line_ids.price_subtotal",
        "line_ids.tax_ids",
        "line_ids.price_total",
        "currency_id",
        "amount_total",
        "amount_residual",
        "company_id.currency_id",
    )
    def _compute_total_currencies(self):
        for move in self:
            totals = {}
            company_currency = move.company_id.currency_id

            currencies = self.env["res.currency"].search(
                [("active", "=", True), ("id", "!=", move.currency_id.id)]
            )

            for currency in currencies:
                date = move.date or fields.Date.today()
                total_in_currency = move.currency_id._convert(
                    move.amount_total, currency, move.company_id, date
                )

                if currency == company_currency:
                    date = fields.Date.today()

                residual_in_currency = move.currency_id._convert(
                    move.amount_residual, currency, move.company_id, date
                )

                totals[str(currency.id)] = {
                    "currency_id": currency.id,
                    "currency_name": currency.name,
                    "total": total_in_currency,
                    "residual": residual_in_currency,
                }

            # El campo JSON debe almacenar una estructura serializable
            move.total_currencies = json.dumps(totals) if totals else False

    def _prepare_product_base_line_for_taxes_computation(self, product_line):
        """Convert an account.move.line having display_type='product' into a base line for the taxes computation.

        :param product_line: An account.move.line.
        :return: A base line returned by '_prepare_base_line_for_taxes_computation'.
        """
        self.ensure_one()
        is_invoice = self.is_invoice(include_receipts=True)
        sign = self.direction_sign if is_invoice else 1
        if is_invoice:
            if product_line.price_subtotal_currency:
                rate = product_line.currency_rate
            else:
                rate = self.invoice_currency_rate
        else:
            rate = (
                (abs(product_line.amount_currency) / abs(product_line.balance))
                if product_line.balance
                else 0.0
            )

        return self.env["account.tax"]._prepare_base_line_for_taxes_computation(
            product_line,
            price_unit=(
                product_line.price_unit if is_invoice else product_line.amount_currency
            ),
            quantity=product_line.quantity if is_invoice else 1.0,
            discount=product_line.discount if is_invoice else 0.0,
            rate=rate,
            sign=sign,
            special_mode=False if is_invoice else "total_excluded",
            name=product_line.name,
        )

