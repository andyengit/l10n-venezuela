from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    l10n_ve_apply_igtf = fields.Boolean(string="Apply IGTF", default=False)
    l10n_ve_igtf_included = fields.Boolean(
        string="Include IGTF in amount",
        default=False,
        help="If enabled, the payment amount already includes IGTF. "
        "Example: Invoice 100, IGTF 3% => pay 103 to settle the invoice and record 3 as IGTF.",
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

    def _l10n_ve_igtf_block_manual_activation(self, vals):
        """
        Prevent enabling IGTF directly on payments.

        Parameters
        ----------
        vals : dict
            Values being written/created.

        Returns
        -------
        None

        Raises
        ------
        UserError
            If IGTF flags are being enabled outside the invoice payment register wizard.
        """
        if self.env.context.get("l10n_ve_igtf_from_register_payment"):
            return
        enable_apply = vals.get("l10n_ve_apply_igtf") is True
        enable_included = vals.get("l10n_ve_igtf_included") is True
        if enable_apply or enable_included:
            raise UserError(
                _(
                    "You cannot enable IGTF directly on the payment. "
                    "Please register the payment from the invoice wizard (Register Payment)."
                )
            )

    @api.model_create_multi
    def create(self, vals_list):
        """
        Create payments enforcing IGTF activation rules.

        Parameters
        ----------
        vals_list : list[dict]
            Create values.

        Returns
        -------
        recordset
            Created payments.
        """
        for vals in vals_list:
            self._l10n_ve_igtf_block_manual_activation(vals)
        return super().create(vals_list)

    def write(self, vals):
        """
        Write payments enforcing IGTF activation rules.

        Parameters
        ----------
        vals : dict
            Write values.

        Returns
        -------
        bool
        """
        self._l10n_ve_igtf_block_manual_activation(vals)
        return super().write(vals)

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

    @api.depends("currency_id", "company_id", "company_id.l10n_ve_igtf_currency_ids")
    def _compute_l10n_ve_show_apply_igtf(self):
        for payment in self:
            if payment.country_code != "VE":
                payment.l10n_ve_show_apply_igtf = False
                continue
            allowed = payment.company_id.l10n_ve_igtf_currency_ids
            if not allowed:
                allowed = (
                    payment.env.ref("base.USD", raise_if_not_found=False)
                    or payment.env["res.currency"]
                )
            payment.l10n_ve_show_apply_igtf = bool(
                payment.currency_id and payment.currency_id in allowed
            )

    @api.depends(
        "l10n_ve_apply_igtf",
        "l10n_ve_igtf_included",
        "amount",
        "currency_id",
        "date",
        "company_id",
        "company_currency_id",
        "company_id.l10n_ve_igtf_percent",
    )
    def _compute_l10n_ve_igtf_amount_currency(self):
        """
        Compute IGTF amount in the payment currency.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        for payment in self:
            if payment.country_code != "VE":
                payment.l10n_ve_igtf_amount_currency = 0.0
                continue
            percent = payment.company_id.l10n_ve_igtf_percent or 0.0
            if (
                not payment.l10n_ve_apply_igtf
                or percent <= 0.0
                or not payment.currency_id
            ):
                payment.l10n_ve_igtf_amount_currency = 0.0
                continue

            if payment.currency_id not in payment._get_igtf_currency_ids():
                payment.l10n_ve_igtf_amount_currency = 0.0
                continue

            p = percent / 100.0
            if payment.l10n_ve_igtf_included:
                igtf_amount = payment.amount * p / (1.0 + p)
            else:
                igtf_amount = payment.amount * p
            payment.l10n_ve_igtf_amount_currency = payment.currency_id.round(
                igtf_amount
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
        for payment in self:
            if payment.country_code != "VE":
                payment.l10n_ve_igtf_amount_company_currency = 0.0
                continue
            igtf_amount_currency = payment.l10n_ve_igtf_amount_currency
            if not payment.currency_id or payment.currency_id.is_zero(
                igtf_amount_currency
            ):
                payment.l10n_ve_igtf_amount_company_currency = 0.0
                continue

            payment.l10n_ve_igtf_amount_company_currency = (
                payment.company_currency_id.round(
                    payment.currency_id._convert(
                        igtf_amount_currency,
                        payment.company_currency_id,
                        payment.company_id,
                        payment.date,
                    )
                )
            )

    def _prepare_move_line_default_vals(
        self, write_off_line_vals=None, force_balance=None
    ):
        """
        Split IGTF from receivable and post it to the IGTF payable account.

        Parameters
        ----------
        write_off_line_vals : dict | None
            Optional write-off line values.
        force_balance : float | None
            Optional forced balance.

        Returns
        -------
        list[dict]
            Journal item values for the payment entry.

        Raises
        ------
        UserError
            If computed IGTF exceeds the receivable counterpart amount.
        """
        self.ensure_one()

        line_vals_list = super()._prepare_move_line_default_vals(
            write_off_line_vals=write_off_line_vals,
            force_balance=force_balance,
        )

        if self.country_code != "VE":
            return line_vals_list

        company = self.company_id
        igtf_account = company.l10n_ve_igtf_account_id
        igtf_percent = company.l10n_ve_igtf_percent or 0.0

        if (
            not igtf_account
            or not self.l10n_ve_apply_igtf
            or igtf_percent <= 0.0
            or self.payment_type != "inbound"
            or self.destination_account_id.account_type != "asset_receivable"
            or self.currency_id not in self._get_igtf_currency_ids()
        ):
            return line_vals_list

        counterpart_line = next(
            (
                line
                for line in line_vals_list
                if line.get("account_id") == self.destination_account_id.id
            ),
            None,
        )
        if not counterpart_line:
            return line_vals_list

        p = igtf_percent / 100.0
        if self.l10n_ve_igtf_included:
            igtf_amount_currency_abs = self.currency_id.round(
                self.amount * p / (1.0 + p)
            )
        else:
            igtf_amount_currency_abs = self.currency_id.round(self.amount * p)
        if self.currency_id.is_zero(igtf_amount_currency_abs):
            return line_vals_list

        igtf_amount_currency = -igtf_amount_currency_abs
        igtf_balance_abs = company.currency_id.round(
            self.currency_id._convert(
                igtf_amount_currency_abs,
                company.currency_id,
                company,
                self.date,
            )
        )

        if counterpart_line.get("credit", 0.0) <= 0.0:
            return line_vals_list

        if counterpart_line["credit"] < igtf_balance_abs:
            raise UserError(
                _(
                    "Computed IGTF exceeds the payment amount. Please review the IGTF percentage."
                )
            )

        counterpart_line["credit"] = company.currency_id.round(
            counterpart_line["credit"] - igtf_balance_abs
        )
        counterpart_line["amount_currency"] = self.currency_id.round(
            counterpart_line["amount_currency"] - igtf_amount_currency
        )

        igtf_line_vals = {
            "name": _("IGTF (%s%%)") % (igtf_percent,),
            "date_maturity": self.date,
            "amount_currency": igtf_amount_currency,
            "currency_id": self.currency_id.id,
            "debit": 0.0,
            "credit": igtf_balance_abs,
            "partner_id": False,
            "account_id": igtf_account.id,
        }

        idx = line_vals_list.index(counterpart_line)
        line_vals_list.insert(idx + 1, igtf_line_vals)
        return line_vals_list
