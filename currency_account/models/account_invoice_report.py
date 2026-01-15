from odoo import models, fields, api
from odoo.tools import SQL

class AccountInvoiceReport(models.Model):
    _inherit = "account.invoice.report"


    amount_currency_usd = fields.Float(
        string="Saldo en USD",
        help="Saldo en USD",
    )

    @api.model
    def _select(self):
        return SQL("%s,line.amount_currency_usd as amount_currency_usd ", super()._select())
