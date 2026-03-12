from odoo import fields, models
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    l10n_ve_register_origin = fields.Boolean(
        default=False,
        copy=False,
    )
    l10n_ve_is_advance_application = fields.Boolean(
        default=False,
        copy=False,
    )

    def _l10n_ve_get_advance_account(self):
        self.ensure_one()
        return self.company_id.l10n_ve_advance_liability_account_id

    def _l10n_ve_is_customer_inbound(self):
        self.ensure_one()
        return self.payment_type == "inbound" and self.partner_type == "customer"

    def _l10n_ve_is_menu_advance_candidate(self):
        self.ensure_one()
        return (
            self._l10n_ve_is_customer_inbound()
            and not self.l10n_ve_register_origin
            and not self.invoice_ids
        )

    def _l10n_ve_check_advance_account(self):
        self.ensure_one()
        account = self._l10n_ve_get_advance_account()
        if not account:
            raise UserError("Configure la cuenta de anticipos para registrar pagos sin factura.")
        if account.account_type not in ("liability_current", "liability_non_current", "liability_payable"):
            raise UserError("La cuenta de anticipos debe ser de pasivo.")
        if not account.reconcile:
            raise UserError("La cuenta de anticipos debe permitir conciliacion.")
        return account

    def _l10n_ve_sync_advance_records(self):
        advance_model = self.env["l10n_ve.advance.payment"]
        for pay in self.filtered(lambda p: p.move_id and p.move_id.state == "posted" and p._l10n_ve_is_customer_inbound()):
            account = pay._l10n_ve_get_advance_account()
            if not account:
                continue
            lines = pay.move_id.line_ids.filtered(
                lambda line: line.account_id == account and line.credit > 0 and line.parent_state == "posted"
            )
            existing = advance_model.search([("move_line_id", "in", lines.ids)])
            existing_line_ids = set(existing.mapped("move_line_id").ids)
            for line in lines:
                if line.id in existing_line_ids:
                    continue
                partner = line.partner_id.commercial_partner_id or pay.partner_id.commercial_partner_id
                if not partner:
                    continue
                advance_model.create(
                    {
                        "company_id": pay.company_id.id,
                        "partner_id": partner.id,
                        "payment_id": pay.id,
                        "move_line_id": line.id,
                    }
                )

    def action_post(self):
        for pay in self:
            if pay._l10n_ve_is_menu_advance_candidate():
                if not pay.partner_id:
                    raise UserError("Debe seleccionar un cliente para registrar un anticipo.")
                account = pay._l10n_ve_check_advance_account()
                pay.destination_account_id = account
        res = super().action_post()
        self._l10n_ve_sync_advance_records()
        return res

    def _prepare_move_liquidity_lines(self, default_values):
        lines = super()._prepare_move_liquidity_lines(default_values)
        if self.l10n_ve_is_advance_application:
            account = self._l10n_ve_check_advance_account()
            for line in lines:
                line["account_id"] = account.id
        return lines
