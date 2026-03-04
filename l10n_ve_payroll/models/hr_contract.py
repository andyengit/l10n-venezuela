from odoo import api, fields, models


class HrContract(models.Model):
    _inherit = "hr.contract"

    @api.model
    def _default_struct_id_ve(self):
        company = self.env.company
        if company.country_id.code == "VE":
            structure = self.env.ref(
                "l10n_ve_payroll.structure_ve",
                raise_if_not_found=False,
            )
            if structure and structure.company_id == company:
                return structure
        return self.env["hr.payroll.structure"]

    struct_id = fields.Many2one(
        default=_default_struct_id_ve,
    )
