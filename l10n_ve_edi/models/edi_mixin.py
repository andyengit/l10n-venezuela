import base64
import json
import re

from odoo import api, fields, models

STATE_NOT_SENT = "not_sent"
STATE_QUEUED = "queued"
STATE_SENT = "sent"
STATE_FAILED = "failed"


class L10nVeEdiMixin(models.AbstractModel):
    _name = "l10n_ve.edi.mixin"
    _description = "Venezuela digital invoicing tracking mixin"

    l10n_ve_edi_show_tab = fields.Boolean(
        compute="_compute_l10n_ve_edi_show_tab",
        string="Show EDI Tab",
    )
    l10n_ve_edi_send_state = fields.Selection(
        selection=[
            (STATE_NOT_SENT, "Not Sent"),
            (STATE_QUEUED, "Queued"),
            (STATE_SENT, "Sent"),
            (STATE_FAILED, "Failed"),
        ],
        default=STATE_NOT_SENT,
        copy=False,
        readonly=True,
        string="EDI Send State",
        oldname="tfhka_send_state",
    )
    l10n_ve_edi_sent_at = fields.Datetime(
        copy=False, readonly=True, string="EDI Sent At", oldname="tfhka_sent_at"
    )
    l10n_ve_edi_payload_attachment_id = fields.Many2one(
        "ir.attachment",
        copy=False,
        readonly=True,
        string="EDI Payload Attachment",
        oldname="tfhka_payload_attachment_id",
    )
    l10n_ve_edi_payload_debug_json = fields.Text(
        compute="_compute_l10n_ve_edi_payload_debug_json",
        string="EDI Payload JSON",
    )
    l10n_ve_edi_last_error = fields.Text(
        copy=False, readonly=True, string="EDI Last Error", oldname="tfhka_last_error"
    )
    l10n_ve_edi_response_json = fields.Text(
        copy=False, readonly=True, string="EDI Response JSON", oldname="tfhka_response_json"
    )

    @api.depends("journal_id.l10n_ve_edi_provider")
    def _compute_l10n_ve_edi_show_tab(self):
        for record in self:
            p = record.journal_id.l10n_ve_edi_provider
            record.l10n_ve_edi_show_tab = bool(p and p != "none")

    @api.depends("l10n_ve_edi_payload_attachment_id")
    def _compute_l10n_ve_edi_payload_debug_json(self):
        for record in self:
            record.l10n_ve_edi_payload_debug_json = False
            attachment = record.l10n_ve_edi_payload_attachment_id
            if not attachment or not attachment.datas:
                continue
            try:
                raw = base64.b64decode(attachment.datas)
                payload = json.loads(raw.decode("utf-8"))
                record.l10n_ve_edi_payload_debug_json = json.dumps(
                    payload, ensure_ascii=False, indent=2
                )
            except Exception:
                record.l10n_ve_edi_payload_debug_json = False

    def _l10n_ve_edi_parse_ve_vat(self, vat):
        clean = (vat or "").upper().strip()
        if not clean:
            return "", ""
        clean = re.sub(r"^RIF\s*", "", clean)
        match = re.match(r"^([VEJPGC])[-\s]?(.*)$", clean)
        if match:
            prefix = match.group(1)
            raw_number = (match.group(2) or "").strip()
            number = re.sub(r"[^0-9A-Z\-]", "", raw_number)
            return prefix, number
        compact = re.sub(r"[\s\._/]", "", clean)
        prefix_match = re.search(r"[VEJPGC]", compact)
        prefix = prefix_match.group(0) if prefix_match else ""
        number = re.sub(r"[^0-9A-Z\-]", "", compact[len(prefix):] if prefix else compact)
        return prefix, number

    def _l10n_ve_edi_format_decimal(self, amount):
        return f"{abs(amount or 0.0):.2f}"
