from odoo import fields, models, _
from odoo.exceptions import UserError


class L10nVeIgtfUnreconcilePaymentWizard(models.TransientModel):
    _name = "l10n_ve_igtf.unreconcile.payment.wizard"
    _description = "IGTF payment unreconcile decision"

    move_id = fields.Many2one("account.move", string="Invoice", required=True)
    partial_id = fields.Many2one("account.partial.reconcile", string="Partial Reconcile", required=True)
    payment_id = fields.Many2one("account.payment", string="Payment", required=True)

    action = fields.Selection(
        selection=[
            ("cancel", "Cancel payment"),
            ("keep_remove_igtf", "Keep payment but remove IGTF"),
        ],
        required=True,
        default="keep_remove_igtf",
        string="Action",
    )

    def action_confirm(self):
        """
        Unreconcile the selected payment from the invoice and apply the chosen IGTF option.

        Parameters
        ----------
        None

        Returns
        -------
        dict
            A window close action.

        Raises
        ------
        UserError
            If required information is missing, IGTF account is not configured, or the resulting amount is invalid.

        Notes
        -----
        The flow is:
        1) Unreconcile the partial reconcile from the invoice (same as the standard payments widget).
        2) Either cancel the payment, or keep it by removing the IGTF split (draft -> update -> post).
        """
        self.ensure_one()

        if not self.move_id or not self.partial_id or not self.payment_id:
            raise UserError(_("Missing data to process the request."))

        self.move_id.js_remove_outstanding_partial(self.partial_id.id)

        if self.action == "cancel":
            self.payment_id.action_cancel()
            return {"type": "ir.actions.act_window_close"}

        company = self.payment_id.company_id
        igtf_account = company.l10n_ve_igtf_account_id
        if not igtf_account:
            raise UserError(_("No IGTF account is configured for the company."))

        igtf_lines = self.payment_id.move_id.line_ids.filtered(lambda l: l.account_id == igtf_account)
        if not igtf_lines:
            self.payment_id.with_context(l10n_ve_igtf_from_register_payment=True).write(
                {"l10n_ve_apply_igtf": False, "l10n_ve_igtf_included": False}
            )
            return {"type": "ir.actions.act_window_close"}

        igtf_amount_currency_abs = sum(abs(l.amount_currency) for l in igtf_lines)

        self.payment_id.action_draft()

        new_amount = self.payment_id.currency_id.round(self.payment_id.amount - igtf_amount_currency_abs)
        if new_amount < 0:
            raise UserError(_("The payment amount would become negative after removing IGTF."))

        self.payment_id.with_context(l10n_ve_igtf_from_register_payment=True).write(
            {
                "l10n_ve_apply_igtf": False,
                "l10n_ve_igtf_included": False,
                "amount": new_amount,
            }
        )

        self.payment_id.move_id.action_post()
        self.payment_id.action_post()
        return {"type": "ir.actions.act_window_close"}


