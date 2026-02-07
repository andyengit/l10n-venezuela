from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

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

    @api.depends("payment_term_id", "payment_term_id.line_ids.nb_days", "payment_term_id.line_ids.delay_type")
    def _compute_is_credit_sale(self):
        for order in self:
            is_credit = False
            if order.payment_term_id:
                for line in order.payment_term_id.line_ids:
                    if line.nb_days >= 1 or line.delay_type != "days_after":
                        is_credit = True
                        break
            order.is_credit_sale = is_credit

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

    def _confirmation_error_message(self):
        error = super()._confirmation_error_message()
        if error:
            return error
        if self.is_credit_sale and not self.credit_authorized:
            return _(
                "No se puede confirmar el presupuesto '%(order)s' porque es una "
                "venta a crédito y no ha sido autorizada. Active el campo "
                "'Crédito Autorizado' para continuar.",
                order=self.name,
            )
        return False
