# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import L10nVeSeniatCommon


@tagged("post_install", "-at_install")
class TestResPartner(L10nVeSeniatCommon):
    def test_check_vat_ve_valid_formats(self):
        partner = self.env["res.partner"].create(
            {"name": "Test Partner", "country_id": self.env.ref("base.ve").id}
        )
        valid_vats = ["V12345678", "E12345678", "J12345678", "G12345678", "J-12.345.678-9"]
        for vat in valid_vats:
            partner.vat = vat
            self.assertTrue(partner.check_vat_ve(partner.vat), f"VAT {vat} should be valid")

    def test_check_vat_ve_invalid_formats(self):
        partner = self.env["res.partner"].create(
            {"name": "Test Partner", "country_id": self.env.ref("base.ve").id}
        )
        invalid_vats = ["12345678", "X12345678", "V123", "V12345678901"]
        for vat in invalid_vats:
            partner.vat = vat
            self.assertFalse(partner.check_vat_ve(partner.vat), f"VAT {vat} should be invalid")

    def test_compute_vat_prefix(self):
        partner = self.env["res.partner"].create(
            {"name": "Test Partner", "country_id": self.env.ref("base.ve").id, "vat": "J12345678"}
        )
        self.assertEqual(partner.prefix_vat, "J")

    def test_compute_taxpayer_type_ve(self):
        partner = self.env["res.partner"].create(
            {"name": "Test Partner", "country_id": self.env.ref("base.ve").id}
        )
        self.assertEqual(partner.taxpayer_type, "ordinary")

    def test_compute_taxpayer_type_non_ve(self):
        partner = self.env["res.partner"].create(
            {"name": "Test Partner", "country_id": self.env.ref("base.us").id}
        )
        self.assertFalse(partner.taxpayer_type)

    def test_name_search_customer_mode(self):
        partners = self.env["res.partner"].with_context(
            res_partner_search_mode="customer"
        ).name_search("Partner")
        self.assertTrue(isinstance(partners, list))

    def test_name_search_supplier_mode(self):
        partners = self.env["res.partner"].with_context(
            res_partner_search_mode="supplier"
        ).name_search("Partner")
        self.assertTrue(isinstance(partners, list))

    def test_check_taxpayer_type_country_constraint(self):
        partner = self.env["res.partner"].create(
            {"name": "US Partner", "country_id": self.env.ref("base.us").id}
        )
        with self.assertRaises(ValidationError) as cm:
            partner.taxpayer_type = "ordinary"
        self.assertIn("Venezuelan", str(cm.exception))
