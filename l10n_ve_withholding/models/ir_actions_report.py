import logging

from odoo import _, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        if (
            self._get_report(report_ref).report_name
            == "l10n_ve_withholding.retention_voucher_template"
        ):
            retention_ids = self.env["account.retention"].browse(res_ids)
            for retention in retention_ids:
                if retention.state == "draft":
                    raise ValidationError(
                        _("You cannot download a withholding slip in draft status. ")
                    )
        return super()._render_qweb_pdf(report_ref, res_ids, data)
