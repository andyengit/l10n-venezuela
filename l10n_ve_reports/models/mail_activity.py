# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models
from odoo.exceptions import UserError


class AccountTaxReportActivity(models.Model):
    _inherit = "mail.activity"

    account_tax_closing_params = fields.Json(string="Tax closing additional params")

    def action_open_tax_activity(self):
        self.ensure_one()
        if self.activity_type_id == self.env.ref(
            "l10n_ve_reports.mail_activity_type_tax_report_to_pay"
        ):
            move = self.env["account.move"].browse(self.res_id)
            return move._action_tax_to_pay_wizard()
        elif self.activity_type_id == self.env.ref(
            "l10n_ve_reports.mail_activity_type_tax_report_to_be_sent"
        ):
            move = self.env["account.move"].browse(self.res_id)
            return move._action_tax_to_send()

        raise UserError(_("Tax Return report has been removed from this module."))
