import logging

from odoo import models

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _compute_tax_totals(self):
        super()._compute_tax_totals()
        for move in self:
            if move.tax_totals:
                move.tax_totals["display_in_company_currency"] = True
