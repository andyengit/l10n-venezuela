import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
    _inherit = "account.journal"

    l10n_ve_invoice_sequence_id = fields.Many2one(
        "ir.sequence",
        string="SENIAT Invoice Sequence",
        copy=False,
        help="Secuencia para generar números de control de facturas de venta",
    )
    l10n_ve_credit_note_sequence_id = fields.Many2one(
        "ir.sequence",
        string="SENIAT Credit Note Sequence",
        copy=False,
        help="Secuencia para generar números de control de notas de crédito de venta",
    )
    invoicing_in_series = fields.Boolean(
        string="Facturacion en Serie",
        help="If enabled, the 'Correlativo en Serie' value is used for digital invoicing instead of the SENIAT sequence prefix.",
    )
    series_correlative = fields.Char(
        string="Correlativo en Serie",
        help="Series value used by digital invoicing when 'Facturacion en Serie' is enabled.",
    )

    def action_create_seniat_sequences(self):
        for journal in self:
            if journal.type != "sale":
                continue
            journal._create_seniat_sequences()
        return True


    @api.model_create_multi
    def create(self, vals_list):
        journals = super().create(vals_list)
        for journal in journals:
            if journal.type == "sale":
                journal._create_seniat_sequences()
            journal._sync_series_correlative_from_sequence()
        return journals

    def write(self, vals):
        res = super().write(vals)
        if "type" in vals:
            for journal in self:
                if journal.type == "sale":
                    journal._create_seniat_sequences()
        if "name" in vals:
            for journal in self:
                if journal.type == "sale":
                    journal._update_sequence_names()
        if "l10n_ve_invoice_sequence_id" in vals or "l10n_ve_credit_note_sequence_id" in vals or "invoicing_in_series" in vals:
            self._sync_series_correlative_from_sequence()
        return res

    def _create_seniat_sequences(self):
        self.ensure_one()
        if self.type != "sale":
            return

        company = self.company_id
        invoice_sequence_name = f"SENIAT INVOICE SEQUENCE: {self.name}"
        credit_note_sequence_name = f"SENIAT CREDIT NOTE SEQUENCE: {self.name}"

        if not self.l10n_ve_invoice_sequence_id:
            invoice_sequence = self.env["ir.sequence"].search(
                [
                    ("code", "=", f"l10n_ve_journal_{self.id}_invoice"),
                    ("company_id", "=", company.id),
                ],
                limit=1,
            )
            if not invoice_sequence:
                invoice_sequence = self.env["ir.sequence"].create(
                    {
                        "name": invoice_sequence_name,
                        "code": f"l10n_ve_journal_{self.id}_invoice",
                        "prefix": "",
                        "suffix": "",
                        "padding": 8,
                        "number_increment": 1,
                        "number_next": 1,
                        "company_id": company.id,
                    }
                )
            self.l10n_ve_invoice_sequence_id = invoice_sequence.id

        if not self.l10n_ve_credit_note_sequence_id:
            credit_note_sequence = self.env["ir.sequence"].search(
                [
                    ("code", "=", f"l10n_ve_journal_{self.id}_credit_note"),
                    ("company_id", "=", company.id),
                ],
                limit=1,
            )
            if not credit_note_sequence:
                credit_note_sequence = self.env["ir.sequence"].create(
                    {
                        "name": credit_note_sequence_name,
                        "code": f"l10n_ve_journal_{self.id}_credit_note",
                        "prefix": "",
                        "suffix": "",
                        "padding": 8,
                        "number_increment": 1,
                        "number_next": 1,
                        "company_id": company.id,
                    }
                )
            self.l10n_ve_credit_note_sequence_id = credit_note_sequence.id
        self._sync_series_correlative_from_sequence()

    def _update_sequence_names(self):
        self.ensure_one()
        if self.type != "sale":
            return

        invoice_sequence_name = f"SENIAT INVOICE SEQUENCE: {self.name}"
        credit_note_sequence_name = f"SENIAT CREDIT NOTE SEQUENCE: {self.name}"

        if self.l10n_ve_invoice_sequence_id:
            self.l10n_ve_invoice_sequence_id.name = invoice_sequence_name
        if self.l10n_ve_credit_note_sequence_id:
            self.l10n_ve_credit_note_sequence_id.name = credit_note_sequence_name

    @api.onchange("l10n_ve_invoice_sequence_id", "l10n_ve_credit_note_sequence_id", "invoicing_in_series")
    def _onchange_series_correlative(self):
        for journal in self:
            if journal.invoicing_in_series:
                continue
            invoice_prefix = (journal.l10n_ve_invoice_sequence_id.prefix or "").strip()
            credit_prefix = (journal.l10n_ve_credit_note_sequence_id.prefix or "").strip()
            journal.series_correlative = invoice_prefix or credit_prefix or ""

    def _sync_series_correlative_from_sequence(self):
        for journal in self:
            if journal.invoicing_in_series:
                continue
            invoice_prefix = (journal.l10n_ve_invoice_sequence_id.prefix or "").strip()
            credit_prefix = (journal.l10n_ve_credit_note_sequence_id.prefix or "").strip()
            journal.series_correlative = invoice_prefix or credit_prefix or ""

