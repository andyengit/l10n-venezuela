# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from .common import L10nVeSeniatCommon


@tagged("post_install", "-at_install")
class TestAccountJournal(L10nVeSeniatCommon):
    def test_sale_journal_has_seniat_sequences(self):
        journal = self.company_data["default_journal_sale"]
        journal.action_create_seniat_sequences()
        self.assertTrue(journal.l10n_ve_invoice_sequence_id)
        self.assertTrue(journal.l10n_ve_credit_note_sequence_id)

    def test_action_create_seniat_sequences(self):
        journal = self.env["account.journal"].create(
            {
                "name": "Test Sale Journal",
                "type": "sale",
                "code": "TSAL",
                "company_id": self.env.company.id,
            }
        )
        self.assertTrue(journal.l10n_ve_invoice_sequence_id)
        self.assertTrue(journal.l10n_ve_credit_note_sequence_id)

    def test_non_sale_journal_no_seniat_sequences_on_create(self):
        journal = self.env["account.journal"].create(
            {
                "name": "Test Purchase Journal",
                "type": "purchase",
                "code": "TPUR",
                "company_id": self.env.company.id,
            }
        )
        self.assertFalse(journal.l10n_ve_invoice_sequence_id)
        self.assertFalse(journal.l10n_ve_credit_note_sequence_id)

    def test_action_create_seniat_sequences_skips_non_sale(self):
        journal = self.env["account.journal"].create(
            {
                "name": "Purchase Journal",
                "type": "purchase",
                "code": "TPUR",
                "company_id": self.env.company.id,
            }
        )
        journal.action_create_seniat_sequences()
        self.assertFalse(journal.l10n_ve_invoice_sequence_id)

    def test_journal_write_updates_sequence_names(self):
        journal = self.company_data["default_journal_sale"]
        journal.action_create_seniat_sequences()
        old_name = journal.l10n_ve_invoice_sequence_id.name
        journal.write({"name": "Ventas Modificado"})
        self.assertIn("Ventas Modificado", journal.l10n_ve_invoice_sequence_id.name)

    def test_journal_sync_series_correlative(self):
        journal = self.company_data["default_journal_sale"]
        journal.action_create_seniat_sequences()
        seq = journal.l10n_ve_invoice_sequence_id
        seq.prefix = "F-001-"
        journal.write({"l10n_ve_invoice_sequence_id": seq.id})
        self.assertEqual(journal.series_correlative, "F-001-")
