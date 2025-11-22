import logging

from odoo import Command, _, api, models

_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        for record in res:
            if record.move_id.move_type == "entry":
                continue

            if record.move_id.country_code != self.env.ref("base.ve").code:
                continue

            record._put_unique_tax_per_line()
        return res

    def write(self, vals):
        res = super().write(vals)
        for record in self:
            if record.move_id.move_type == "entry":
                continue
            if record.move_id.country_code != self.env.ref("base.ve").code:
                continue

            record._put_unique_tax_per_line()
        return res

    def _put_unique_tax_per_line(self):
        self.ensure_one()
        if self.display_type not in ("product", "discount"):
            return

        if len(self.tax_ids) == 0:
            if self.move_id.move_type in ("out_invoice", "out_refund", "out_receipt"):
                self.tax_ids = [Command.link(self.env.company.account_sale_tax_id.id)]
                self.move_id.message_post(
                    body=_("Added default sales tax to line: %s.") % self.name
                )

            if self.move_id.move_type in ("in_invoice", "in_refund", "in_receipt"):
                self.tax_ids = [
                    Command.link(self.env.company.account_purchase_tax_id.id)
                ]
