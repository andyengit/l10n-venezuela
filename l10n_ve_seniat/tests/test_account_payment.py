# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.tests import tagged

from .common import L10nVeSeniatCommon


@tagged("post_install", "-at_install")
class TestAccountPayment(L10nVeSeniatCommon):
    def test_payment_is_retention_field(self):
        partner = self.env["res.partner"].create(
            {"name": "Partner", "country_id": self.env.ref("base.ve").id, "vat": "J12345678"}
        )
        move = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": partner.id,
                "invoice_date": fields.Date.today(),
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Line",
                            "quantity": 1.0,
                            "price_unit": 100.0,
                            "account_id": self.company_data["default_account_revenue"].id,
                            "tax_ids": [(6, 0, [self.company_data["default_tax_sale"].id])],
                        },
                    )
                ],
            }
        )
        move.action_post()
        wizard = (
            self.env["account.payment.register"]
            .with_context(active_model="account.move", active_ids=move.ids)
            .create({"payment_date": fields.Date.today()})
        )
        payments = wizard._create_payments()
        payment = payments[0] if len(payments) > 1 else payments
        payment.is_retention = True
        self.assertTrue(payment.is_retention)
