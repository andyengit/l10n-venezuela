# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.tests import tagged

from .common import L10nVeSeniatCommon


@tagged("post_install", "-at_install")
class TestIrActionsReport(L10nVeSeniatCommon):
    def test_render_qweb_pdf_marks_original_printed(self):
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
        report = self.env.ref("account.account_invoices", raise_if_not_found=False)
        if report:
            report.with_context(l10n_ve_invoice=True)._render_qweb_pdf(
                report.report_name, move.ids
            )
            move.invalidate_recordset()
            self.assertTrue(move.l10n_ve_invoice_original_printed)
