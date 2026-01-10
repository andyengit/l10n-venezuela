from odoo import models

from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @template("ve_seniat", "account.account")
    def _get_ve_seniat_igtf_account(self):
        """
        Provide the IGTF payable account in the Venezuelan chart template.

        Parameters
        ----------
        None

        Returns
        -------
        dict
            Mapping of template XML IDs to account value dicts.
        """
        return {
            "l10n_ve_igtf.l10n_ve_igtf_account_igtf_payable": {
                "name": "IGTF Payable",
                "code": "2139001",
                "account_type": "liability_payable",
                "reconcile": True,
            },
        }

    @template("ve_seniat", "res.company")
    def _get_ve_seniat_res_company_igtf(self):
        """
        Configure the company defaults for IGTF when the chart template is installed.

        Parameters
        ----------
        None

        Returns
        -------
        dict
            Mapping of company IDs to default field values.
        """
        return {
            self.env.company.id: {
                "l10n_ve_igtf_account_id": "l10n_ve_igtf.l10n_ve_igtf_account_igtf_payable",
                "l10n_ve_igtf_percent": 3.0,
            },
        }
