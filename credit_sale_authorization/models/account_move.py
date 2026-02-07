from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    is_credit_sale = fields.Boolean(
        string="Es venta a crédito",
        compute="_compute_is_credit_sale",
        store=True,
    )
    credit_authorized = fields.Boolean(
        string="Crédito Autorizado",
        default=False,
        tracking=True,
    )
    can_authorize_credit = fields.Boolean(
        compute="_compute_can_authorize_credit",
    )

    @api.depends(
        "invoice_payment_term_id",
        "invoice_payment_term_id.line_ids.nb_days",
        "invoice_payment_term_id.line_ids.delay_type",
    )
    def _compute_is_credit_sale(self):
        for move in self:
            is_credit = False
            if move.invoice_payment_term_id:
                for line in move.invoice_payment_term_id.line_ids:
                    if line.nb_days >= 1 or line.delay_type != "days_after":
                        is_credit = True
                        break
            move.is_credit_sale = is_credit

    def _compute_can_authorize_credit(self):
        can = self.env.user.has_group(
            "credit_sale_authorization.group_credit_sale_confirm"
        )
        for record in self:
            record.can_authorize_credit = can

    def write(self, vals):
        if "credit_authorized" in vals and not self.env.user.has_group(
            "credit_sale_authorization.group_credit_sale_confirm"
        ):
            raise AccessError(
                _(
                    "No tiene permiso para modificar el campo 'Crédito Autorizado'. "
                    "Contacte a un usuario con el permiso 'Confirmar ventas a Crédito'."
                )
            )
        return super().write(vals)

    def _post(self, soft=True):
        for move in self:
            if (
                move.is_invoice(include_receipts=True)
                and move.is_credit_sale
                and not move.credit_authorized
            ):
                raise UserError(
                    _(
                        "No se puede confirmar la factura '%(move)s' porque es una "
                        "venta a crédito y no ha sido autorizada. Active el campo "
                        "'Crédito Autorizado' para continuar.",
                        move=move.name,
                    )
                )
        return super()._post(soft=soft)
