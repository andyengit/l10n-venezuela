from odoo import Command, fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class TestL10nVeAdvanceCommon(AccountTestInvoicingCommon):
    @classmethod
    @AccountTestInvoicingCommon.setup_country("ve")
    @AccountTestInvoicingCommon.setup_chart_template("ve_seniat")
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company_data_ve = cls.company_data
        cls.receivable_account = cls.company_data_ve["default_account_receivable"]
        cls.revenue_account = cls.company_data_ve["default_account_revenue"]
        cls.bank_journal = cls.company_data_ve["default_journal_bank"]
        cls.sale_journal = cls.company_data_ve["default_journal_sale"]
        cls.currency = cls.company.currency_id
        cls.test_date = fields.Date.from_string("2026-03-12")

        cls.advance_account = cls.env["account.account"].with_company(cls.company).create(
            {
                "name": "Advance Liability Test",
                "code": "2399001",
                "account_type": "liability_current",
                "company_ids": [Command.set([cls.company.id])],
                "reconcile": True,
            }
        )
        cls.company.l10n_ve_advance_liability_account_id = cls.advance_account

        cls.partner = cls.env["res.partner"].with_company(cls.company).create(
            {
                "name": "Advance Partner",
                "vat": "V12345678",
                "company_id": False,
                "property_account_receivable_id": cls.receivable_account.id,
                "property_account_payable_id": cls.company_data_ve["default_account_payable"].id,
            }
        )
        cls.inbound_method = cls.bank_journal.inbound_payment_method_line_ids[:1]

    def _create_customer_invoice(self, amount):
        invoice = (
            self.env["account.move"]
            .with_company(self.company)
            .create(
                {
                    "move_type": "out_invoice",
                    "company_id": self.company.id,
                    "journal_id": self.sale_journal.id,
                    "partner_id": self.partner.id,
                    "currency_id": self.currency.id,
                    "invoice_date": self.test_date,
                    "date": self.test_date,
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "name": "Invoice line",
                                "quantity": 1.0,
                                "price_unit": amount,
                                "account_id": self.revenue_account.id,
                                "tax_ids": [Command.clear()],
                            }
                        )
                    ],
                }
            )
        )
        invoice.action_post()
        return invoice

    def _create_manual_payment(self, amount):
        return (
            self.env["account.payment"]
            .with_company(self.company)
            .create(
                {
                    "date": self.test_date,
                    "amount": amount,
                    "payment_type": "inbound",
                    "partner_type": "customer",
                    "partner_id": self.partner.id,
                    "journal_id": self.bank_journal.id,
                    "payment_method_line_id": self.inbound_method.id,
                    "currency_id": self.currency.id,
                    "company_id": self.company.id,
                    "memo": "Manual advance",
                }
            )
        )

    def _register_payment_from_invoice(self, invoice, amount):
        wizard = (
            self.env["account.payment.register"]
            .with_company(self.company)
            .with_context(active_model="account.move", active_ids=invoice.ids)
            .create(
                {
                    "company_id": self.company.id,
                    "journal_id": self.bank_journal.id,
                    "payment_date": self.test_date,
                    "amount": amount,
                    "currency_id": self.currency.id,
                    "group_payment": True,
                }
            )
        )
        return wizard._create_payments()
