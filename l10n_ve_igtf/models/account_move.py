from odoo import _, api, fields, models
from odoo.tools.misc import formatLang


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_ve_igtf_collected_amount_currency = fields.Monetary(
        string="IGTF %",
        currency_field="currency_id",
        compute="_compute_l10n_ve_igtf_collected_amounts",
        store=False,
        readonly=True,
    )
    l10n_ve_igtf_collected_amount_company_currency = fields.Monetary(
        string="IGTF % (Company Currency)",
        currency_field="company_currency_id",
        compute="_compute_l10n_ve_igtf_collected_amounts",
        store=False,
        readonly=True,
    )
    l10n_ve_igtf_residual_amount_company_currency = fields.Monetary(
        string="IGTF Residual (Company Currency)",
        currency_field="company_currency_id",
        compute="_compute_l10n_ve_igtf_collected_amounts",
        store=False,
        readonly=True,
    )

    def _l10n_ve_igtf_get_collected_amounts(self, include_base=False):
        """
        Compute the IGTF collected for this invoice from reconciled IGTF payments.

        Parameters
        ----------
        None

        Returns
        -------
        tuple[float, float]
            A tuple `(amount_in_invoice_currency, amount_in_company_currency)`.

        Notes
        -----
        The computation allocates the gross payment amount proportionally to this invoice based on the net
        amount reconciled between the payment receivable line and the invoice. The resulting base is capped
        to the invoice total to avoid overcounting on overpayments.
        """
        self.ensure_one()

        if self.country_code != "VE":
            if include_base:
                return 0.0, 0.0, 0.0, 0.0
            return 0.0, 0.0

        if not self.is_sale_document(include_receipts=True):
            if include_base:
                return 0.0, 0.0, 0.0, 0.0
            return 0.0, 0.0

        company = self.company_id
        if not company.l10n_ve_igtf_account_id:
            if include_base:
                return 0.0, 0.0, 0.0, 0.0
            return 0.0, 0.0

        percent = company.l10n_ve_igtf_percent or 0.0
        if percent <= 0.0:
            if include_base:
                return 0.0, 0.0, 0.0, 0.0
            return 0.0, 0.0

        sign = 1.0
        if self.move_type == "out_refund":
            sign = -1.0

        p = percent / 100.0
        invoice_currency = self.currency_id
        invoice_total = invoice_currency.round(abs(self.amount_total))
        if invoice_currency.is_zero(invoice_total):
            if include_base:
                return 0.0, 0.0, 0.0, 0.0
            return 0.0, 0.0

        receivable_lines = self.line_ids.filtered(
            lambda line: line.account_id.account_type == "asset_receivable"
        )
        partials = (
            receivable_lines.matched_debit_ids | receivable_lines.matched_credit_ids
        ).filtered(
            lambda pr: (
                not pr.exchange_move_id
                or pr.debit_move_id.payment_id
                or pr.credit_move_id.payment_id
            )
        )
        if not partials:
            if include_base:
                return 0.0, 0.0, 0.0, 0.0
            return 0.0, 0.0

        by_pay_line = {}
        for pr in partials:
            pay_line = (
                pr.debit_move_id
                if pr.debit_move_id.payment_id
                else pr.credit_move_id
                if pr.credit_move_id.payment_id
                else False
            )
            if not pay_line:
                continue
            payment = pay_line.payment_id
            if not payment or not payment.exists() or not payment.l10n_ve_apply_igtf:
                continue
            entry = by_pay_line.setdefault(
                pay_line, {"payment": payment, "net_invoice": 0.0}
            )
            line_currency = (
                pr.debit_currency_id
                if pr.debit_move_id == pay_line
                else pr.credit_currency_id
            )
            amt = (
                abs(pr.debit_amount_currency)
                if pr.debit_move_id == pay_line
                else abs(pr.credit_amount_currency)
            )
            entry["net_invoice"] += (
                amt
                if line_currency == invoice_currency
                else line_currency._convert(amt, invoice_currency, company, pr.max_date)
            )

        if not by_pay_line:
            if include_base:
                return 0.0, 0.0, 0.0, 0.0
            return 0.0, 0.0

        base_total = 0.0
        for pay_line, data in by_pay_line.items():
            payment = data["payment"]
            net_invoice = invoice_currency.round(data["net_invoice"])
            if invoice_currency.is_zero(net_invoice):
                continue

            matched_partials = (
                pay_line.matched_debit_ids | pay_line.matched_credit_ids
            ).filtered(
                lambda pr: (
                    not pr.exchange_move_id
                    or pr.debit_move_id.payment_id
                    or pr.credit_move_id.payment_id
                )
            )
            total_net = 0.0
            for pr in matched_partials:
                line_currency = (
                    pr.debit_currency_id
                    if pr.debit_move_id == pay_line
                    else pr.credit_currency_id
                )
                amt = (
                    abs(pr.debit_amount_currency)
                    if pr.debit_move_id == pay_line
                    else abs(pr.credit_amount_currency)
                )
                total_net += (
                    amt
                    if line_currency == invoice_currency
                    else line_currency._convert(
                        amt, invoice_currency, company, pr.max_date
                    )
                )
            total_net = invoice_currency.round(total_net)
            if invoice_currency.is_zero(total_net):
                continue

            payment_amount_invoice_currency = (
                payment.amount
                if payment.currency_id == invoice_currency
                else payment.currency_id._convert(
                    payment.amount, invoice_currency, company, payment.date
                )
            )
            payment_amount_invoice_currency = invoice_currency.round(
                payment_amount_invoice_currency
            )
            if invoice_currency.is_zero(payment_amount_invoice_currency):
                continue

            base_total += payment_amount_invoice_currency * (net_invoice / total_net)

        base_total = min(invoice_currency.round(base_total), invoice_total)
        igtf_invoice_currency = invoice_currency.round(sign * (base_total * p))
        base_total_company = company.currency_id.round(
            invoice_currency._convert(
                base_total,
                company.currency_id,
                company,
                self.date,
            )
        )
        igtf_company_currency = company.currency_id.round(sign * (base_total_company * p))
        base_total_signed = invoice_currency.round(sign * base_total)
        base_total_company_signed = company.currency_id.round(sign * base_total_company)
        if invoice_currency.is_zero(igtf_invoice_currency) and company.currency_id.is_zero(
            igtf_company_currency
        ):
            if include_base:
                return base_total_signed, base_total_company_signed, 0.0, 0.0
            return 0.0, 0.0
        if include_base:
            return (
                base_total_signed,
                base_total_company_signed,
                igtf_invoice_currency,
                igtf_company_currency,
            )
        return igtf_invoice_currency, igtf_company_currency

    def _l10n_ve_igtf_get_residual_company_amount(self):
        self.ensure_one()
        if self.country_code != "VE" or not self.is_sale_document(include_receipts=True):
            return 0.0
        percent = self.company_id.l10n_ve_igtf_percent or 0.0
        if percent <= 0.0:
            return 0.0
        invoice_total_company = self.company_currency_id.round(
            self.currency_id._convert(
                abs(self.amount_total),
                self.company_currency_id,
                self.company_id,
                self.date,
            )
        )
        max_igtf = self.company_currency_id.round(
            invoice_total_company * (percent / 100.0)
        )
        _amt_cur, collected_company = self._l10n_ve_igtf_get_collected_amounts()
        residual = max_igtf - abs(collected_company)
        return self.company_currency_id.round(max(residual, 0.0))

    @api.depends(
        "move_type", "line_ids.amount_residual", "line_ids.amount_residual_currency"
    )
    def _compute_l10n_ve_igtf_collected_amounts(self):
        """
        Compute IGTF collected fields for display purposes.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        for move in self:
            if move.country_code != "VE":
                move.l10n_ve_igtf_collected_amount_currency = 0.0
                move.l10n_ve_igtf_collected_amount_company_currency = 0.0
                move.l10n_ve_igtf_residual_amount_company_currency = 0.0
                continue
            amt_cur, amt_comp = move._l10n_ve_igtf_get_collected_amounts()
            move.l10n_ve_igtf_collected_amount_currency = amt_cur
            move.l10n_ve_igtf_collected_amount_company_currency = amt_comp
            move.l10n_ve_igtf_residual_amount_company_currency = (
                move._l10n_ve_igtf_get_residual_company_amount()
            )

    def l10n_ve_igtf_get_unreconcile_action(self, partial_id):
        """
        Build an action that prompts the user when unreconciling an IGTF payment.

        Parameters
        ----------
        partial_id : int
            ID of the `account.partial.reconcile` being removed from this invoice.

        Returns
        -------
        dict | bool
            An `ir.actions.act_window` dictionary to open the wizard if the payment is an IGTF payment;
            otherwise `False` to fall back to the standard behavior.
        """
        self.ensure_one()

        if self.country_code != "VE":
            return False

        partial = self.env["account.partial.reconcile"].browse(partial_id)
        if not partial.exists():
            return False

        payment = partial.debit_move_id.payment_id or partial.credit_move_id.payment_id
        if not payment or not payment.exists():
            return False

        if not payment.l10n_ve_apply_igtf:
            return False

        return {
            "type": "ir.actions.act_window",
            "name": _("IGTF Payment"),
            "res_model": "l10n_ve_igtf.unreconcile.payment.wizard",
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "new",
            "context": {
                "default_move_id": self.id,
                "default_partial_id": partial.id,
                "default_payment_id": payment.id,
            },
        }

    @api.depends_context("lang")
    @api.depends(
        "invoice_line_ids.currency_rate",
        "invoice_line_ids.tax_base_amount",
        "invoice_line_ids.tax_line_id",
        "invoice_line_ids.price_total",
        "invoice_line_ids.price_subtotal",
        "invoice_payment_term_id",
        "partner_id",
        "currency_id",
        "line_ids.amount_residual",
        "line_ids.amount_residual_currency",
        "move_type",
    )
    def _compute_tax_totals(self):
        """
        Compute invoice tax totals and inject an IGTF collected row when applicable.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Notes
        -----
        This only affects display. It does not change accounting totals nor taxes computation.
        The IGTF amount is added to the total_amount to include it in the final invoice total.
        """
        super()._compute_tax_totals()
        for move in self:
            if move.country_code != "VE":
                continue
            if (
                not move.tax_totals
                or not move.is_invoice(include_receipts=True)
                or not move.is_sale_document(include_receipts=True)
            ):
                continue
            (
                igtf_base_amount_currency,
                igtf_base_amount_company_currency,
                igtf_amount_currency,
                igtf_amount_company_currency,
            ) = move._l10n_ve_igtf_get_collected_amounts(include_base=True)
            if not move.currency_id:
                continue
            totals = dict(move.tax_totals)
            subtotals = list(totals.get("subtotals") or [])
            percent = move.company_id.l10n_ve_igtf_percent or 0
            percent_str = int(percent) if percent == int(percent) else percent
            igtf_tax_group = {
                "id": -1,
                "involved_tax_ids": [],
                "group_name": _("IGTF %(percent)s %%") % {"percent": percent_str},
                "group_label": False,
                "base_amount_currency": igtf_base_amount_currency,
                "display_base_amount_currency": igtf_base_amount_currency,
                "tax_amount_currency": igtf_amount_currency,
                "base_amount": igtf_base_amount_company_currency,
                "display_base_amount": igtf_base_amount_company_currency,
                "tax_amount": igtf_amount_company_currency,
            }
            if subtotals:
                last_subtotal = subtotals[-1]
                last_subtotal["tax_groups"] = list(
                    last_subtotal.get("tax_groups") or []
                ) + [igtf_tax_group]
            else:
                subtotals.append(
                    {
                        "name": _("Untaxed Amount"),
                        "base_amount_currency": igtf_base_amount_currency,
                        "base_amount": igtf_base_amount_company_currency,
                        "tax_amount_currency": 0.0,
                        "tax_amount": 0.0,
                        "tax_groups": [igtf_tax_group],
                    }
                )
            totals["subtotals"] = subtotals
            totals["l10n_ve_igtf_collected_amount_currency"] = igtf_amount_currency
            totals["l10n_ve_igtf_collected_amount"] = igtf_amount_company_currency
            totals["total_amount_currency"] = (
                totals.get("total_amount_currency", 0.0) + igtf_amount_currency
            )
            totals["total_amount"] = (
                totals.get("total_amount", 0.0) + igtf_amount_company_currency
            )
            move.tax_totals = totals

    @api.depends("move_type", "line_ids.amount_residual")
    def _compute_payments_widget_reconciled_info(self):
        """
        Enrich the invoice payments widget lines with IGTF details.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Notes
        -----
        This method post-processes `invoice_payments_widget` computed by core to:
        - Show the gross paid amount on the widget line (base amount before IGTF deduction).
        - Show the IGTF amount (in payment currency and company currency) as an extra line and in the popover.
        - Allocate IGTF proportionally per invoice when a single payment is reconciled with multiple invoices.
        """
        super()._compute_payments_widget_reconciled_info()

        Partial = self.env["account.partial.reconcile"]
        Payment = self.env["account.payment"]

        for move in self:
            if move.country_code != "VE":
                continue
            widget = move.invoice_payments_widget
            if not widget or not isinstance(widget, dict) or not widget.get("content"):
                continue

            content = widget["content"]
            lines = list(content.values()) if isinstance(content, dict) else (content or [])

            for line in lines:
                if line.get("is_exchange"):
                    continue

                payment_id = line.get("account_payment_id")
                partial_id = line.get("partial_id")
                currency_id = line.get("currency_id")
                if not payment_id or not partial_id or not currency_id:
                    continue

                payment = Payment.browse(payment_id)
                if not payment or not payment.exists():
                    continue

                igtf_account = payment.company_id.l10n_ve_igtf_account_id
                if not igtf_account:
                    continue

                partial = Partial.browse(partial_id)
                if not partial or not partial.exists():
                    continue

                widget_currency = self.env["res.currency"].browse(currency_id)

                total_igtf_company_currency = 0.0
                igtf_amls = payment.move_id.line_ids.filtered(
                    lambda line: line.account_id == igtf_account
                )
                if not igtf_amls:
                    igtf_amls = payment.move_id.line_ids.filtered(
                        lambda line: (line.name or "").upper().startswith("IGTF")
                    )
                if not igtf_amls:
                    continue

                for aml in igtf_amls:
                    total_igtf_company_currency += abs(aml.balance)

                total_igtf_company_currency = payment.company_currency_id.round(
                    total_igtf_company_currency
                )
                if payment.company_currency_id.is_zero(total_igtf_company_currency):
                    continue

                pay_line = False
                if partial.debit_move_id.payment_id == payment:
                    pay_line = partial.debit_move_id
                elif partial.credit_move_id.payment_id == payment:
                    pay_line = partial.credit_move_id
                if not pay_line:
                    continue

                net_amount = line.get("amount", 0.0)
                if widget_currency.is_zero(net_amount):
                    continue

                payment_amount_widget = (
                    payment.amount
                    if payment.currency_id == widget_currency
                    else payment.currency_id._convert(
                        payment.amount,
                        widget_currency,
                        payment.company_id,
                        payment.date,
                    )
                )
                if widget_currency.is_zero(payment_amount_widget):
                    continue

                p = (payment.company_id.l10n_ve_igtf_percent or 0.0) / 100.0
                if p <= 0.0:
                    continue

                matched_partials = (
                    pay_line.matched_debit_ids | pay_line.matched_credit_ids
                ).filtered(
                    lambda pr: (
                        not pr.exchange_move_id
                        or pr.debit_move_id.payment_id
                        or pr.credit_move_id.payment_id
                    )
                )
                total_net_paymentline_widget = 0.0
                for pr in matched_partials:
                    line_currency = (
                        pr.debit_currency_id
                        if pr.debit_move_id == pay_line
                        else pr.credit_currency_id
                    )
                    amt = (
                        abs(pr.debit_amount_currency)
                        if pr.debit_move_id == pay_line
                        else abs(pr.credit_amount_currency)
                    )
                    total_net_paymentline_widget += (
                        amt
                        if line_currency == widget_currency
                        else line_currency._convert(
                            amt, widget_currency, payment.company_id, pr.max_date
                        )
                    )
                if widget_currency.is_zero(total_net_paymentline_widget):
                    continue

                gross_allocated_widget = payment_amount_widget * (
                    net_amount / total_net_paymentline_widget
                )
                allocation_ratio = net_amount / total_net_paymentline_widget
                igtf_company_currency = payment.company_currency_id.round(
                    total_igtf_company_currency * allocation_ratio
                )
                igtf_amount_widget = widget_currency.round(
                    payment.company_currency_id._convert(
                        igtf_company_currency,
                        widget_currency,
                        payment.company_id,
                        partial.max_date,
                    )
                )

                invoice_total_widget = (
                    move.amount_total
                    if move.currency_id == widget_currency
                    else move.currency_id._convert(
                        move.amount_total, widget_currency, move.company_id, move.date
                    )
                )
                base_widget = (
                    min(gross_allocated_widget, invoice_total_widget)
                    if invoice_total_widget
                    else gross_allocated_widget
                )
                gross_amount = base_widget

                gross_company_currency = abs(
                    widget_currency._convert(
                        gross_amount,
                        payment.company_currency_id,
                        payment.company_id,
                        partial.max_date,
                    )
                )

                line.update(
                    {
                        "amount": gross_amount,
                        "l10n_ve_net_amount": net_amount,
                        "l10n_ve_igtf_amount": igtf_amount_widget,
                        "l10n_ve_net_amount_formatted": formatLang(
                            self.env, net_amount, currency_obj=widget_currency
                        ),
                        "l10n_ve_igtf_amount_formatted": formatLang(
                            self.env, igtf_amount_widget, currency_obj=widget_currency
                        ),
                        "l10n_ve_igtf_amount_company_currency_formatted": formatLang(
                            self.env,
                            igtf_company_currency,
                            currency_obj=payment.company_currency_id,
                        ),
                        "amount_foreign_currency": formatLang(
                            self.env, gross_amount, currency_obj=widget_currency
                        ),
                        "amount_company_currency": formatLang(
                            self.env,
                            gross_company_currency,
                            currency_obj=payment.company_currency_id,
                        ),
                    }
                )

