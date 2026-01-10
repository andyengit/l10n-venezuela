from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    l10n_ve_apply_igtf = fields.Boolean(string="Apply IGTF", default=False)
    l10n_ve_igtf_included = fields.Boolean(
        string="Include IGTF in amount",
        default=False,
        help="If enabled, the suggested amount includes IGTF (residual + IGTF).",
    )
    l10n_ve_igtf_currency_ids = fields.Many2many(
        related="company_id.l10n_ve_igtf_currency_ids",
        readonly=True,
    )
    l10n_ve_show_apply_igtf = fields.Boolean(
        string="Show Apply IGTF",
        compute="_compute_l10n_ve_show_apply_igtf",
        store=False,
    )
    l10n_ve_igtf_amount_company_currency = fields.Monetary(
        string="IGTF (Company currency)",
        currency_field="company_currency_id",
        compute="_compute_l10n_ve_igtf_amount_company_currency",
        store=False,
        readonly=True,
        help="Computed IGTF amount expressed in the company currency.",
    )
    l10n_ve_igtf_amount_currency = fields.Monetary(
        string="IGTF (Payment currency)",
        currency_field="currency_id",
        compute="_compute_l10n_ve_igtf_amount_currency",
        store=False,
        readonly=True,
        help="Computed IGTF amount expressed in the payment currency.",
    )

    def _get_igtf_currency_ids(self):
        """
        Return the currencies that should trigger IGTF for the current company.

        Parameters
        ----------
        None

        Returns
        -------
        recordset
            `res.currency` recordset.
        """
        self.ensure_one()
        currencies = self.company_id.l10n_ve_igtf_currency_ids
        return (
            currencies
            or self.env.ref("base.USD", raise_if_not_found=False)
            or self.env["res.currency"]
        )

    @api.depends(
        "currency_id", "company_id", "company_id.l10n_ve_igtf_currency_ids", "batches"
    )
    def _compute_l10n_ve_show_apply_igtf(self):
        for wiz in self:
            if wiz.company_id.account_fiscal_country_id.code != "VE":
                wiz.l10n_ve_show_apply_igtf = False
                continue

            # Verificar que los movimientos sean facturas de clientes o notas de crédito de clientes
            # No mostrar IGTF para facturas de proveedor (in_invoice) o notas de crédito de proveedor (in_refund)
            show_igtf = True
            if wiz.batches:
                # batches es una lista de diccionarios, cada uno con 'lines' que es un recordset de account.move.line
                for batch in wiz.batches:
                    lines = batch.get("lines", self.env["account.move.line"])
                    if lines:
                        moves = lines.move_id
                        if moves:
                            # Solo permitir IGTF para facturas de clientes (out_invoice) y notas de crédito de clientes (out_refund)
                            allowed_move_types = ("out_invoice", "out_refund")
                            if any(
                                move.move_type not in allowed_move_types
                                for move in moves
                            ):
                                show_igtf = False
                                break

            if not show_igtf:
                wiz.l10n_ve_show_apply_igtf = False
                continue

            allowed = wiz.company_id.l10n_ve_igtf_currency_ids
            if not allowed:
                allowed = (
                    wiz.env.ref("base.USD", raise_if_not_found=False)
                    or wiz.env["res.currency"]
                )
            wiz.l10n_ve_show_apply_igtf = bool(
                wiz.currency_id and wiz.currency_id in allowed
            )

    @api.depends(
        "l10n_ve_apply_igtf",
        "l10n_ve_igtf_included",
        "amount",
        "currency_id",
        "payment_date",
        "source_amount_currency",
        "source_currency_id",
        "company_id",
        "company_currency_id",
        "company_id.l10n_ve_igtf_percent",
    )
    def _compute_l10n_ve_igtf_amount_currency(self):
        """
        Compute IGTF amount in the wizard currency.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Notes
        -----
        The IGTF base is capped by the invoice residual in the wizard currency to avoid overcomputing
        IGTF when the user enters an amount larger than the invoice total.
        """
        for wiz in self:
            if wiz.company_id.account_fiscal_country_id.code != "VE":
                wiz.l10n_ve_igtf_amount_currency = 0.0
                continue
            percent = wiz.company_id.l10n_ve_igtf_percent or 0.0
            if not wiz.l10n_ve_apply_igtf or percent <= 0.0 or not wiz.currency_id:
                wiz.l10n_ve_igtf_amount_currency = 0.0
                continue

            if wiz.currency_id not in wiz._get_igtf_currency_ids():
                wiz.l10n_ve_igtf_amount_currency = 0.0
                continue

            p = percent / 100.0
            residual_in_currency = wiz.source_amount_currency
            if (
                wiz.source_currency_id
                and wiz.currency_id
                and wiz.source_currency_id != wiz.currency_id
            ):
                residual_in_currency = wiz.source_currency_id._convert(
                    wiz.source_amount_currency,
                    wiz.currency_id,
                    wiz.company_id,
                    wiz.payment_date,
                )

            base_from_amount = (
                wiz.amount / (1.0 + p) if wiz.l10n_ve_igtf_included else wiz.amount
            )
            base = (
                min(base_from_amount, residual_in_currency)
                if residual_in_currency
                else base_from_amount
            )
            igtf_amount = base * p
            wiz.l10n_ve_igtf_amount_currency = wiz.currency_id.round(igtf_amount)

    @api.depends(
        "l10n_ve_igtf_amount_currency",
        "currency_id",
        "company_currency_id",
        "company_id",
        "payment_date",
    )
    def _compute_l10n_ve_igtf_amount_company_currency(self):
        """
        Compute IGTF amount expressed in company currency.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        for wiz in self:
            if wiz.company_id.account_fiscal_country_id.code != "VE":
                wiz.l10n_ve_igtf_amount_company_currency = 0.0
                continue
            igtf_amount_currency = wiz.l10n_ve_igtf_amount_currency
            if not wiz.currency_id or wiz.currency_id.is_zero(igtf_amount_currency):
                wiz.l10n_ve_igtf_amount_company_currency = 0.0
                continue

            wiz.l10n_ve_igtf_amount_company_currency = wiz.company_currency_id.round(
                wiz.currency_id._convert(
                    igtf_amount_currency,
                    wiz.company_currency_id,
                    wiz.company_id,
                    wiz.payment_date,
                )
            )

    @api.onchange(
        "l10n_ve_apply_igtf", "l10n_ve_igtf_included", "currency_id", "payment_date"
    )
    def _onchange_l10n_ve_igtf_included(self):
        """
        Suggest an amount including IGTF when the option is enabled.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        for wiz in self:
            if not wiz.can_edit_wizard:
                continue

            if not wiz.l10n_ve_apply_igtf:
                wiz.l10n_ve_igtf_included = False
                continue

            if not wiz.l10n_ve_igtf_included:
                wiz.custom_user_amount = False
                wiz.custom_user_currency_id = False
                continue

            percent = wiz.company_id.l10n_ve_igtf_percent or 0.0
            if (
                percent <= 0.0
                or not wiz.currency_id
                or wiz.currency_id not in wiz._get_igtf_currency_ids()
            ):
                continue

            p = percent / 100.0
            base_amount = (
                wiz._get_total_amounts_to_pay(wiz.batches)["amount_by_default"]
                if wiz.batches
                else wiz.amount
            )
            suggested = wiz.currency_id.round(base_amount * (1.0 + p))
            wiz.custom_user_currency_id = wiz.currency_id
            wiz.custom_user_amount = suggested
            wiz.amount = suggested

    def _l10n_ve_get_residual_in_currency(self):
        """
        Return the invoice residual expressed in the wizard currency.

        Parameters
        ----------
        None

        Returns
        -------
        float
        """
        self.ensure_one()
        residual_in_currency = self.source_amount_currency
        if (
            self.source_currency_id
            and self.currency_id
            and self.source_currency_id != self.currency_id
        ):
            residual_in_currency = self.source_currency_id._convert(
                self.source_amount_currency,
                self.currency_id,
                self.company_id,
                self.payment_date,
            )
        return residual_in_currency

    def _l10n_ve_get_max_amount_with_igtf(self):
        """
        Compute the maximum allowed payment amount when IGTF applies.

        Parameters
        ----------
        None

        Returns
        -------
        float
            Max allowed amount in the wizard currency.

        Notes
        -----
        The max is computed as `residual * (1 + p)`.
        """
        self.ensure_one()
        percent = self.company_id.l10n_ve_igtf_percent or 0.0
        p = percent / 100.0
        residual = self._l10n_ve_get_residual_in_currency()
        return self.currency_id.round(residual * (1.0 + p))

    def _l10n_ve_validate_amount_max_with_igtf(self):
        """
        Validate that the payment amount does not exceed invoice total plus IGTF.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Raises
        ------
        UserError
            If the amount exceeds the computed maximum allowed amount.
        """
        self.ensure_one()
        if self.company_id.account_fiscal_country_id.code != "VE":
            return
        if (
            not self.l10n_ve_apply_igtf
            or not self.currency_id
            or not self.payment_date
            or (self.currency_id not in self._get_igtf_currency_ids())
        ):
            return

        max_amount = self._l10n_ve_get_max_amount_with_igtf()
        if self.currency_id.compare_amounts(self.amount, max_amount) > 0:
            raise UserError(
                _(
                    "The payment amount (%(amount)s) cannot be greater than the invoice total plus IGTF (%(max)s).",
                    amount=self.amount,
                    max=max_amount,
                )
            )

    @api.onchange("amount", "l10n_ve_apply_igtf", "currency_id", "payment_date")
    def _onchange_l10n_ve_validate_amount_max_with_igtf(self):
        """
        Trigger IGTF maximum amount validation on changes.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        for wiz in self:
            if not wiz.amount:
                continue
            wiz._l10n_ve_validate_amount_max_with_igtf()

    def _create_payments(self):
        """
        Create payments from the wizard enforcing IGTF validations and context.

        Parameters
        ----------
        None

        Returns
        -------
        recordset
            Created `account.payment` recordset.
        """
        self.ensure_one()
        self._l10n_ve_validate_amount_max_with_igtf()
        return super(
            AccountPaymentRegister,
            self.with_context(l10n_ve_igtf_from_register_payment=True),
        )._create_payments()

    def _create_payment_vals_from_wizard(self, batch_result):
        """
        Extend created payment values with IGTF flags from the wizard.

        Parameters
        ----------
        batch_result : dict
            Batch result produced by core wizard logic.

        Returns
        -------
        dict
            Payment create values.
        """
        vals = super()._create_payment_vals_from_wizard(batch_result)
        vals["l10n_ve_apply_igtf"] = self.l10n_ve_apply_igtf
        vals["l10n_ve_igtf_included"] = self.l10n_ve_igtf_included
        return vals

    def _create_payment_vals_from_batch(self, batch_result):
        """
        Extend created payment values with IGTF flags for each batch.

        Parameters
        ----------
        batch_result : dict
            Batch result produced by core wizard logic.

        Returns
        -------
        dict
            Payment create values.
        """
        vals = super()._create_payment_vals_from_batch(batch_result)
        vals["l10n_ve_apply_igtf"] = self.l10n_ve_apply_igtf
        vals["l10n_ve_igtf_included"] = self.l10n_ve_igtf_included
        return vals
