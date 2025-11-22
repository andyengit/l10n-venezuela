import logging

from odoo import Command, api, models

_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
    _inherit = "account.journal"

    @api.depends("type", "currency_id")
    def _compute_inbound_payment_method_line_ids(self):
        journal_ids = self.env["account.journal"]
        for journal in self:
            pay_method_line_ids_commands = [Command.clear()]

            if self.env.company.chart_template != "ve_seniat":
                continue

            if journal.code in ("RIP", "RIC", "ISLRP", "ISLRC"):
                pay_method = self.env.ref("account.account_payment_method_manual_in")
                pay_method_line_ids_commands += [
                    Command.create(
                        {
                            "name": pay_method.name,
                            "payment_method_id": pay_method.id,
                            "payment_account_id": journal.default_account_id.id,
                        }
                    )
                ]
                journal_ids |= journal
                journal.inbound_payment_method_line_ids = pay_method_line_ids_commands

        return super(
            AccountJournal, self - journal_ids
        )._compute_inbound_payment_method_line_ids()

    @api.depends("type", "currency_id")
    def _compute_outbound_payment_method_line_ids(self):
        journal_ids = self.env["account.journal"]
        for journal in self:
            pay_method_line_ids_commands = [Command.clear()]

            if self.env.company.chart_template != "ve_seniat":
                continue

            if journal.code in ("RIP", "RIC", "ISLRP", "ISLRC"):
                pay_method = self.env.ref("account.account_payment_method_manual_out")
                pay_method_line_ids_commands += [
                    Command.create(
                        {
                            "name": pay_method.name,
                            "payment_method_id": pay_method.id,
                            "payment_account_id": journal.default_account_id.id,
                        }
                    )
                ]
                journal_ids |= journal
                journal.outbound_payment_method_line_ids = pay_method_line_ids_commands

        return super(
            AccountJournal, self - journal_ids
        )._compute_outbound_payment_method_line_ids()
