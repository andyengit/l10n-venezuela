# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    invoicing_date = fields.Date(
        string="Fecha de Facturación",
        compute="_compute_invoicing_date",
        store=True,
        readonly=False,
        help="Fecha en que se espera facturar. Se calcula según los términos de pago o puede establecerse manualmente.",
    )

    @api.depends("date_order", "payment_term_id", "commitment_date")
    def _compute_invoicing_date(self):
        for order in self:
            date_ref = order.commitment_date or order.date_order
            date_ref = date_ref.date() if date_ref and hasattr(date_ref, "date") else date_ref
            if date_ref and order.payment_term_id:
                amount = order.amount_untaxed or 1.0
                terms = order.payment_term_id._compute_terms(
                    date_ref=date_ref,
                    currency=order.currency_id or order.company_id.currency_id,
                    company=order.company_id,
                    tax_amount=0,
                    tax_amount_currency=0,
                    untaxed_amount=amount,
                    untaxed_amount_currency=amount,
                    sign=1,
                )
                if terms.get("line_ids"):
                    order.invoicing_date = max(line["date"] for line in terms["line_ids"])
                else:
                    order.invoicing_date = date_ref
            elif date_ref:
                order.invoicing_date = date_ref
            else:
                order.invoicing_date = False

    @api.model
    def _cron_create_uninvoiced_orders_announcement(self):
        if not self.env["ir.module.module"].search(
            [("name", "=", "announcement"), ("state", "=", "installed")], limit=1
        ):
            return
        orders = self.search(
            [("state", "=", "sale"), ("invoice_status", "=", "to invoice")]
        )
        if not orders:
            return
        group_sales = self.env.ref("sales_team.group_sale_salesman", raise_if_not_found=False)
        group_invoice = self.env.ref("account.group_account_invoice", raise_if_not_found=False)
        if not group_sales or not group_invoice:
            return
        allowed_users = group_sales.users & group_invoice.users
        if not allowed_users:
            return
        action_orders = self.env.ref(
            "l10n_ve_seniat_sale.action_sale_order_to_invoice", raise_if_not_found=False
        )
        action_lines = self.env.ref(
            "l10n_ve_seniat_sale.action_sale_order_line_to_invoice", raise_if_not_found=False
        )
        base_url = self.env.company.get_base_url()
        btn_orders = ""
        btn_lines = ""
        if action_orders:
            btn_orders = f'<a href="{base_url}/web#action={action_orders.id}&model=sale.order&view_type=list" class="btn btn-primary">Ver pedidos pendientes</a>'
        if action_lines:
            btn_lines = f'<a href="{base_url}/web#action={action_lines.id}&model=sale.order.line&view_type=list" class="btn btn-secondary">Ver productos pendientes</a>'
        content = f"""
        <p>Tienes <strong>{len(orders)}</strong> pedido(s) de venta pendiente(s) de facturar.</p>
        <p>{btn_orders} {btn_lines}</p>
        """
        existing = self.env["announcement"].search(
            [
                ("name", "=", "Pedidos de venta pendientes de facturar"),
                ("active", "=", True),
            ],
            limit=1,
        )
        vals = {
            "name": "Pedidos de venta pendientes de facturar",
            "content": content,
            "announcement_type": "specific_users",
            "specific_user_ids": [(6, 0, allowed_users.ids)],
            "notification_date": fields.Datetime.now(),
            "active": True,
        }
        if existing:
            existing.write(vals)
        else:
            self.env["announcement"].create(vals)
