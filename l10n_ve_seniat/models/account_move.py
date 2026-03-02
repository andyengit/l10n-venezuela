import logging
from odoo.tools.safe_eval import safe_eval

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    seniat_invoice_tag = fields.Html(
        string="SENIAT Invoice Tag",
        readonly=True,
        compute="_compute_seniat_invoice_tag",
    )

    @api.depends("company_id", "l10n_ve_inverse_rate", "move_type", "country_code")
    def _compute_seniat_invoice_tag(self):
        for move in self:
            if move.country_code == "VE" and move.move_type in (
                "out_invoice",
                "out_refund",
            ):
                texts = []
                # Primer texto sobre IGTF
                texts.append(
                    "<span>Este pago estará sujeto al cobro adicional del 3% del Impuesto a las Grandes Transacciones Financieras (IGTF), de conformidad con la Providencia Administrativa SNAT/2022/000013 publicada en la G.O N 42.339 del 17-03-2022, en caso de ser cancelado en divisas. No aplica en pago en Bs.</span> "
                )
                # Segundo texto sobre tipo de cambio (solo si hay tasa inversa)
                if (move.company_currency_id != move.currency_id):
                    # Formatear la tasa inversa con la moneda de la compañía
                    rate_formatted = move.company_currency_id.format(
                        move.l10n_ve_inverse_rate
                    )
                    texts.append(
                        f"<span>Este documento se expresa en Bolívares con su equivalente en Divisas, al tipo de cambio corriente del mercado a la fecha de su emisión, según lo establecido en el articulo 13 numeral 14 de la providencia administrativa SNAT/2011/0071 ({rate_formatted}) en concordancia con el articulo 128 de la Ley del Banco Central de Venezuela (BCV); articulo 15 de la Ley que establece el impuesto al valor agregado (IVA) y 38 del Reglamento General de la Ley que establece el Impuesto de Valor agregado (RLIVA)</span>"
                    )
                move.seniat_invoice_tag = "".join(texts) if texts else False
            else:
                move.seniat_invoice_tag = False

    def write(self, vals):
        res = super().write(vals)
        if "l10n_ve_control_number" in vals:
            for rec in self:
                if rec.l10n_ve_control_number and rec.move_type in (
                    "out_invoice",
                    "out_refund",
                ):
                    rec._check_control_number_unique()
        return res

    l10n_ve_invoice_original_printed = fields.Boolean(
        string="VE Invoice Original Printed",
        copy=False,
        readonly=True,
        help="Technical flag used by the VE invoice report to determine if a printed copy should display a 'faithful copy' label.",
    )

    reception_date = fields.Date(
        help="Indicates when the invoice was received by the client/company",
        tracking=True,
    )
    l10n_ve_invoice_date = fields.Datetime("Invoice Datetime", readonly=True)
    l10n_ve_control_number = fields.Char(
        string="Control Number",
        copy=False,
        store=True,
        tracking=True,
    )
    l10n_ve_serial_number = fields.Char(
        string="Fiscal Machine Serial",
        copy=False,
        tracking=True,
        help="Serial number of the fiscal machine",
    )
    l10n_ve_invoice_number = fields.Char(
        string="Fiscal Invoice Number",
        copy=False,
        tracking=True,
        help="Invoice number from the fiscal machine",
    )
    l10n_ve_report_z = fields.Char(
        string="Report Z Number",
        copy=False,
        tracking=True,
        help="Report Z number from the fiscal machine",
    )

    def action_post(self):
        for move_id in self:
            if move_id.country_code != self.env.ref("base.ve").code:
                continue

            if move_id.move_type in (
                "out_invoice",
                "out_refund",
                "in_invoice",
                "in_refund",
            ):
                partner = move_id.partner_id
                if not partner.vat:
                    raise ValidationError(
                        _(
                            "No se puede confirmar la factura '%s'. "
                            "El contacto '%s' no tiene el RIF (VAT) configurado.",
                            move_id.name or _("Borrador"),
                            partner.name,
                        )
                    )
                if not partner.check_vat_ve(partner.vat):
                    raise ValidationError(
                        _(
                            "No se puede confirmar la factura '%s'. "
                            "El RIF '%s' del contacto '%s' no tiene un formato válido. "
                            "El formato correcto es: [V/E/J/C/P/G] seguido del número "
                            "de identificación (ej: V12345678, J-12.345.678-9).",
                            move_id.name or _("Borrador"),
                            partner.vat,
                            partner.name,
                        )
                    )

                # Validar que el total de la factura no sea 0
                if abs(move_id.amount_total) < 0.01:
                    raise ValidationError(
                        _(
                            "No se puede facturar con un total de 0. Por favor, verifique las líneas de la factura."
                        )
                    )

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
        # No permitir cancelar facturas de clientes ni notas de crédito en Venezuela
        for move in self:
            if move.country_code == self.env.ref("base.ve").code and move.move_type in (
                "out_invoice",
                "out_refund",
            ):
                if move.move_type == "out_invoice":
                    raise ValidationError(
                        _(
                            "No se pueden cancelar las facturas de clientes. Por favor, cree una nota de crédito en su lugar."
                        )
                    )
                elif move.move_type == "out_refund":
                    raise ValidationError(
                        _(
                            "No se pueden cancelar las notas de crédito. Por favor, cree una nueva nota de crédito o factura en su lugar."
                        )
                    )
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

        journal = self.journal_id
        sequence_id = None

        if journal and journal.type == "sale":
            if self.move_type == "out_invoice" and journal.l10n_ve_invoice_sequence_id:
                sequence_id = journal.l10n_ve_invoice_sequence_id.id
            elif (
                self.move_type == "out_refund"
                and journal.l10n_ve_credit_note_sequence_id
            ):
                sequence_id = journal.l10n_ve_credit_note_sequence_id.id

        if not sequence_id:
            return

        # Verificar que la secuencia existe y es válida
        sequence = self.env["ir.sequence"].browse(sequence_id)
        if not sequence.exists():
            _logger.warning(
                "Sequence with ID %s does not exist for move %s", sequence_id, self.name
            )
            return

        self.l10n_ve_control_number = sequence.with_company(
            self.company_id.id
        ).next_by_id()
        self._check_control_number_unique()

    def _check_control_number_unique(self):
        """Valida que el número de control sea único y no inferior al último asignado por compañía"""
        self.ensure_one()
        if not self.l10n_ve_control_number:
            return

        # Solo validar para facturas y notas de crédito/débito
        if self.move_type not in ("out_invoice", "out_refund"):
            return

        domain = [
            ("l10n_ve_control_number", "=", self.l10n_ve_control_number),
            ("company_id", "=", self.company_id.id),
            ("move_type", "=", self.move_type),
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

        # Validar que el número de control no sea inferior al último asignado
        self._check_control_number_not_inferior()

    def _extract_control_number_numeric(self, control_number):
        """Extrae la parte numérica del número de control para comparación"""
        if not control_number:
            return 0
        # Extraer solo los dígitos del número de control
        digits = "".join(c for c in control_number if c.isdigit())
        return int(digits) if digits else 0

    def _check_control_number_not_inferior(self):
        """Valida que el número de control no sea inferior al último asignado por compañía"""
        self.ensure_one()
        if not self.l10n_ve_control_number:
            return

        # Buscar el número de control más alto existente en la misma compañía
        last_move = self.search(
            [
                ("l10n_ve_control_number", "!=", False),
                ("company_id", "=", self.company_id.id),
                ("move_type", "in", ("out_invoice", "out_refund")),
                ("id", "!=", self.id),
            ],
            order="l10n_ve_control_number desc",
            limit=1,
        )

        if not last_move:
            return

        current_num = self._extract_control_number_numeric(self.l10n_ve_control_number)
        last_num = self._extract_control_number_numeric(
            last_move.l10n_ve_control_number
        )

        if current_num < last_num:
            raise ValidationError(
                _(
                    "El número de control '%s' es inferior al último número de control asignado '%s' "
                    "en la compañía '%s'. No se permite asignar un número de control anterior al último utilizado."
                )
                % (
                    self.l10n_ve_control_number,
                    last_move.l10n_ve_control_number,
                    self.company_id.name,
                )
            )

    sale_tax_data = fields.Json(
        string="Datos de Impuestos para Libro de Ventas",
        compute="_compute_sale_tax_data",
        store=True,
        help="Estructura: {tax_group_id: {'base': X, 'amount': Y, 'tax_type': 'exempt|reduced|general|extend'}}",
    )

    purchase_tax_data = fields.Json(
        string="Datos de Impuestos para Libro de Compras",
        compute="_compute_purchase_tax_data",
        store=True,
        help="Estructura: {tax_group_id: {'base': X, 'amount': Y, 'tax_type': 'exempt|reduced|general|extend'}}",
    )

    @api.depends("tax_totals", "move_type", "state", "company_id")
    def _compute_sale_tax_data(self):
        for move in self:
            if move.state != "posted" or move.move_type not in [
                "out_invoice",
                "out_refund",
            ]:
                move.sale_tax_data = {}
                continue

            if not move.company_id:
                move.sale_tax_data = {}
                continue

            tax_data = {}
            tax_totals = move.tax_totals or {}
            multiplier = -1 if move.move_type == "out_refund" else 1

            company = move.company_id
            tax_config = {}
            if hasattr(company, "exent_aliquot_sale") and company.exent_aliquot_sale:
                tax_config["exempt"] = company.exent_aliquot_sale.tax_group_id.id
            if (
                hasattr(company, "reduced_aliquot_sale")
                and company.reduced_aliquot_sale
            ):
                tax_config["reduced"] = company.reduced_aliquot_sale.tax_group_id.id
            if (
                hasattr(company, "general_aliquot_sale")
                and company.general_aliquot_sale
            ):
                tax_config["general"] = company.general_aliquot_sale.tax_group_id.id
            if hasattr(company, "extend_aliquot_sale") and company.extend_aliquot_sale:
                tax_config["extend"] = company.extend_aliquot_sale.tax_group_id.id

            subtotals = tax_totals.get("subtotals", [])
            for subtotal in subtotals:
                if not isinstance(subtotal, dict):
                    continue
                tax_groups = subtotal.get("tax_groups", [])
                if not isinstance(tax_groups, list):
                    continue
                for tax_info in tax_groups:
                    if not isinstance(tax_info, dict):
                        continue
                    tax_group_id = tax_info.get("id")
                    if not tax_group_id:
                        continue

                    tax_type = None
                    for ttype, tg_id in tax_config.items():
                        if tg_id == tax_group_id:
                            tax_type = ttype
                            break

                    base_amount = (
                        tax_info.get(
                            "base_amount", tax_info.get("base_amount_currency", 0.0)
                        )
                        * multiplier
                    )
                    tax_amount = (
                        tax_info.get(
                            "tax_amount", tax_info.get("tax_amount_currency", 0.0)
                        )
                        * multiplier
                    )
                    tax_data[str(tax_group_id)] = {
                        "base": base_amount,
                        "amount": tax_amount,
                        "tax_type": tax_type,
                    }

            total_taxed = 0.0
            for tax_group_id_str, tax_info in tax_data.items():
                if tax_group_id_str.startswith("_"):
                    continue
                if isinstance(tax_info, dict) and tax_info.get("tax_type") != "exempt":
                    total_taxed += tax_info.get("base", 0.0) + tax_info.get(
                        "amount", 0.0
                    )

            tax_data["_total_taxed"] = total_taxed
            if tax_totals:
                base_untaxed = tax_totals.get(
                    "base_amount",
                    tax_totals.get(
                        "base_amount_currency", tax_totals.get("amount_untaxed", 0.0)
                    ),
                )
                tax_data["_total_untaxed"] = base_untaxed * multiplier
            else:
                tax_data["_total_untaxed"] = 0.0

            move.sale_tax_data = tax_data

    def get_sale_tax_values_by_type(self, tax_type="general"):
        """
        Obtiene los valores de impuestos almacenados por tipo de alícuota.

        Args:
            tax_type: 'exempt', 'reduced', 'general', 'extend'

        Returns:
            dict: {'base': X, 'amount': Y} o {'base': 0.0, 'amount': 0.0}
        """
        self.ensure_one()
        if not self.sale_tax_data:
            return {"base": 0.0, "amount": 0.0}

        company = self.company_id
        tax_config = {}
        if hasattr(company, "exent_aliquot_sale") and company.exent_aliquot_sale:
            tax_config["exempt"] = company.exent_aliquot_sale.tax_group_id.id
        if hasattr(company, "reduced_aliquot_sale") and company.reduced_aliquot_sale:
            tax_config["reduced"] = company.reduced_aliquot_sale.tax_group_id.id
        if hasattr(company, "general_aliquot_sale") and company.general_aliquot_sale:
            tax_config["general"] = company.general_aliquot_sale.tax_group_id.id
        if hasattr(company, "extend_aliquot_sale") and company.extend_aliquot_sale:
            tax_config["extend"] = company.extend_aliquot_sale.tax_group_id.id

        tax_group_id = tax_config.get(tax_type)
        if not tax_group_id:
            return {"base": 0.0, "amount": 0.0}

        return self.sale_tax_data.get(tax_group_id, {"base": 0.0, "amount": 0.0})

    @api.depends("tax_totals", "move_type", "state", "company_id")
    def _compute_purchase_tax_data(self):
        for move in self:
            if move.state != "posted" or move.move_type not in [
                "in_invoice",
                "in_refund",
            ]:
                move.purchase_tax_data = {}
                continue

            if not move.company_id:
                move.purchase_tax_data = {}
                continue

            tax_data = {}
            tax_totals = move.tax_totals or {}
            multiplier = -1 if move.move_type == "in_refund" else 1

            company = move.company_id
            tax_config = {}
            if (
                hasattr(company, "exent_aliquot_purchase")
                and company.exent_aliquot_purchase
            ):
                tax_config["exempt"] = company.exent_aliquot_purchase.tax_group_id.id
            if (
                hasattr(company, "reduced_aliquot_purchase")
                and company.reduced_aliquot_purchase
            ):
                tax_config["reduced"] = company.reduced_aliquot_purchase.tax_group_id.id
            if (
                hasattr(company, "general_aliquot_purchase")
                and company.general_aliquot_purchase
            ):
                tax_config["general"] = company.general_aliquot_purchase.tax_group_id.id
            if (
                hasattr(company, "extend_aliquot_purchase")
                and company.extend_aliquot_purchase
            ):
                tax_config["extend"] = company.extend_aliquot_purchase.tax_group_id.id

            subtotals = tax_totals.get("subtotals", [])
            for subtotal in subtotals:
                if not isinstance(subtotal, dict):
                    continue
                tax_groups = subtotal.get("tax_groups", [])
                if not isinstance(tax_groups, list):
                    continue
                for tax_info in tax_groups:
                    if not isinstance(tax_info, dict):
                        continue
                    tax_group_id = tax_info.get("id")
                    if not tax_group_id:
                        continue

                    tax_type = None
                    for ttype, tg_id in tax_config.items():
                        if tg_id == tax_group_id:
                            tax_type = ttype
                            break

                    base_amount = (
                        tax_info.get(
                            "base_amount", tax_info.get("base_amount_currency", 0.0)
                        )
                        * multiplier
                    )
                    tax_amount = (
                        tax_info.get(
                            "tax_amount", tax_info.get("tax_amount_currency", 0.0)
                        )
                        * multiplier
                    )
                    tax_data[str(tax_group_id)] = {
                        "base": base_amount,
                        "amount": tax_amount,
                        "tax_type": tax_type,
                    }

            total_taxed = 0.0
            for tax_group_id_str, tax_info in tax_data.items():
                if tax_group_id_str.startswith("_"):
                    continue
                if isinstance(tax_info, dict) and tax_info.get("tax_type") != "exempt":
                    tax_amount = tax_info.get("amount", 0.0)
                    if tax_amount != 0.0:
                        total_taxed += tax_info.get("base", 0.0) + tax_amount

            tax_data["_total_taxed"] = total_taxed
            if tax_totals:
                base_untaxed = tax_totals.get(
                    "base_amount",
                    tax_totals.get(
                        "base_amount_currency", tax_totals.get("amount_untaxed", 0.0)
                    ),
                )
                tax_data["_total_untaxed"] = base_untaxed * multiplier
            else:
                tax_data["_total_untaxed"] = 0.0

            move.purchase_tax_data = tax_data

    l10n_ve_inverse_rate = fields.Float(
        string="Tasa de Cambio Inversa",
        compute="_compute_l10n_ve_inverse_rate",
        store=True,
        help="Tasa de cambio inversa (inverse_rate) de la moneda de la factura para la fecha de la factura",
    )

    @api.depends("currency_id", "date", "company_id")
    def _compute_l10n_ve_inverse_rate(self):
        for move in self:
            if not move.currency_id or not move.date or not move.company_id:
                move.l10n_ve_inverse_rate = 0.0
                continue

            if move.currency_id == move.company_id.currency_id:
                move.l10n_ve_inverse_rate = 1.0
                continue

            currency_rate = self.env["res.currency.rate"].search(
                [
                    ("currency_id", "=", move.currency_id.id),
                    ("name", "<=", move.date),
                    ("company_id", "=", move.company_id.id),
                ],
                order="name desc",
                limit=1,
            )
            if currency_rate and currency_rate.rate and currency_rate.rate != 0.0:
                move.l10n_ve_inverse_rate = 1.0 / currency_rate.rate
            else:
                move.l10n_ve_inverse_rate = 0.0

    def _get_name_invoice_report(self):
        self.ensure_one()
        if self.company_id.account_fiscal_country_id.code == "VE":
            return "l10n_ve_seniat.report_invoice_document"
        return super()._get_name_invoice_report()
        
    def action_print_pdf(self):
        return super(AccountMove, self.with_context(l10n_ve_invoice=True)).action_print_pdf()
