# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import L10nVeSeniatCommon


@tagged("post_install", "-at_install")
class TestResCountryMunicipality(L10nVeSeniatCommon):
    def test_onchange_name_uppercase(self):
        state = self.env["res.country.state"].search(
            [("country_id", "=", self.env.ref("base.ve").id)], limit=1
        )
        if state:
            municipality = self.env["res.country.municipality"].new(
                {"country_id": self.env.ref("base.ve").id, "name": "  test name  "}
            )
            municipality.on_change_state()
            self.assertEqual(municipality.name, "TEST NAME")

    def test_constraint_unique_municipality(self):
        state = self.env["res.country.state"].search(
            [("country_id", "=", self.env.ref("base.ve").id)], limit=1
        )
        if state:
            self.env["res.country.municipality"].sudo().create(
                {
                    "name": "UNIQUE MUN",
                    "code": "UM1",
                    "country_id": self.env.ref("base.ve").id,
                    "state_id": [(6, 0, state.ids)],
                }
            )
            with self.assertRaises(ValidationError) as cm:
                self.env["res.country.municipality"].sudo().create(
                    {
                        "name": "UNIQUE MUN",
                        "code": "UM2",
                        "country_id": self.env.ref("base.ve").id,
                        "state_id": [(6, 0, state.ids)],
                    }
                )
            self.assertIn("already registered", str(cm.exception))
