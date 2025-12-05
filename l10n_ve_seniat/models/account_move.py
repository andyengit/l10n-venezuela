import logging

from odoo import _, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    reception_date = fields.Date(
        help="Indicates when the invoice was received by the client/company",
        tracking=True,
    )
    l10n_ve_invoice_date = fields.Datetime("Invoice Datetime", readonly=True)
    l10n_ve_control_number = fields.Char(
        "Control Number",
        copy=False,
    )

    def action_post(self):
        for move_id in self:
            if move_id.country_code != self.env.ref("base.ve").code:
                continue

            lines = []
            for line in self.line_ids:
                if len(line.tax_ids) > 1:
                    tax_mapped = ", ".join(line.tax_ids.mapped("name"))
                    lines.append(f" - {line.name}: {tax_mapped}")

            if lines:
                raise UserError(
                    _(
                        "You cannot assign more than one tax to a single invoice line. "
                        "Please create separate lines for each tax. \n"
                        "%s"
                    )
                    % ("\n".join(lines))
                )
        return super().action_post()

    def button_cancel(self):
        self = self.with_context(force_draft=True)
        return super().button_cancel()

    def button_draft(self):
        if self.country_code != self.env.ref("base.ve").code:
            return super().button_draft()

        if self.env.context.get("force_draft"):
            return super().button_draft()

        _logger.info("Button draft called on move %s", self.move_type)
        if self.move_type == "entry":
            return super().button_draft()

        raise ValidationError(
            _("""You cannot reset to draft an invoice in the Venezuelan localization.
Please create a credit note instead.
        """)
        )

    def _post(self, soft=True):
        res = super()._post(soft=soft)
        for rec in self:
            if rec.state == "posted":
                rec.l10n_ve_invoice_date = fields.Datetime.now()
                # Generar número de control solo para facturas y notas de crédito/débito de cliente
                if (
                    rec.country_code == self.env.ref("base.ve").code
                    and rec.move_type in ("out_invoice", "out_refund")
                    and not rec.l10n_ve_control_number
                ):
                    rec._generate_control_number()
        return res

    def _generate_control_number(self):
        """Genera el número de control según los estándares venezolanos"""
        self.ensure_one()
        if self.l10n_ve_control_number:
            return

        sequence_code = "l10n_ve_control_number"
        # Generar el número usando la secuencia con el contexto de la compañía
        # Odoo maneja automáticamente la multicompañía buscando primero una secuencia
        # específica de la compañía y luego una global
        self.l10n_ve_control_number = (
            self.env["ir.sequence"]
            .with_company(self.company_id.id)
            .next_by_code(sequence_code)
        )

        if not self.l10n_ve_control_number:
            raise UserError(
                _(
                    "No se pudo generar el número de control para la compañía '%s'. "
                    "Por favor, verifique que la secuencia 'l10n_ve_control_number' esté configurada."
                )
                % self.company_id.name
            )

        # Validar que no exista duplicado en la misma compañía
        self._check_control_number_unique()

    def _check_control_number_unique(self):
        """Valida que el número de control sea único por compañía"""
        self.ensure_one()
        if not self.l10n_ve_control_number:
            return

        # Solo validar para facturas y notas de crédito/débito
        if self.move_type not in ("out_invoice", "out_refund"):
            return

        domain = [
            ("l10n_ve_control_number", "=", self.l10n_ve_control_number),
            ("company_id", "=", self.company_id.id),
            ("move_type", "in", ("out_invoice", "out_refund")),
            ("id", "!=", self.id),
        ]

        existing = self.search(domain, limit=1)
        if existing:
            raise ValidationError(
                _(
                    "El número de control '%s' ya existe en la compañía '%s'. "
                    "Por favor, verifique la secuencia o corrija el número manualmente."
                )
                % (self.l10n_ve_control_number, self.company_id.name)
            )

    def write(self, vals):
        """Sobrescribir write para validar el número de control al editar manualmente"""
        res = super().write(vals)
        if "l10n_ve_control_number" in vals:
            for rec in self:
                # Solo validar para facturas y notas de crédito/débito
                if rec.l10n_ve_control_number and rec.move_type in (
                    "out_invoice",
                    "out_refund",
                ):
                    rec._check_control_number_unique()
        return res
