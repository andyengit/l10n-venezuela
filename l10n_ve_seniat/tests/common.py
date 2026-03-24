# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class L10nVeSeniatCommon(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.partner_id.write({"vat": "J770023598", "country_id": cls.env.ref("base.ve").id})
        cls.change_company_country(cls.env.company, cls.env.ref("base.ve"))
