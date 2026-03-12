from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_ve_advance_payment_ids = fields.Many2many(
        comodel_name="l10n_ve.advance.payment",
        compute="_compute_l10n_ve_advance_payment_ids",
    )
    l10n_ve_advance_available_amount = fields.Monetary(
        currency_field="currency_id",
        compute="_compute_l10n_ve_advance_payment_ids",
    )
    l10n_ve_has_advance_available = fields.Boolean(
        compute="_compute_l10n_ve_advance_payment_ids",
    )
    l10n_ve_advance_widget = fields.Json(
        compute="_compute_l10n_ve_advance_widget",
    )

    def _compute_l10n_ve_advance_payment_ids(self):
        advance_model = self.env["l10n_ve.advance.payment"]
        for move in self:
            move.l10n_ve_advance_payment_ids = False
            move.l10n_ve_advance_available_amount = 0.0
            move.l10n_ve_has_advance_available = False
            if move.move_type != "out_invoice" or move.state != "posted" or not move.partner_id:
                continue
            advances = advance_model.search(
                [
                    ("company_id", "=", move.company_id.id),
                    ("partner_id", "=", move.commercial_partner_id.id),
                    ("state", "=", "open"),
                ],
                order="date asc, id asc",
            )
            visible_advances = self.env["l10n_ve.advance.payment"]
            total = 0.0
            for advance in advances:
                if advance.move_line_id.parent_state != "posted" or advance.move_line_id.reconciled:
                    continue
                available = advance.currency_id._convert(
                    advance.amount_residual,
                    move.currency_id,
                    move.company_id,
                    move.date or fields.Date.context_today(move),
                )
                available = move.currency_id.round(available)
                if move.currency_id.is_zero(available):
                    continue
                total += available
                visible_advances |= advance
            move.l10n_ve_advance_payment_ids = visible_advances
            move.l10n_ve_advance_available_amount = move.currency_id.round(total)
            move.l10n_ve_has_advance_available = bool(visible_advances)

    def _compute_l10n_ve_advance_widget(self):
        for move in self:
            content = []
            for advance in move.l10n_ve_advance_payment_ids:
                amount = advance.currency_id._convert(
                    advance.amount_residual,
                    move.currency_id,
                    move.company_id,
                    move.date or fields.Date.context_today(move),
                )
                content.append(
                    {
                        "id": advance.id,
                        "date": fields.Date.to_string(advance.date) if advance.date else False,
                        "currency_id": move.currency_id.id,
                        "amount": move.currency_id.round(amount),
                        "payment_name": advance.payment_id.display_name or advance.name,
                        "journal_name": advance.payment_id.journal_id.display_name,
                        "ref": advance.move_id.ref or advance.move_id.name,
                    }
                )
            move.l10n_ve_advance_widget = {
                "title": "Anticipos disponibles",
                "outstanding": True,
                "move_id": move.id,
                "content": content,
            }

    def l10n_ve_action_open_register_from_advance(self, advance_id):
        self.ensure_one()
        advance = self.env["l10n_ve.advance.payment"].browse(advance_id)
        return advance.with_context(l10n_ve_invoice_id=self.id).action_apply_from_invoice()
