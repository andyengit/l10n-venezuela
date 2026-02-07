from odoo import models


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    def create_invoices_and_stay(self):
        self._check_amount_is_positive()
        self._create_invoices(self.sale_order_ids)
        return {'type': 'ir.actions.act_window_close'}
