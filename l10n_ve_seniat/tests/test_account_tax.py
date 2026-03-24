# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import L10nVeSeniatCommon


@tagged("post_install", "-at_install")
class TestAccountTax(L10nVeSeniatCommon):
    def test_ve_tax_amount_not_modifiable(self):
        tax = self.env["account.tax"].create(
            {
                "name": "Test VE Tax",
                "amount": 16.0,
                "amount_type": "percent",
                "type_tax_use": "sale",
                "company_id": self.env.company.id,
            }
        )
        self.assertEqual(tax.country_code, "VE")
        with self.assertRaises(UserError) as cm:
            tax.write({"amount": 8.0})
        self.assertIn("Venezuela", str(cm.exception))
        self.assertIn("alícuota", str(cm.exception))
