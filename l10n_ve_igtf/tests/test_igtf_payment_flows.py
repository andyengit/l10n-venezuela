from odoo.tests import tagged

from .common import TestL10nVeIgtfCommon


@tagged("post_install", "-at_install")
class TestIgtfPaymentFlows(TestL10nVeIgtfCommon):
    def _assert_igtf_case_in_bs(self, payment_ratio, expected_igtf_bs):
        invoice = self._create_customer_invoice(amount=100.0, currency=self.ves)
        payment_amount_bs = 100.0 * payment_ratio
        payment_amount_usd = self._usd_amount_for_ves(payment_amount_bs)
        payment, wizard = self._register_invoice_payment(
            invoice=invoice,
            amount=payment_amount_usd,
            currency=self.usd,
            apply_igtf=True,
            igtf_included=False,
            return_wizard=True,
        )
        self._assert_wizard_payment_consistency(wizard, payment)

        igtf_bs = abs(invoice.l10n_ve_igtf_collected_amount_company_currency)
        self.assertAlmostEqual(igtf_bs, expected_igtf_bs, places=3)
        self.assertLessEqual(igtf_bs, 3.0)

        igtf_group = self._get_igtf_group_from_tax_totals(invoice)
        self.assertTrue(igtf_group)
        self.assertAlmostEqual(
            abs(igtf_group.get("tax_amount", 0.0)),
            expected_igtf_bs,
            places=3,
        )
        self.assertLessEqual(abs(igtf_group.get("tax_amount", 0.0)), 3.0)
        self._assert_no_writeoff_or_exchange_diff(invoice, payment)

    def test_invoice_ves_payment_ves_without_igtf(self):
        invoice = self._create_customer_invoice(amount=100.0, currency=self.ves)
        payment, wizard = self._register_invoice_payment(
            invoice=invoice,
            amount=100.0,
            currency=self.ves,
            apply_igtf=False,
            igtf_included=False,
            return_wizard=True,
        )
        self._assert_wizard_payment_consistency(wizard, payment)
        invoice.invalidate_recordset()

        igtf_line = self._get_payment_igtf_line(payment)
        self.assertFalse(igtf_line)
        self.assertEqual(invoice.l10n_ve_igtf_collected_amount_currency, 0.0)
        self.assertEqual(invoice.l10n_ve_igtf_collected_amount_company_currency, 0.0)
        self._assert_no_writeoff_or_exchange_diff(invoice, payment)

        igtf_group = self._get_igtf_group_from_tax_totals(invoice)
        if igtf_group:
            self.assertEqual(igtf_group.get("tax_amount_currency", 0.0), 0.0)
            self.assertEqual(igtf_group.get("tax_amount", 0.0), 0.0)

    def test_invoice_usd_payment_ves_without_igtf(self):
        invoice = self._create_customer_invoice(amount=1.0, currency=self.usd)
        payment, wizard = self._register_invoice_payment(
            invoice=invoice,
            amount=100.0,
            currency=self.ves,
            apply_igtf=False,
            igtf_included=False,
            return_wizard=True,
        )
        self._assert_wizard_payment_consistency(wizard, payment)

        igtf_line = self._get_payment_igtf_line(payment)
        self.assertFalse(igtf_line)
        self.assertEqual(invoice.l10n_ve_igtf_collected_amount_currency, 0.0)
        self.assertEqual(invoice.l10n_ve_igtf_collected_amount_company_currency, 0.0)
        self._assert_no_writeoff_or_exchange_diff(invoice, payment)

        igtf_group = self._get_igtf_group_from_tax_totals(invoice)
        if igtf_group:
            self.assertEqual(igtf_group.get("tax_amount_currency", 0.0), 0.0)
            self.assertEqual(igtf_group.get("tax_amount", 0.0), 0.0)

    def test_invoice_ves_payment_usd_with_igtf(self):
        payment_amount_usd = self._usd_amount_for_ves(900.0)
        invoice = self._create_customer_invoice(amount=1000.0, currency=self.ves)
        payment, wizard = self._register_invoice_payment(
            invoice=invoice,
            amount=payment_amount_usd,
            currency=self.usd,
            apply_igtf=True,
            igtf_included=False,
            return_wizard=True,
        )
        self._assert_wizard_payment_consistency(wizard, payment)

        igtf_line = self._get_payment_igtf_line(payment)
        self.assertTrue(igtf_line)
        expected_igtf_company = abs(sum(igtf_line.mapped("balance")))
        self.assertAlmostEqual(
            abs(sum(igtf_line.mapped("balance"))), expected_igtf_company, places=2
        )
        self.assertGreater(abs(sum(igtf_line.mapped("amount_currency"))), 0.0)

        igtf_group = self._get_igtf_group_from_tax_totals(invoice)
        self.assertTrue(igtf_group)
        self.assertAlmostEqual(
            abs(igtf_group.get("tax_amount_currency", 0.0)),
            abs(invoice.l10n_ve_igtf_collected_amount_currency),
            places=2,
        )
        self.assertAlmostEqual(
            abs(igtf_group.get("tax_amount", 0.0)),
            abs(invoice.l10n_ve_igtf_collected_amount_company_currency),
            places=2,
        )
        self.assertLessEqual(abs(igtf_group.get("tax_amount", 0.0)), invoice.amount_total * 0.03)
        self._assert_no_writeoff_or_exchange_diff(invoice, payment)

    def test_invoice_ves_half_payment_usd_with_igtf(self):
        payment_amount_usd = self._usd_amount_for_ves(50.0)
        invoice = self._create_customer_invoice(amount=100.0, currency=self.ves)
        payment, wizard = self._register_invoice_payment(
            invoice=invoice,
            amount=payment_amount_usd,
            currency=self.usd,
            apply_igtf=True,
            igtf_included=False,
            return_wizard=True,
        )
        self._assert_wizard_payment_consistency(wizard, payment)

        igtf_line = self._get_payment_igtf_line(payment)
        igtf_company = abs(invoice.l10n_ve_igtf_collected_amount_company_currency)
        if igtf_line:
            self.assertAlmostEqual(igtf_company, abs(sum(igtf_line.mapped("balance"))), places=2)
        self.assertLessEqual(
            igtf_company,
            invoice.amount_total * 0.03,
        )

        igtf_group = self._get_igtf_group_from_tax_totals(invoice)
        if igtf_group:
            self.assertAlmostEqual(
                abs(igtf_group.get("tax_amount", 0.0)),
                igtf_company,
                places=2,
            )
        self._assert_no_writeoff_or_exchange_diff(invoice, payment)

    def test_invoice_ves_igtf_limit_matrix_in_bs(self):
        cases = [
            (1.00, 3.00),
            (0.50, 1.45),
            (0.15, 0.39),
            (0.88, 2.63),
        ]
        for payment_ratio, expected_igtf_bs in cases:
            with self.subTest(
                payment_ratio=payment_ratio,
                expected_igtf_bs=expected_igtf_bs,
            ):
                self._assert_igtf_case_in_bs(payment_ratio, expected_igtf_bs)

    def test_invoice_100bs_paid_103bs_in_usd_expected_igtf_3bs(self):
        invoice = self._create_customer_invoice(amount=100.0, currency=self.ves)
        payment, wizard = self._register_invoice_payment(
            invoice=invoice,
            amount=self._usd_amount_for_ves(103.0),
            currency=self.usd,
            apply_igtf=True,
            igtf_included=False,
            return_wizard=True,
        )
        self._assert_wizard_payment_consistency(wizard, payment)

        igtf_line = self._get_payment_igtf_line(payment)
        self.assertTrue(igtf_line)
        self.assertAlmostEqual(abs(sum(igtf_line.mapped("balance"))), 3.0, places=2)

        exchange_accounts = (
            self.company.income_currency_exchange_account_id
            | self.company.expense_currency_exchange_account_id
        )
        exchange_lines = payment.move_id.line_ids.filtered(
            lambda line: line.account_id in exchange_accounts
        )
        for line in exchange_lines:
            self.assertNotAlmostEqual(abs(line.balance), 3.0, places=2)

    def test_invoice_100bs_paid_150pct_in_usd_expected_igtf_3bs(self):
        invoice = self._create_customer_invoice(amount=100.0, currency=self.ves)
        payment, wizard = self._register_invoice_payment(
            invoice=invoice,
            amount=self._usd_amount_for_ves(150.0),
            currency=self.usd,
            apply_igtf=True,
            igtf_included=False,
            return_wizard=True,
        )
        self._assert_wizard_payment_consistency(wizard, payment)

        igtf_line = self._get_payment_igtf_line(payment)
        self.assertTrue(igtf_line)
        self.assertAlmostEqual(abs(sum(igtf_line.mapped("balance"))), 3.0, places=2)
        self.assertAlmostEqual(
            abs(invoice.l10n_ve_igtf_collected_amount_company_currency),
            3.0,
            places=2,
        )

        igtf_group = self._get_igtf_group_from_tax_totals(invoice)
        self.assertTrue(igtf_group)
        self.assertAlmostEqual(abs(igtf_group.get("tax_amount", 0.0)), 3.0, places=2)

        payment_receivable_lines = payment.move_id.line_ids.filtered(
            lambda line: line.account_id.account_type == "asset_receivable"
        )
        self.assertTrue(payment_receivable_lines)
        self.assertGreater(abs(sum(payment_receivable_lines.mapped("amount_residual"))), 0.0)

        exchange_accounts = (
            self.company.income_currency_exchange_account_id
            | self.company.expense_currency_exchange_account_id
        )
        exchange_lines = payment.move_id.line_ids.filtered(
            lambda line: line.account_id in exchange_accounts
        )
        for line in exchange_lines:
            self.assertNotAlmostEqual(abs(line.balance), 3.0, places=2)

    def test_invoice_100bs_paid_in_two_50pct_payments_expected_igtf_3bs(self):
        invoice = self._create_customer_invoice(amount=100.0, currency=self.ves)

        first_payment, first_wizard = self._register_invoice_payment(
            invoice=invoice,
            amount=self._usd_amount_for_ves(50.0),
            currency=self.usd,
            apply_igtf=True,
            igtf_included=False,
            return_wizard=True,
        )
        self._assert_wizard_payment_consistency(first_wizard, first_payment)
        self.assertAlmostEqual(
            abs(invoice.l10n_ve_igtf_collected_amount_company_currency),
            1.45,
            places=3,
        )
        self._assert_no_writeoff_or_exchange_diff(invoice, first_payment)

        second_payment, second_wizard = self._register_invoice_payment(
            invoice=invoice,
            amount=self._usd_amount_for_ves(50.0),
            currency=self.usd,
            apply_igtf=True,
            igtf_included=False,
            return_wizard=True,
        )
        self._assert_wizard_payment_consistency(second_wizard, second_payment)
        self.assertAlmostEqual(
            abs(invoice.l10n_ve_igtf_collected_amount_company_currency),
            2.89,
            places=3,
        )
        igtf_group = self._get_igtf_group_from_tax_totals(invoice)
        self.assertTrue(igtf_group)
        self.assertAlmostEqual(abs(igtf_group.get("tax_amount", 0.0)), 2.89, places=3)
        self._assert_no_writeoff_or_exchange_diff(invoice, second_payment)

    def test_invoice_100bs_payment_010usd_expected_igtf_131bs(self):
        invoice = self._create_customer_invoice(amount=100.0, currency=self.ves)
        payment, wizard = self._register_invoice_payment(
            invoice=invoice,
            amount=0.10,
            currency=self.usd,
            apply_igtf=True,
            igtf_included=False,
            return_wizard=True,
        )
        self._assert_wizard_payment_consistency(wizard, payment)

        self.assertAlmostEqual(
            wizard["l10n_ve_igtf_amount_company_currency"],
            1.31,
            places=2,
        )
        self.assertAlmostEqual(
            abs(invoice.l10n_ve_igtf_collected_amount_company_currency),
            1.31,
            places=2,
        )
        igtf_group = self._get_igtf_group_from_tax_totals(invoice)
        self.assertTrue(igtf_group)
        self.assertAlmostEqual(abs(igtf_group.get("tax_amount", 0.0)), 1.31, places=2)

    def _expected_igtf_bs_from_payment(self, payment_amount, payment_currency):
        payment_amount_bs = self.ves.round(
            payment_currency._convert(
                payment_amount,
                self.ves,
                self.company,
                self.test_date,
            )
        )
        return self.ves.round(payment_amount_bs * 0.03)

    def _invoice_max_igtf_bs(self, invoice):
        invoice_total_bs = self.ves.round(
            invoice.currency_id._convert(
                invoice.amount_total,
                self.ves,
                self.company,
                invoice.date,
            )
        )
        return self.ves.round(invoice_total_bs * 0.03)

    def test_invoice_usd_payment_usd_with_igtf_base_in_bs(self):
        invoice = self._create_customer_invoice(amount=100.0, currency=self.usd)
        payment, wizard = self._register_invoice_payment(
            invoice=invoice,
            amount=100.0,
            currency=self.usd,
            apply_igtf=True,
            igtf_included=False,
            return_wizard=True,
        )
        self._assert_wizard_payment_consistency(wizard, payment)

        expected_igtf_bs = self._expected_igtf_bs_from_payment(100.0, self.usd)
        max_igtf_bs = self._invoice_max_igtf_bs(invoice)
        expected_igtf_bs = min(expected_igtf_bs, max_igtf_bs)
        self.assertAlmostEqual(
            abs(invoice.l10n_ve_igtf_collected_amount_company_currency),
            expected_igtf_bs,
            places=2,
        )
        self.assertAlmostEqual(
            payment.l10n_ve_igtf_amount_company_currency,
            expected_igtf_bs,
            places=2,
        )
        igtf_group = self._get_igtf_group_from_tax_totals(invoice)
        self.assertTrue(igtf_group)
        self.assertAlmostEqual(
            abs(igtf_group.get("tax_amount", 0.0)),
            expected_igtf_bs,
            places=2,
        )

    def test_invoice_usd_half_payment_usd_with_igtf_base_in_bs(self):
        invoice = self._create_customer_invoice(amount=100.0, currency=self.usd)
        payment, wizard = self._register_invoice_payment(
            invoice=invoice,
            amount=50.0,
            currency=self.usd,
            apply_igtf=True,
            igtf_included=False,
            return_wizard=True,
        )
        self._assert_wizard_payment_consistency(wizard, payment)

        expected_igtf_bs = self._expected_igtf_bs_from_payment(50.0, self.usd)
        self.assertAlmostEqual(
            abs(invoice.l10n_ve_igtf_collected_amount_company_currency),
            expected_igtf_bs,
            places=2,
        )
        self.assertAlmostEqual(
            payment.l10n_ve_igtf_amount_company_currency,
            expected_igtf_bs,
            places=2,
        )
        igtf_group = self._get_igtf_group_from_tax_totals(invoice)
        self.assertTrue(igtf_group)
        self.assertAlmostEqual(
            abs(igtf_group.get("tax_amount", 0.0)),
            expected_igtf_bs,
            places=2,
        )

    def test_invoice_usd_igtf_limit_matrix_in_bs(self):
        invoice_amount_usd = 100.0
        ratios = [1.00, 0.50, 0.15, 0.88]
        for payment_ratio in ratios:
            with self.subTest(payment_ratio=payment_ratio):
                invoice = self._create_customer_invoice(amount=invoice_amount_usd, currency=self.usd)
                payment_amount_usd = self.usd.round(invoice_amount_usd * payment_ratio)
                payment, wizard = self._register_invoice_payment(
                    invoice=invoice,
                    amount=payment_amount_usd,
                    currency=self.usd,
                    apply_igtf=True,
                    igtf_included=False,
                    return_wizard=True,
                )
                self._assert_wizard_payment_consistency(wizard, payment)

                expected_igtf_bs = self._expected_igtf_bs_from_payment(payment_amount_usd, self.usd)
                max_igtf_bs = self._invoice_max_igtf_bs(invoice)
                expected_igtf_bs = min(expected_igtf_bs, max_igtf_bs)
                self.assertAlmostEqual(
                    abs(invoice.l10n_ve_igtf_collected_amount_company_currency),
                    expected_igtf_bs,
                    places=2,
                )
                self.assertLessEqual(
                    abs(invoice.l10n_ve_igtf_collected_amount_company_currency),
                    max_igtf_bs,
                )

    def test_invoice_usd_paid_150pct_in_usd_igtf_capped_in_bs(self):
        invoice = self._create_customer_invoice(amount=100.0, currency=self.usd)
        payment, wizard = self._register_invoice_payment(
            invoice=invoice,
            amount=150.0,
            currency=self.usd,
            apply_igtf=True,
            igtf_included=False,
            return_wizard=True,
        )
        self._assert_wizard_payment_consistency(wizard, payment)

        max_igtf_bs = self._invoice_max_igtf_bs(invoice)
        self.assertAlmostEqual(
            abs(invoice.l10n_ve_igtf_collected_amount_company_currency),
            max_igtf_bs,
            places=2,
        )
        self.assertAlmostEqual(
            payment.l10n_ve_igtf_amount_company_currency,
            max_igtf_bs,
            places=2,
        )
        igtf_group = self._get_igtf_group_from_tax_totals(invoice)
        self.assertTrue(igtf_group)
        self.assertAlmostEqual(abs(igtf_group.get("tax_amount", 0.0)), max_igtf_bs, places=2)

    def test_invoice_usd_paid_103pct_in_usd_igtf_capped_in_bs(self):
        invoice = self._create_customer_invoice(amount=100.0, currency=self.usd)
        payment_amount_usd = self.usd.round(103.0)
        payment, wizard = self._register_invoice_payment(
            invoice=invoice,
            amount=payment_amount_usd,
            currency=self.usd,
            apply_igtf=True,
            igtf_included=False,
            return_wizard=True,
        )
        self._assert_wizard_payment_consistency(wizard, payment)

        max_igtf_bs = self._invoice_max_igtf_bs(invoice)
        expected_igtf_bs = min(
            self._expected_igtf_bs_from_payment(payment_amount_usd, self.usd),
            max_igtf_bs,
        )
        self.assertAlmostEqual(
            abs(invoice.l10n_ve_igtf_collected_amount_company_currency),
            expected_igtf_bs,
            places=2,
        )
        self.assertAlmostEqual(
            payment.l10n_ve_igtf_amount_company_currency,
            expected_igtf_bs,
            places=2,
        )
        igtf_group = self._get_igtf_group_from_tax_totals(invoice)
        self.assertTrue(igtf_group)
        self.assertAlmostEqual(
            abs(igtf_group.get("tax_amount", 0.0)),
            expected_igtf_bs,
            places=2,
        )

    def test_invoice_usd_paid_in_two_50pct_payments_igtf_capped_in_bs(self):
        invoice = self._create_customer_invoice(amount=100.0, currency=self.usd)
        max_igtf_bs = self._invoice_max_igtf_bs(invoice)

        first_payment, first_wizard = self._register_invoice_payment(
            invoice=invoice,
            amount=50.0,
            currency=self.usd,
            apply_igtf=True,
            igtf_included=False,
            return_wizard=True,
        )
        self._assert_wizard_payment_consistency(first_wizard, first_payment)
        expected_first_igtf_bs = min(
            self._expected_igtf_bs_from_payment(50.0, self.usd),
            max_igtf_bs,
        )
        self.assertAlmostEqual(
            abs(invoice.l10n_ve_igtf_collected_amount_company_currency),
            expected_first_igtf_bs,
            places=2,
        )

        second_payment, second_wizard = self._register_invoice_payment(
            invoice=invoice,
            amount=50.0,
            currency=self.usd,
            apply_igtf=True,
            igtf_included=False,
            return_wizard=True,
        )
        self._assert_wizard_payment_consistency(second_wizard, second_payment)
        self.assertAlmostEqual(
            abs(invoice.l10n_ve_igtf_collected_amount_company_currency),
            max_igtf_bs,
            places=2,
        )
        self.assertAlmostEqual(
            second_payment.l10n_ve_igtf_amount_company_currency
            + first_payment.l10n_ve_igtf_amount_company_currency,
            max_igtf_bs,
            places=2,
        )
        igtf_group = self._get_igtf_group_from_tax_totals(invoice)
        self.assertTrue(igtf_group)
        self.assertAlmostEqual(
            abs(igtf_group.get("tax_amount", 0.0)),
            max_igtf_bs,
            places=2,
        )

    def test_invoice_usd_payment_010usd_expected_igtf_in_bs(self):
        invoice = self._create_customer_invoice(amount=100.0, currency=self.usd)
        payment_amount_usd = 0.10
        payment, wizard = self._register_invoice_payment(
            invoice=invoice,
            amount=payment_amount_usd,
            currency=self.usd,
            apply_igtf=True,
            igtf_included=False,
            return_wizard=True,
        )
        self._assert_wizard_payment_consistency(wizard, payment)

        expected_igtf_bs = self._expected_igtf_bs_from_payment(payment_amount_usd, self.usd)
        self.assertAlmostEqual(
            wizard["l10n_ve_igtf_amount_company_currency"],
            expected_igtf_bs,
            places=2,
        )
        self.assertAlmostEqual(
            payment.l10n_ve_igtf_amount_company_currency,
            expected_igtf_bs,
            places=2,
        )
        self.assertAlmostEqual(
            abs(invoice.l10n_ve_igtf_collected_amount_company_currency),
            expected_igtf_bs,
            places=2,
        )

    def test_invoice_ves_include_igtf_in_amount_computes_correct_addition(self):
        invoice = self._create_customer_invoice(amount=100.0, currency=self.ves)
        payment_amount_usd = self._usd_amount_for_ves(103.0)
        payment, wizard = self._register_invoice_payment(
            invoice=invoice,
            amount=payment_amount_usd,
            currency=self.usd,
            apply_igtf=True,
            igtf_included=True,
            return_wizard=True,
        )
        self._assert_wizard_payment_consistency(wizard, payment)

        self.assertTrue(wizard["l10n_ve_igtf_included"])
        self.assertAlmostEqual(
            wizard["l10n_ve_base_amount_company_currency"],
            100.0,
            places=2,
        )
        self.assertAlmostEqual(
            wizard["l10n_ve_igtf_amount_company_currency"],
            3.0,
            places=2,
        )
        self.assertAlmostEqual(
            payment.l10n_ve_igtf_amount_company_currency,
            3.0,
            places=2,
        )

    def test_invoice_usd_include_igtf_in_amount_computes_correct_addition(self):
        invoice = self._create_customer_invoice(amount=100.0, currency=self.usd)
        payment, wizard = self._register_invoice_payment(
            invoice=invoice,
            amount=103.0,
            currency=self.usd,
            apply_igtf=True,
            igtf_included=True,
            return_wizard=True,
        )
        self._assert_wizard_payment_consistency(wizard, payment)

        max_igtf_bs = self._invoice_max_igtf_bs(invoice)
        self.assertTrue(wizard["l10n_ve_igtf_included"])
        self.assertAlmostEqual(
            wizard["l10n_ve_base_amount_company_currency"],
            self.ves.round(max_igtf_bs / 0.03),
            places=2,
        )
        self.assertAlmostEqual(
            wizard["l10n_ve_igtf_amount_company_currency"],
            max_igtf_bs,
            places=2,
        )
        self.assertAlmostEqual(
            payment.l10n_ve_igtf_amount_company_currency,
            max_igtf_bs,
            places=2,
        )

    def test_invoice_ves_amount_above_total_plus_igtf_turns_on_included(self):
        invoice = self._create_customer_invoice(amount=100.0, currency=self.ves)
        wizard = self._create_payment_register_wizard(
            invoice=invoice,
            amount=self._usd_amount_for_ves(110.0),
            currency=self.usd,
            apply_igtf=True,
            igtf_included=False,
        )
        wizard._onchange_l10n_ve_validate_amount_max_with_igtf()
        self.assertTrue(wizard.l10n_ve_igtf_included)

    def test_invoice_usd_amount_above_total_plus_igtf_turns_on_included(self):
        invoice = self._create_customer_invoice(amount=100.0, currency=self.usd)
        wizard = self._create_payment_register_wizard(
            invoice=invoice,
            amount=104.0,
            currency=self.usd,
            apply_igtf=True,
            igtf_included=False,
        )
        wizard._onchange_l10n_ve_validate_amount_max_with_igtf()
        self.assertTrue(wizard.l10n_ve_igtf_included)

    def test_invoice_100usd_paid_50_then_53_included_invoice_fully_paid(self):
        invoice = self._create_customer_invoice(amount=100.0, currency=self.usd)

        first_payment, first_wizard = self._register_invoice_payment(
            invoice=invoice,
            amount=50.0,
            currency=self.usd,
            apply_igtf=True,
            igtf_included=False,
            return_wizard=True,
        )
        self._assert_wizard_payment_consistency(first_wizard, first_payment)

        second_payment, second_wizard = self._register_invoice_payment(
            invoice=invoice,
            amount=53.0,
            currency=self.usd,
            apply_igtf=True,
            igtf_included=True,
            return_wizard=True,
        )
        self._assert_wizard_payment_consistency(second_wizard, second_payment)

        invoice.invalidate_recordset()
        self.assertTrue(
            invoice.currency_id.is_zero(abs(invoice.amount_residual)),
            "La factura debe quedar completamente pagada.",
        )

    def test_wizard_payment_difference_100usd_50_then_53_included_is_zero(self):
        invoice = self._create_customer_invoice(amount=100.0, currency=self.usd)

        self._register_invoice_payment(
            invoice=invoice,
            amount=50.0,
            currency=self.usd,
            apply_igtf=True,
            igtf_included=False,
        )

        wizard = self._create_payment_register_wizard(
            invoice=invoice,
            amount=53.0,
            currency=self.usd,
            apply_igtf=True,
            igtf_included=True,
        )
        self.assertAlmostEqual(wizard.payment_difference, 0.0, places=2)

    def test_wizard_payment_difference_100usd_50_then_55_included_is_minus_two(self):
        invoice = self._create_customer_invoice(amount=100.0, currency=self.usd)

        self._register_invoice_payment(
            invoice=invoice,
            amount=50.0,
            currency=self.usd,
            apply_igtf=True,
            igtf_included=False,
        )

        wizard = self._create_payment_register_wizard(
            invoice=invoice,
            amount=55.0,
            currency=self.usd,
            apply_igtf=True,
            igtf_included=True,
        )
        self.assertAlmostEqual(wizard.payment_difference, -2.0, places=2)
