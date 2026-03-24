# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, fields
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import L10nVeSeniatCommon


@tagged("post_install", "-at_install")
class TestAccountMoveLine(L10nVeSeniatCommon):
    def test_validate_price_not_zero_raises_on_zero_price(self):
        partner = self.env["res.partner"].create(
            {"name": "Partner", "country_id": self.env.ref("base.ve").id, "vat": "J12345678"}
        )
        with self.assertRaises(ValidationError) as cm:
            self.env["account.move"].create(
                {
                    "move_type": "out_invoice",
                    "partner_id": partner.id,
                    "invoice_line_ids": [
                        (
                            0,
                            0,
                            {
                                "name": "Zero price line",
                                "quantity": 1.0,
                                "price_unit": 0.0,
                                "account_id": self.company_data["default_account_revenue"].id,
                                "tax_ids": [(6, 0, [self.company_data["default_tax_sale"].id])],
                            },
                        )
                    ],
                }
            )
        self.assertIn("precio en 0", str(cm.exception))

    def test_subtotal_company_currency_invoice(self):
        partner = self.env["res.partner"].create(
            {"name": "Partner", "country_id": self.env.ref("base.ve").id, "vat": "J12345678"}
        )
        move = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": partner.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Line",
                            "quantity": 2.0,
                            "price_unit": 100.0,
                            "account_id": self.company_data["default_account_revenue"].id,
                            "tax_ids": [(6, 0, [self.company_data["default_tax_sale"].id])],
                        },
                    )
                ],
            }
        )
        move.action_post()
        line = move.line_ids.filtered(lambda l: l.display_type == "product")
        self.assertEqual(len(line), 1)
        self.assertGreater(line.subtotal_company_currency, 0)

    def test_put_unique_tax_per_line_purchase_adds_default_tax(self):
        supplier = self.env["res.partner"].create(
            {"name": "Supplier", "country_id": self.env.ref("base.ve").id, "vat": "J98765432"}
        )
        move = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": supplier.id,
                "invoice_date": fields.Date.today(),
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Line no tax",
                            "quantity": 1.0,
                            "price_unit": 50.0,
                            "account_id": self.company_data["default_account_expense"].id,
                            "tax_ids": [],
                        },
                    )
                ],
            }
        )
        line = move.invoice_line_ids.filtered(lambda l: l.display_type == "product")
        self.assertEqual(len(line.tax_ids), 1)
        self.assertEqual(line.tax_ids, self.company_data["default_tax_purchase"])

    def test_subtotal_refund(self):
        partner = self.env["res.partner"].create(
            {"name": "P", "country_id": self.env.ref("base.ve").id, "vat": "J12345678"}
        )
        invoice = self.env["account.move"].create(
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
                            "price_unit": 50.0,
                            "account_id": self.company_data["default_account_revenue"].id,
                            "tax_ids": [(6, 0, [self.company_data["default_tax_sale"].id])],
                        },
                    )
                ],
            }
        )
        invoice.action_post()
        move = invoice._reverse_moves()
        move.action_post()
        line = move.line_ids.filtered(lambda l: l.display_type == "product")
        self.assertGreater(line.subtotal_company_currency, 0)
