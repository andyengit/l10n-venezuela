from odoo import api, fields, models
from odoo.exceptions import UserError


class L10nVeAdvancePayment(models.Model):
    _name = "l10n_ve.advance.payment"
    _description = "Venezuela Customer Advance Payment"
    _order = "date desc, id desc"

    name = fields.Char(
        compute="_compute_name",
        store=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        index=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        required=True,
        index=True,
    )
    payment_id = fields.Many2one(
        comodel_name="account.payment",
        required=True,
        ondelete="cascade",
        index=True,
    )
    move_id = fields.Many2one(
        comodel_name="account.move",
        related="payment_id.move_id",
        store=True,
        index=True,
    )
    move_line_id = fields.Many2one(
        comodel_name="account.move.line",
        required=True,
        ondelete="cascade",
        index=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        compute="_compute_amounts",
        store=True,
    )
    amount_total = fields.Monetary(
        currency_field="currency_id",
        compute="_compute_amounts",
        store=True,
    )
    amount_residual = fields.Monetary(
        currency_field="currency_id",
        compute="_compute_amounts",
        store=True,
    )
    date = fields.Date(
        related="payment_id.date",
        store=True,
    )
    state = fields.Selection(
        selection=[("open", "Open"), ("used", "Used")],
        compute="_compute_state",
        store=True,
    )

    _sql_constraints = [
        (
            "l10n_ve_advance_unique_move_line",
            "unique(move_line_id)",
            "La linea de anticipo ya existe.",
        ),
    ]

    @api.depends("payment_id.name", "move_line_id.move_name")
    def _compute_name(self):
        for rec in self:
            rec.name = rec.payment_id.name or rec.move_line_id.move_name or "/"

    @api.depends(
        "move_line_id.currency_id",
        "move_line_id.amount_currency",
        "move_line_id.amount_residual_currency",
        "move_line_id.balance",
        "move_line_id.amount_residual",
        "move_line_id.parent_state",
        "move_line_id.reconciled",
    )
    def _compute_amounts(self):
        for rec in self:
            currency = rec.move_line_id.currency_id or rec.company_id.currency_id
            if rec.move_line_id.currency_id:
                total = abs(rec.move_line_id.amount_currency)
                residual = abs(rec.move_line_id.amount_residual_currency)
            else:
                total = abs(rec.move_line_id.balance)
                residual = abs(rec.move_line_id.amount_residual)
            if rec.move_line_id.parent_state != "posted" or rec.move_line_id.reconciled:
                residual = 0.0
            rec.currency_id = currency
            rec.amount_total = total
            rec.amount_residual = residual

    @api.depends("amount_residual")
    def _compute_state(self):
        for rec in self:
            currency = rec.currency_id or rec.company_id.currency_id
            rec.state = "open" if currency and not currency.is_zero(rec.amount_residual) else "used"

    def action_apply_from_invoice(self):
        self.ensure_one()
        invoice_id = self.env.context.get("l10n_ve_invoice_id")
        if not invoice_id:
            raise UserError("No se encontro la factura para aplicar el anticipo.")
        invoice = self.env["account.move"].browse(invoice_id)
        if not invoice.exists():
            raise UserError("La factura no existe.")
        if invoice.move_type != "out_invoice" or invoice.state != "posted":
            raise UserError("Solo puede aplicar anticipos sobre facturas de cliente publicadas.")
        if self.state != "open":
            raise UserError("El anticipo seleccionado no tiene saldo disponible.")
        if self.move_line_id.parent_state != "posted" or self.move_line_id.reconciled:
            raise UserError("El anticipo seleccionado ya no tiene saldo disponible.")
        if self.currency_id.is_zero(self.amount_residual):
            raise UserError("El anticipo seleccionado no tiene saldo disponible.")
        if self.company_id != invoice.company_id:
            raise UserError("El anticipo y la factura deben pertenecer a la misma compania.")
        if self.partner_id != invoice.commercial_partner_id:
            raise UserError("El anticipo y la factura deben pertenecer al mismo cliente.")
        action = invoice.action_register_payment()
        available_amount = self.currency_id._convert(
            self.amount_residual,
            invoice.currency_id,
            invoice.company_id,
            invoice.date or fields.Date.context_today(invoice),
        )
        available_amount = invoice.currency_id.round(available_amount)
        default_amount = min(abs(invoice.amount_residual), available_amount)
        ctx = dict(action.get("context", {}))
        ctx.update(
            {
                "l10n_ve_force_advance_id": self.id,
                "default_amount": default_amount,
                "default_payment_date": fields.Date.to_string(self.date) if self.date else False,
                "l10n_ve_force_advance_date": fields.Date.to_string(self.date) if self.date else False,
            }
        )
        action["context"] = ctx
        return action
