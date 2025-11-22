from odoo import models, api, _, fields
from odoo.tools.misc import formatLang
from odoo.tools.float_utils import float_round, float_is_zero

import logging

_logger = logging.getLogger(__name__)


class AccountTax(models.Model):
    _inherit = "account.tax"

    @api.model
    def _get_tax_totals_summary(self, base_lines, currency, company, cash_rounding=None):
        """
        Extend the standard tax totals summary to include IGTF information.

        All IGTF amounts (base and tax) are expressed in company currency (Bs).
        """
        tax_totals = super()._get_tax_totals_summary(
            base_lines=base_lines,
            currency=currency,
            company=company,
            cash_rounding=cash_rounding,
        )

        company_currency = company.currency_id
        invoice = False
        order = False

        # ---------------------------------------------------------------------
        # Detect source document (invoice / sale order) from base_lines
        # ---------------------------------------------------------------------
        for base_line in base_lines or []:
            record = base_line.get("record")
            if not record:
                continue

            if record._name == "account.move.line":
                invoice = record.move_id
                break
            elif record._name == "sale.order.line":
                order = record.order_id
                break

        # Determine document currency
        document_currency = (
            invoice.currency_id
            if invoice
            else order.currency_id
            if order
            else currency
        )

        # ---------------------------------------------------------------------
        # IGTF config
        # ---------------------------------------------------------------------
        float_igtf_percentage = company.igtf_percentage or 0.0
        igtf_percentage = float_igtf_percentage / 100.0

        apply_igtf = False
        is_igtf_suggested = False
        igtf_base_company = 0.0

        # ---------------------------------------------------------------------
        # No IGTF if document is already in company currency (Bs)
        # ---------------------------------------------------------------------
        if document_currency == company_currency or float_is_zero(
            igtf_percentage, precision_digits=4
        ):
            tax_totals["igtf"] = {
                "apply_igtf": False,
                "name": f"{float_igtf_percentage} %",
                "igtf_base_amount": 0.0,
                "igtf_amount": 0.0,
                "formatted_igtf_amount": formatLang(
                    self.env, 0.0, currency_obj=company_currency
                ),
                "formatted_igtf_base_amount": formatLang(
                    self.env, 0.0, currency_obj=company_currency
                ),
                "is_igtf_suggested": False,
            }
            # Total con IGTF = solo total en Bs (sin IGTF)
            base_total_company = 0.0
            if invoice:
                if invoice.currency_id == company_currency:
                    base_total_company = invoice.amount_total
                else:
                    date = invoice.invoice_date or fields.Date.context_today(self)
                    base_total_company = invoice.currency_id._convert(
                        invoice.amount_total,
                        company_currency,
                        company,
                        date,
                    )
            elif order:
                date = (order.date_order and order.date_order.date()) or fields.Date.context_today(self)
                if order.currency_id == company_currency:
                    base_total_company = order.amount_total
                else:
                    base_total_company = order.currency_id._convert(
                        order.amount_total,
                        company_currency,
                        company,
                        date,
                    )

            tax_totals["amount_total_igtf"] = base_total_company
            tax_totals["formatted_amount_total_igtf"] = formatLang(
                self.env,
                base_total_company,
                currency_obj=company_currency,
            )
            return tax_totals

        # ---------------------------------------------------------------------
        # Helper: convert a document amount to company currency
        # ---------------------------------------------------------------------
        def _to_company(amount, date):
            return document_currency._convert(
                amount,
                company_currency,
                company,
                date,
            )

        # ---------------------------------------------------------------------
        # Base IGTF for invoices
        # ---------------------------------------------------------------------
        if invoice:
            date = invoice.invoice_date or fields.Date.context_today(self)

            # 1) Explicit BI IGTF on invoice overrides suggestion
            if getattr(invoice, "bi_igtf", False):
                is_igtf_suggested = False

                if self._context.get("from_widget"):
                    # Base = sum of payments flagged for IGTF (amounts in doc currency)
                    base_doc = self.process_payments_to_igtf(invoice) or 0.0
                    igtf_base_company = _to_company(base_doc, date)
                else:
                    # invoice.bi_igtf is stored in company currency
                    invoice_total_company = _to_company(
                        invoice.amount_total, date
                    )
                    igtf_base_company = min(invoice.bi_igtf, invoice_total_company)

            # 2) Suggested IGTF over unpaid invoices
            elif (
                company.show_igtf_suggested_account_move
                and invoice.payment_state == "not_paid"
            ):
                is_igtf_suggested = True
                igtf_base_company = _to_company(invoice.amount_total, date)

        # ---------------------------------------------------------------------
        # Base IGTF for sale orders
        # ---------------------------------------------------------------------
        elif order and company.show_igtf_suggested_sale_order:
            is_igtf_suggested = True
            date = (order.date_order and order.date_order.date()) or fields.Date.context_today(
                self
            )
            if order.currency_id == company_currency:
                igtf_base_company = order.amount_total
            else:
                igtf_base_company = order.currency_id._convert(
                    order.amount_total,
                    company_currency,
                    company,
                    date,
                )

        # ---------------------------------------------------------------------
        # Final rounding and amount computation (all in company currency)
        # ---------------------------------------------------------------------
        igtf_base_amount = float_round(
            igtf_base_company or 0.0,
            precision_rounding=company_currency.rounding,
        )

        if not float_is_zero(
            igtf_base_amount, precision_rounding=company_currency.rounding
        ):
            apply_igtf = True

        # Calculate IGTF amount
        # If we have a foreign currency, calculate tax in that currency first then convert
        # to avoid rounding discrepancies.
        if apply_igtf and document_currency != company_currency:
            # Re-determine date and base in document currency to calculate tax
            # This is a bit repetitive but ensures we use the correct source amount
            doc_amount_for_tax = 0.0
            calc_date = fields.Date.context_today(self)

            if invoice:
                calc_date = invoice.invoice_date or fields.Date.context_today(self)
                if getattr(invoice, "bi_igtf", False):
                    if self._context.get("from_widget"):
                         doc_amount_for_tax = self.process_payments_to_igtf(invoice) or 0.0
                    else:
                         # Fallback to base company if we can't easily get doc amount
                         # or if bi_igtf is manually set in Bs.
                         # In this case we stick to the standard calculation below
                         doc_amount_for_tax = 0.0
                elif is_igtf_suggested:
                    doc_amount_for_tax = invoice.amount_total

            elif order and is_igtf_suggested:
                 calc_date = (order.date_order and order.date_order.date()) or fields.Date.context_today(self)
                 doc_amount_for_tax = order.amount_total

            if doc_amount_for_tax:
                igtf_amount_doc = doc_amount_for_tax * igtf_percentage
                igtf_amount = _to_company(igtf_amount_doc, calc_date)
                igtf_amount = float_round(
                    igtf_amount,
                    precision_rounding=company_currency.rounding,
                )
            else:
                # Fallback to standard calculation
                igtf_amount = float_round(
                    igtf_base_amount * igtf_percentage,
                    precision_rounding=company_currency.rounding,
                )
        else:
            igtf_amount = float_round(
                igtf_base_amount * igtf_percentage,
                precision_rounding=company_currency.rounding,
            )

        # ---------------------------------------------------------------------
        # Compute total of the document in company currency
        # ---------------------------------------------------------------------
        base_total_company = 0.0
        if invoice:
            date = invoice.invoice_date or fields.Date.context_today(self)
            base_total_company = _to_company(invoice.amount_total, date)
        elif order:
            date = (order.date_order and order.date_order.date()) or fields.Date.context_today(
                self
            )
            if order.currency_id == company_currency:
                base_total_company = order.amount_total
            else:
                base_total_company = order.currency_id._convert(
                    order.amount_total,
                    company_currency,
                    company,
                    date,
                )

        amount_total_igtf = float_round(
            base_total_company + igtf_amount,
            precision_rounding=company_currency.rounding,
        )

        # ---------------------------------------------------------------------
        # Enrich tax_totals with IGTF data (all in Bs)
        # ---------------------------------------------------------------------
        tax_totals["igtf"] = {
            "apply_igtf": apply_igtf,
            "name": f"{float_igtf_percentage} %",
            "igtf_base_amount": igtf_base_amount,
            "igtf_amount": igtf_amount,
            "formatted_igtf_amount": formatLang(
                self.env, igtf_amount, currency_obj=company_currency
            ),
            "formatted_igtf_base_amount": formatLang(
                self.env, igtf_base_amount, currency_obj=company_currency
            ),
            "is_igtf_suggested": is_igtf_suggested,
        }

        tax_totals["amount_total_igtf"] = amount_total_igtf
        tax_totals["formatted_amount_total_igtf"] = formatLang(
            self.env,
            amount_total_igtf,
            currency_obj=company_currency,
        )

        return tax_totals

    # -------------------------------------------------------------------------
    # Helper: payments IGTF base (still in document currency here)
    # -------------------------------------------------------------------------
    def process_payments_to_igtf(self, invoice):
        invoice_payments_widget = invoice.invoice_payments_widget or {}
        content = invoice_payments_widget.get("content") or []

        if not content:
            return 0.0

        payments_id = [
            payment["account_payment_id"]
            for payment in content
            if "account_payment_id" in payment
        ]

        payments = self.env["account.payment"].browse(payments_id)
        payments_igtf = payments.filtered(lambda p: p.is_igtf_on_foreign_exchange)

        amount_to_igtf = [
            payment["amount"]
            for payment in content
            if "account_payment_id" in payment
            and payment["account_payment_id"] in payments_igtf.ids
        ]
        return sum(amount_to_igtf)

