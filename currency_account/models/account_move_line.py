from odoo import api, fields, models

import logging

from odoo.tools.float_utils import float_compare, float_is_zero

_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    price_subtotal_currency = fields.Monetary(
        string="Precio en Moneda",
        help="",
        currency_field="company_currency_id",
        compute="_compute_price_subtotal_currency",
        precompute=True,
        store=True,
        readonly=False,
    )

    warning_rate_difference = fields.Boolean(
        string="Advertencia de tasa de cambio",
        help="Advertencia de tasa de cambio",
        compute="_compute_warning_rate_difference",
        store=True,
    )

    manually_price_subtotal_currency = fields.Boolean(
        string="Precio en Moneda manual",
        help="Precio en Moneda manual",
        default=False,
    )

    has_rate_difrerence = fields.Boolean(
        string="Tiene diferencia de tasa de cambio",
        help="Tiene diferencia de tasa de cambio",
        compute="_compute_has_rate_difrerence",
    )

    @api.depends(
        "currency_rate",
        "move_id.invoice_currency_rate",
    )
    def _compute_has_rate_difrerence(self):
        for line in self:
            line.has_rate_difrerence = (
                line.currency_rate != line.move_id.invoice_currency_rate
            )

    def reset_price_subtotal_currency(self):
        for line in self:
            rate = line.move_id.invoice_currency_rate or 1.0
            line.currency_rate = rate or 1.0
            line.price_subtotal_currency = line.price_unit / rate
            line.manually_price_subtotal_currency = False

    @api.onchange("price_subtotal_currency")
    def _onchange_price_subtotal_currency(self):
        for line in self:
            if not line.price_subtotal_currency:
                continue
            line.manually_price_subtotal_currency = True

    @api.depends(
        "price_unit",
        "quantity",
        "amount_currency",
        "balance",
        "company_id.currency_id",
        "manually_price_subtotal_currency",
    )
    def _compute_price_subtotal_currency(self):
        for line in self:
            if line.manually_price_subtotal_currency:
                continue

            if line.currency_id == line.company_id.currency_id:
                line.price_subtotal_currency = False
                continue

            line.price_subtotal_currency = abs(line.balance)

    @api.depends(
        "currency_id",
        "company_id",
        "move_id.invoice_currency_rate",
        "move_id.date",
        "price_subtotal_currency",
        "manually_price_subtotal_currency",
        "amount_currency",
    )
    def _compute_currency_rate(self):
        for line in self:
            if line.price_subtotal_currency and line.manually_price_subtotal_currency:
                currency_rate = abs(line.amount_currency) / abs(
                    line.price_subtotal_currency
                )
                line.currency_rate = currency_rate
            elif line.move_id.is_invoice(include_receipts=True):
                line.currency_rate = line.move_id.invoice_currency_rate or 1.0
            elif line.currency_id:
                line.currency_rate = self.env["res.currency"]._get_conversion_rate(
                    from_currency=line.company_currency_id,
                    to_currency=line.currency_id,
                    company=line.company_id,
                    date=line.move_id.invoice_date
                    or line.move_id.date
                    or fields.Date.context_today(line),
                )
            else:
                line.currency_rate = 1

    @api.depends(
        "currency_rate",
        "move_id.invoice_currency_rate",
        "price_subtotal_currency",
        "manually_price_subtotal_currency",
        "amount_currency",
    )
    def _compute_warning_rate_difference(self):
        for line in self:
            if line.price_subtotal_currency and line.manually_price_subtotal_currency:
                invoice_currency_rate = line.move_id.invoice_currency_rate or 1.0
                currency_rate = abs(line.amount_currency) / abs(
                    line.price_subtotal_currency
                )
                line.warning_rate_difference = (
                    float_compare(
                        currency_rate, invoice_currency_rate, precision_digits=6
                    )
                    != 0
                )
            else:
                line.warning_rate_difference = False
