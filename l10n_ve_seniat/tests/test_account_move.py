# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo import Command, fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from .common import L10nVeSeniatCommon


@tagged("post_install", "-at_install")
class TestAccountMove(L10nVeSeniatCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_ve = cls.env["res.partner"].create(
            {"name": "Partner VE", "country_id": cls.env.ref("base.ve").id, "vat": "J12345678"}
        )
        cls.partner_ve_no_vat = cls.env["res.partner"].create(
            {
                "name": "Partner sin RIF",
                "country_id": cls.env.ref("base.ve").id,
                "vat": False,
            }
        )
        cls.partner_ve_invalid_vat = cls.env["res.partner"].create(
            {"name": "Partner RIF inválido", "country_id": cls.env.ref("base.ve").id, "vat": "X12345678"}
        )
        cls.third_party_ve = cls.env["res.partner"].create(
            {"name": "Tercero VE", "country_id": cls.env.ref("base.ve").id, "vat": "V12345678"}
        )

    def _create_invoice_vals(self, partner, tax_ids=None, price_unit=100.0):
        return {
            "move_type": "out_invoice",
            "partner_id": partner.id,
            "invoice_date": fields.Date.today(),
            "invoice_line_ids": [
                (
                    0,
                    0,
                    {
                        "name": "Test line",
                        "quantity": 1.0,
                        "price_unit": price_unit,
                        "account_id": self.company_data["default_account_revenue"].id,
                        "tax_ids": [(6, 0, tax_ids or [self.company_data["default_tax_sale"].id])],
                    },
                )
            ],
        }

    def test_out_invoice_post_requires_vat(self):
        move = self.env["account.move"].create(
            self._create_invoice_vals(self.partner_ve_no_vat)
        )
        with self.assertRaises(ValidationError) as cm:
            move.action_post()
        self.assertIn("RIF", str(cm.exception))

    def test_out_invoice_post_requires_valid_vat(self):
        move = self.env["account.move"].create(
            self._create_invoice_vals(self.partner_ve_invalid_vat)
        )
        with self.assertRaises(ValidationError) as cm:
            move.action_post()
        self.assertIn("formato válido", str(cm.exception))

    def test_out_invoice_post_rejects_zero_total(self):
        tax = self.company_data["default_tax_sale"]
        move = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_ve.id,
                "invoice_date": fields.Date.today(),
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Product",
                            "quantity": 1.0,
                            "price_unit": 100.0,
                            "account_id": self.company_data["default_account_revenue"].id,
                            "tax_ids": [(6, 0, [tax.id])],
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Credit",
                            "quantity": 1.0,
                            "price_unit": -100.0,
                            "account_id": self.company_data["default_account_revenue"].id,
                            "tax_ids": [(6, 0, [tax.id])],
                        },
                    ),
                ],
            }
        )
        with self.assertRaises(ValidationError) as cm:
            move.action_post()
        self.assertIn("total de 0", str(cm.exception))

    def test_out_invoice_post_rejects_multiple_taxes_per_line(self):
        tax_b = self.env["account.tax"].create(
            {
                "name": "Tax B Sale",
                "amount": 10.0,
                "amount_type": "percent",
                "type_tax_use": "sale",
                "company_id": self.env.company.id,
            }
        )
        move = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_ve.id,
                "invoice_date": fields.Date.today(),
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Line with 2 taxes",
                            "quantity": 1.0,
                            "price_unit": 100.0,
                            "account_id": self.company_data["default_account_revenue"].id,
                            "tax_ids": [
                                Command.set(
                                    [
                                        self.company_data["default_tax_sale"].id,
                                        tax_b.id,
                                    ]
                                )
                            ],
                        },
                    )
                ],
            }
        )
        with self.assertRaises(UserError) as cm:
            move.action_post()
        self.assertIn("more than one tax", str(cm.exception))

    def test_out_invoice_post_success_generates_control_number(self):
        move = self.env["account.move"].create(
            self._create_invoice_vals(self.partner_ve)
        )
        move.action_post()
        self.assertTrue(move.l10n_ve_control_number)
        self.assertTrue(move.l10n_ve_invoice_date)

    def test_button_cancel_out_invoice_raises(self):
        move = self.env["account.move"].create(
            self._create_invoice_vals(self.partner_ve)
        )
        move.action_post()
        with self.assertRaises(ValidationError) as cm:
            move.button_cancel()
        self.assertIn("No se pueden cancelar", str(cm.exception))

    def test_out_refund_post_without_reversed_entry_raises(self):
        move = self.env["account.move"].create(
            {
                "move_type": "out_refund",
                "partner_id": self.partner_ve.id,
                "invoice_date": fields.Date.today(),
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Test line",
                            "quantity": 1.0,
                            "price_unit": 50.0,
                            "account_id": self.company_data["default_account_revenue"].id,
                            "tax_ids": [(6, 0, [self.company_data["default_tax_sale"].id])],
                        },
                    )
                ],
            }
        )
        with self.assertRaises(ValidationError) as cm:
            move.action_post()
        self.assertIn("documento origen", str(cm.exception))

    def test_out_refund_post_with_reversed_entry_success(self):
        invoice = self.env["account.move"].create(
            self._create_invoice_vals(self.partner_ve)
        )
        invoice.action_post()
        credit_note = invoice._reverse_moves()
        credit_note.action_post()
        self.assertTrue(credit_note.l10n_ve_control_number)
        self.assertEqual(credit_note.reversed_entry_id, invoice)

    def test_in_refund_post_without_reversed_entry_raises(self):
        supplier = self.env["res.partner"].create(
            {"name": "Proveedor VE", "country_id": self.env.ref("base.ve").id, "vat": "J98765432"}
        )
        move = self.env["account.move"].create(
            {
                "move_type": "in_refund",
                "partner_id": supplier.id,
                "invoice_date": fields.Date.today(),
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Test line",
                            "quantity": 1.0,
                            "price_unit": 50.0,
                            "account_id": self.company_data["default_account_expense"].id,
                            "tax_ids": [(6, 0, [self.company_data["default_tax_purchase"].id])],
                        },
                    )
                ],
            }
        )
        with self.assertRaises(ValidationError) as cm:
            move.action_post()
        self.assertIn("documento origen", str(cm.exception))

    def test_on_behalf_of_third_party_disabled_config_raises(self):
        self.env.company.l10n_ve_on_behalf_of_third_party_enabled = False
        move = self.env["account.move"].create(
            {
                **self._create_invoice_vals(self.partner_ve),
                "l10n_ve_on_behalf_of_third_party": True,
                "l10n_ve_third_party_partner_id": self.third_party_ve.id,
            }
        )
        with self.assertRaises(ValidationError) as cm:
            move.action_post()
        self.assertIn("habilitar", str(cm.exception))

    def test_on_behalf_of_third_party_requires_third_party_partner(self):
        self.env.company.l10n_ve_on_behalf_of_third_party_enabled = True
        move = self.env["account.move"].create(
            {
                **self._create_invoice_vals(self.partner_ve),
                "l10n_ve_on_behalf_of_third_party": True,
            }
        )
        with self.assertRaises(ValidationError) as cm:
            move.action_post()
        self.assertIn("tercero", str(cm.exception))

    def test_on_behalf_of_third_party_requires_third_party_vat(self):
        self.env.company.l10n_ve_on_behalf_of_third_party_enabled = True
        third_no_vat = self.env["res.partner"].create(
            {"name": "Tercero sin RIF", "country_id": self.env.ref("base.ve").id, "vat": False}
        )
        move = self.env["account.move"].create(
            {
                **self._create_invoice_vals(self.partner_ve),
                "l10n_ve_on_behalf_of_third_party": True,
                "l10n_ve_third_party_partner_id": third_no_vat.id,
            }
        )
        with self.assertRaises(ValidationError) as cm:
            move.action_post()
        self.assertIn("RIF", str(cm.exception))

    def test_on_behalf_of_third_party_post_success(self):
        self.env.company.l10n_ve_on_behalf_of_third_party_enabled = True
        move = self.env["account.move"].create(
            {
                **self._create_invoice_vals(self.partner_ve),
                "l10n_ve_on_behalf_of_third_party": True,
                "l10n_ve_third_party_partner_id": self.third_party_ve.id,
            }
        )
        move.action_post()
        self.assertTrue(move.l10n_ve_control_number)
        self.assertEqual(move.l10n_ve_third_party_partner_id, self.third_party_ve)

    def test_on_behalf_of_third_party_certified_copy_deadline(self):
        self.env.company.l10n_ve_on_behalf_of_third_party_enabled = True
        move = self.env["account.move"].create(
            {
                **self._create_invoice_vals(self.partner_ve),
                "l10n_ve_on_behalf_of_third_party": True,
                "l10n_ve_third_party_partner_id": self.third_party_ve.id,
                "invoice_date": date(2024, 1, 15),
            }
        )
        move.action_post()
        self.assertEqual(move.l10n_ve_certified_copy_deadline, date(2024, 2, 5))

    def test_on_behalf_of_third_party_report_print(self):
        self.env.company.l10n_ve_on_behalf_of_third_party_enabled = True
        move = self.env["account.move"].create(
            {
                **self._create_invoice_vals(self.partner_ve),
                "l10n_ve_on_behalf_of_third_party": True,
                "l10n_ve_third_party_partner_id": self.third_party_ve.id,
            }
        )
        move.action_post()
        move.action_print_pdf()

    def test_button_cancel_out_refund_raises(self):
        invoice = self.env["account.move"].create(
            self._create_invoice_vals(self.partner_ve)
        )
        invoice.action_post()
        move = invoice._reverse_moves()
        move.action_post()
        with self.assertRaises(ValidationError) as cm:
            move.button_cancel()
        self.assertIn("notas de crédito", str(cm.exception))

    def test_button_draft_out_invoice_raises(self):
        move = self.env["account.move"].create(
            self._create_invoice_vals(self.partner_ve)
        )
        move.action_post()
        with self.assertRaises(ValidationError) as cm:
            move.button_draft()
        self.assertIn("reset to draft", str(cm.exception))
        self.assertIn("Venezuelan", str(cm.exception))

    def test_extract_control_number_numeric(self):
        move = self.env["account.move"].new({})
        self.assertEqual(move._extract_control_number_numeric("00000001"), 1)
        self.assertEqual(move._extract_control_number_numeric("ABC-123"), 123)
        self.assertEqual(move._extract_control_number_numeric(""), 0)
        self.assertEqual(move._extract_control_number_numeric(None), 0)

    def test_seniat_invoice_tag_same_currency(self):
        move = self.env["account.move"].create(
            self._create_invoice_vals(self.partner_ve)
        )
        self.assertTrue(move.seniat_invoice_tag)
        self.assertIn("IGTF", move.seniat_invoice_tag)
        self.assertNotIn("tipo de cambio", move.seniat_invoice_tag)

    def test_write_control_number_triggers_validation(self):
        move = self.env["account.move"].create(
            self._create_invoice_vals(self.partner_ve)
        )
        move.action_post()
        ctrl = move.l10n_ve_control_number
        move2 = self.env["account.move"].create(
            self._create_invoice_vals(self.partner_ve)
        )
        move2.action_post()
        with self.assertRaises(ValidationError) as cm:
            move2.write({"l10n_ve_control_number": ctrl})
        self.assertIn("ya existe", str(cm.exception))

    def test_get_name_invoice_report_ve(self):
        move = self.env["account.move"].create(
            self._create_invoice_vals(self.partner_ve)
        )
        self.assertEqual(
            move._get_name_invoice_report(),
            "l10n_ve_seniat.report_invoice_document",
        )

    def test_action_print_pdf(self):
        move = self.env["account.move"].create(
            self._create_invoice_vals(self.partner_ve)
        )
        move.action_post()
        move.action_print_pdf()

    def test_get_sale_tax_values_by_type(self):
        move = self.env["account.move"].create(
            self._create_invoice_vals(self.partner_ve)
        )
        move.action_post()
        result = move.get_sale_tax_values_by_type("general")
        self.assertIn("base", result)
        self.assertIn("amount", result)
        result_empty = move.get_sale_tax_values_by_type("nonexistent")
        self.assertEqual(result_empty, {"base": 0.0, "amount": 0.0})

    def test_sale_tax_data_computed(self):
        move = self.env["account.move"].create(
            self._create_invoice_vals(self.partner_ve)
        )
        move.action_post()
        self.assertTrue(isinstance(move.sale_tax_data, dict))

    def test_purchase_tax_data_computed(self):
        supplier = self.env["res.partner"].create(
            {"name": "Supplier", "country_id": self.env.ref("base.ve").id, "vat": "J98765432"}
        )
        move = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": supplier.id,
                "invoice_date": fields.Date.today(),
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Line",
                            "quantity": 1.0,
                            "price_unit": 100.0,
                            "account_id": self.company_data["default_account_expense"].id,
                            "tax_ids": [(6, 0, [self.company_data["default_tax_purchase"].id])],
                        },
                    )
                ],
            }
        )
        move.action_post()
        self.assertTrue(isinstance(move.purchase_tax_data, dict))

    def test_compute_l10n_ve_inverse_rate_same_currency(self):
        move = self.env["account.move"].create(
            self._create_invoice_vals(self.partner_ve)
        )
        self.assertEqual(move.l10n_ve_inverse_rate, 1.0)

    def test_button_draft_with_force_draft_context(self):
        move = self.env["account.move"].create(
            self._create_invoice_vals(self.partner_ve)
        )
        move.action_post()
        move.with_context(force_draft=True).button_draft()
        self.assertEqual(move.state, "draft")

    def test_control_number_inferior_raises(self):
        move = self.env["account.move"].create(
            self._create_invoice_vals(self.partner_ve)
        )
        move.action_post()
        move2 = self.env["account.move"].create(
            self._create_invoice_vals(self.partner_ve)
        )
        move2.action_post()
        with self.assertRaises(ValidationError) as cm:
            move2.write({"l10n_ve_control_number": "00000001"})
        self.assertIn("inferior", str(cm.exception))
