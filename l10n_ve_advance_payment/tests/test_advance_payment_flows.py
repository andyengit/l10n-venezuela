from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import TestL10nVeAdvanceCommon


@tagged("post_install", "-at_install")
class TestAdvancePaymentFlows(TestL10nVeAdvanceCommon):
    def test_manual_payment_without_invoice_creates_advance(self):
        payment = self._create_manual_payment(100.0)
        payment.action_post()
        payment.invalidate_recordset()

        liability_lines = payment.move_id.line_ids.filtered(
            lambda line: line.account_id == self.advance_account and line.credit > 0
        )
        self.assertTrue(liability_lines)
        self.assertAlmostEqual(sum(liability_lines.mapped("credit")), 100.0, places=2)

        advance = self.env["l10n_ve.advance.payment"].search([("payment_id", "=", payment.id)])
        self.assertTrue(advance)
        self.assertAlmostEqual(advance.amount_residual, 100.0, places=2)

    def test_register_payment_over_residual_creates_advance(self):
        invoice = self._create_customer_invoice(75.0)
        payments = self._register_payment_from_invoice(invoice, 100.0)
        payment = payments[:1]
        invoice.invalidate_recordset()

        self.assertTrue(invoice.currency_id.is_zero(invoice.amount_residual))

        liability_lines = payment.move_id.line_ids.filtered(
            lambda line: line.account_id == self.advance_account and line.credit > 0
        )
        self.assertTrue(liability_lines)
        self.assertAlmostEqual(sum(liability_lines.mapped("credit")), 25.0, places=2)

        advance = self.env["l10n_ve.advance.payment"].search([("payment_id", "=", payment.id)])
        self.assertTrue(advance)
        self.assertAlmostEqual(advance.amount_residual, 25.0, places=2)

    def test_register_payment_uses_advance_before_bank(self):
        manual_payment = self._create_manual_payment(50.0)
        manual_payment.action_post()
        advance = self.env["l10n_ve.advance.payment"].search([("payment_id", "=", manual_payment.id)], limit=1)
        invoice = self._create_customer_invoice(80.0)
        payments = self._register_payment_from_invoice(invoice, 80.0)
        payment = payments[:1]
        invoice.invalidate_recordset()
        advance.invalidate_recordset()
        self.assertTrue(invoice.currency_id.is_zero(invoice.amount_residual))
        self.assertTrue(payment)
        self.assertAlmostEqual(payment.amount, 30.0, places=2)
        self.assertAlmostEqual(advance.amount_residual, 0.0, places=2)

    def test_register_payment_with_advance_only_no_bank_move(self):
        manual_payment = self._create_manual_payment(50.0)
        manual_payment.action_post()
        advance = self.env["l10n_ve.advance.payment"].search([("payment_id", "=", manual_payment.id)], limit=1)
        invoice = self._create_customer_invoice(40.0)
        payments = self._register_payment_from_invoice(invoice, 40.0)
        payment = payments[:1]
        invoice.invalidate_recordset()
        advance.invalidate_recordset()
        self.assertTrue(payment)
        self.assertTrue(payment.l10n_ve_is_advance_application)
        self.assertAlmostEqual(payment.amount, 40.0, places=2)
        self.assertTrue(invoice.currency_id.is_zero(invoice.amount_residual))
        self.assertAlmostEqual(advance.amount_residual, 10.0, places=2)

    def test_register_payment_with_existing_advance_and_overpay_creates_new_advance(self):
        old_advance_payment = self._create_manual_payment(40.0)
        old_advance_payment.action_post()
        invoice = self._create_customer_invoice(100.0)
        payments = self._register_payment_from_invoice(invoice, 120.0)
        payment = payments[:1]
        invoice.invalidate_recordset()
        self.assertTrue(invoice.currency_id.is_zero(invoice.amount_residual))
        self.assertTrue(payment)
        self.assertAlmostEqual(payment.amount, 80.0, places=2)
        advances = self.env["l10n_ve.advance.payment"].search(
            [("company_id", "=", self.company.id), ("partner_id", "=", self.partner.commercial_partner_id.id)]
        )
        open_advances = advances.filtered(lambda adv: adv.state == "open")
        self.assertEqual(len(open_advances), 1)
        self.assertAlmostEqual(open_advances.amount_residual, 20.0, places=2)

    def test_payment_without_invoice_requires_advance_config(self):
        self.company.l10n_ve_advance_liability_account_id = False
        payment = self._create_manual_payment(100.0)
        with self.assertRaises(UserError):
            payment.action_post()

    def test_widget_apply_opens_register_wizard_and_blocks_amount_over_advance(self):
        manual_payment = self._create_manual_payment(50.0)
        manual_payment.action_post()
        advance = self.env["l10n_ve.advance.payment"].search([("payment_id", "=", manual_payment.id)], limit=1)
        invoice = self._create_customer_invoice(120.0)

        action = advance.with_context(l10n_ve_invoice_id=invoice.id).action_apply_from_invoice()
        self.assertEqual(action["res_model"], "account.payment.register")
        self.assertEqual(action["context"].get("l10n_ve_force_advance_id"), advance.id)
        self.assertAlmostEqual(action["context"].get("default_amount"), 50.0, places=2)
        self.assertEqual(action["context"].get("default_payment_date"), str(advance.date))

        wizard = (
            self.env["account.payment.register"]
            .with_context(action["context"])
            .create(
                {
                    "company_id": self.company.id,
                    "journal_id": self.bank_journal.id,
                    "payment_date": self.test_date,
                    "amount": 60.0,
                    "currency_id": self.currency.id,
                    "group_payment": True,
                }
            )
        )
        self.assertTrue(wizard.l10n_ve_show_selected_advance)
        self.assertEqual(wizard.l10n_ve_selected_advance_id, advance)
        self.assertAlmostEqual(wizard.l10n_ve_selected_advance_available_amount, 50.0, places=2)
        with self.assertRaises(UserError):
            wizard._create_payments()

    def test_widget_apply_blocks_modified_payment_date(self):
        manual_payment = self._create_manual_payment(50.0)
        manual_payment.action_post()
        advance = self.env["l10n_ve.advance.payment"].search([("payment_id", "=", manual_payment.id)], limit=1)
        invoice = self._create_customer_invoice(120.0)
        action = advance.with_context(l10n_ve_invoice_id=invoice.id).action_apply_from_invoice()
        wizard = (
            self.env["account.payment.register"]
            .with_context(action["context"])
            .create(
                {
                    "company_id": self.company.id,
                    "journal_id": self.bank_journal.id,
                    "payment_date": self.test_date + self.test_date.resolution,
                    "amount": 50.0,
                    "currency_id": self.currency.id,
                    "group_payment": True,
                }
            )
        )
        with self.assertRaises(UserError):
            wizard._create_payments()

    def test_widget_apply_uses_payment_entry_with_advance_account(self):
        manual_payment = self._create_manual_payment(50.0)
        manual_payment.action_post()
        advance = self.env["l10n_ve.advance.payment"].search([("payment_id", "=", manual_payment.id)], limit=1)
        invoice = self._create_customer_invoice(120.0)
        action = advance.with_context(l10n_ve_invoice_id=invoice.id).action_apply_from_invoice()
        wizard = (
            self.env["account.payment.register"]
            .with_context(action["context"])
            .create(
                {
                    "company_id": self.company.id,
                    "journal_id": self.bank_journal.id,
                    "payment_date": self.test_date,
                    "amount": 50.0,
                    "currency_id": self.currency.id,
                    "group_payment": True,
                }
            )
        )
        payments = wizard._create_payments()
        payment = payments[:1]
        self.assertTrue(payment)
        self.assertTrue(payment.l10n_ve_is_advance_application)
        liquidity_line = payment.move_id.line_ids.filtered(
            lambda line: line.account_id == self.advance_account and line.parent_state == "posted"
        )[:1]
        self.assertTrue(liquidity_line)
        self.assertFalse(
            self.env["account.move"].search([("ref", "=", "Aplicacion automatica de anticipo")], limit=1)
        )
        invoice.invalidate_recordset()
        advance.invalidate_recordset()
        self.assertAlmostEqual(invoice.amount_residual, 70.0, places=2)
        self.assertAlmostEqual(advance.amount_residual, 0.0, places=2)

    def test_cannot_apply_same_advance_over_residual_after_partial_use(self):
        manual_payment = self._create_manual_payment(50.0)
        manual_payment.action_post()
        advance = self.env["l10n_ve.advance.payment"].search([("payment_id", "=", manual_payment.id)], limit=1)

        invoice_one = self._create_customer_invoice(30.0)
        action_one = advance.with_context(l10n_ve_invoice_id=invoice_one.id).action_apply_from_invoice()
        wizard_one = (
            self.env["account.payment.register"]
            .with_context(action_one["context"])
            .create(
                {
                    "company_id": self.company.id,
                    "journal_id": self.bank_journal.id,
                    "payment_date": self.test_date,
                    "amount": 30.0,
                    "currency_id": self.currency.id,
                    "group_payment": True,
                }
            )
        )
        wizard_one._create_payments()
        advance.invalidate_recordset()
        self.assertAlmostEqual(advance.amount_residual, 20.0, places=2)

        invoice_two = self._create_customer_invoice(40.0)
        action_two = advance.with_context(l10n_ve_invoice_id=invoice_two.id).action_apply_from_invoice()
        wizard_two = (
            self.env["account.payment.register"]
            .with_context(action_two["context"])
            .create(
                {
                    "company_id": self.company.id,
                    "journal_id": self.bank_journal.id,
                    "payment_date": self.test_date,
                    "amount": 25.0,
                    "currency_id": self.currency.id,
                    "group_payment": True,
                }
            )
        )
        with self.assertRaises(UserError):
            wizard_two._create_payments()
