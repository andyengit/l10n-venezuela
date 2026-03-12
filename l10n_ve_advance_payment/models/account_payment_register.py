from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.misc import clean_context


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    l10n_ve_selected_advance_id = fields.Many2one(
        comodel_name="l10n_ve.advance.payment",
        compute="_compute_l10n_ve_selected_advance_info",
    )
    l10n_ve_selected_advance_available_amount = fields.Monetary(
        currency_field="currency_id",
        compute="_compute_l10n_ve_selected_advance_info",
    )
    l10n_ve_show_selected_advance = fields.Boolean(
        compute="_compute_l10n_ve_selected_advance_info",
    )

    @api.depends_context("l10n_ve_force_advance_id")
    def _compute_l10n_ve_selected_advance_info(self):
        for wizard in self:
            wizard.l10n_ve_selected_advance_id = False
            wizard.l10n_ve_selected_advance_available_amount = 0.0
            wizard.l10n_ve_show_selected_advance = False
            force_advance_id = wizard.env.context.get("l10n_ve_force_advance_id")
            if not force_advance_id:
                continue
            advance = wizard.env["l10n_ve.advance.payment"].browse(force_advance_id).exists()
            if not advance:
                continue
            wizard.l10n_ve_selected_advance_id = advance
            if wizard.currency_id:
                available = wizard._l10n_ve_get_advance_available_in_wizard_currency(advance)
            else:
                available = 0.0
            wizard.l10n_ve_selected_advance_available_amount = available
            wizard.l10n_ve_show_selected_advance = True

    def _l10n_ve_get_advance_account(self):
        self.ensure_one()
        account = self.company_id.l10n_ve_advance_liability_account_id
        if not account:
            raise UserError("Configure la cuenta de anticipos para registrar excedentes de pago.")
        if account.account_type not in ("liability_current", "liability_non_current", "liability_payable"):
            raise UserError("La cuenta de anticipos debe ser de pasivo.")
        if not account.reconcile:
            raise UserError("La cuenta de anticipos debe permitir conciliacion.")
        return account

    def _l10n_ve_is_customer_invoice_batch(self, batch_result):
        self.ensure_one()
        lines = batch_result.get("lines", self.env["account.move.line"])
        if self.payment_type != "inbound" or self.partner_type != "customer" or not lines:
            return False
        return all(move.move_type == "out_invoice" for move in lines.move_id)

    def _l10n_ve_get_open_advances(self, batch_result):
        self.ensure_one()
        force_advance_id = self.env.context.get("l10n_ve_force_advance_id")
        if force_advance_id:
            advance = self.env["l10n_ve.advance.payment"].browse(force_advance_id).exists()
            if not advance:
                raise UserError("El anticipo seleccionado no existe.")
            if advance.company_id != self.company_id:
                raise UserError("El anticipo seleccionado no pertenece a esta compania.")
            if advance.state != "open":
                raise UserError("El anticipo seleccionado no tiene saldo disponible.")
            if advance.move_line_id.parent_state != "posted" or advance.move_line_id.reconciled:
                raise UserError("El anticipo seleccionado ya no tiene saldo disponible.")
            lines = batch_result.get("lines", self.env["account.move.line"])
            partner = lines.partner_id[:1].commercial_partner_id if lines else False
            if partner and advance.partner_id != partner:
                raise UserError("El anticipo seleccionado no pertenece al cliente de la factura.")
            return advance
        lines = batch_result.get("lines", self.env["account.move.line"])
        if not lines:
            return self.env["l10n_ve.advance.payment"]
        partner = lines.partner_id[:1].commercial_partner_id
        if not partner:
            return self.env["l10n_ve.advance.payment"]
        advances = self.env["l10n_ve.advance.payment"].search(
            [
                ("company_id", "=", self.company_id.id),
                ("partner_id", "=", partner.id),
                ("state", "=", "open"),
            ],
            order="date asc, id asc",
        )
        return advances.filtered(lambda adv: adv.move_line_id.parent_state == "posted" and not adv.move_line_id.reconciled)

    def _l10n_ve_prepare_advance_plan(self, batch_result, requested_amount):
        self.ensure_one()
        due_amount = self._get_total_amounts_to_pay([batch_result]).get("amount_by_default", 0.0)
        if not self._l10n_ve_is_customer_invoice_batch(batch_result):
            return {
                "due_amount": due_amount,
                "apply_total": 0.0,
                "bank_amount": requested_amount,
                "items": [],
            }
        advances = self._l10n_ve_get_open_advances(batch_result)
        to_cover = min(requested_amount, due_amount)
        remaining = to_cover
        items = []
        for advance in advances:
            if self.currency_id.is_zero(remaining):
                break
            available_in_wizard_currency = self._l10n_ve_get_advance_available_in_wizard_currency(advance)
            if available_in_wizard_currency <= 0:
                continue
            amount_to_apply = min(available_in_wizard_currency, remaining)
            amount_to_apply = self.currency_id.round(amount_to_apply)
            if amount_to_apply <= 0:
                continue
            items.append(
                {
                    "advance": advance,
                    "amount_currency": amount_to_apply,
                }
            )
            remaining = self.currency_id.round(remaining - amount_to_apply)
        apply_total = self.currency_id.round(sum(item["amount_currency"] for item in items))
        bank_amount = self.currency_id.round(max(requested_amount - apply_total, 0.0))
        return {
            "due_amount": due_amount,
            "apply_total": apply_total,
            "bank_amount": bank_amount,
            "items": items,
        }

    def _l10n_ve_get_advance_available_in_wizard_currency(self, advance):
        self.ensure_one()
        move_line = advance.move_line_id
        if not move_line or move_line.parent_state != "posted" or move_line.reconciled:
            return 0.0
        if move_line.currency_id:
            residual = abs(move_line.amount_residual_currency)
            source_currency = move_line.currency_id
        else:
            residual = abs(move_line.amount_residual)
            source_currency = move_line.company_currency_id
        available = source_currency._convert(
            residual,
            self.currency_id,
            self.company_id,
            self.payment_date,
        )
        return self.currency_id.round(available)

    def _l10n_ve_validate_advance_request_amount(self, advance, amount):
        self.ensure_one()
        available = self._l10n_ve_get_advance_available_in_wizard_currency(advance)
        if available <= 0:
            raise UserError("El anticipo seleccionado ya no tiene saldo disponible.")
        if amount > available:
            raise UserError("No puede aplicar un monto mayor al residual disponible del anticipo.")

    def _l10n_ve_validate_forced_advance_date(self):
        self.ensure_one()
        forced_date = self.env.context.get("l10n_ve_force_advance_date")
        if not forced_date:
            return
        expected_date = fields.Date.to_date(forced_date)
        current_date = fields.Date.to_date(self.payment_date)
        if expected_date and current_date != expected_date:
            raise UserError("La fecha del pago debe ser la misma fecha del anticipo seleccionado.")

    def _l10n_ve_validate_forced_advance_amount(self, batch_result):
        self.ensure_one()
        force_advance_id = self.env.context.get("l10n_ve_force_advance_id")
        if not force_advance_id:
            return
        advances = self._l10n_ve_get_open_advances(batch_result)
        advance = advances[:1]
        if not advance:
            raise UserError("No hay anticipo disponible para aplicar.")
        self._l10n_ve_validate_advance_request_amount(advance, self.amount)

    def _l10n_ve_build_overpayment_writeoff(self, bank_amount, due_after_advance):
        self.ensure_one()
        if self.payment_type != "inbound" or self.partner_type != "customer":
            return []
        overpayment = self.currency_id.round(bank_amount - due_after_advance)
        if overpayment <= 0:
            return []
        account = self._l10n_ve_get_advance_account()
        balance = self.currency_id._convert(
            -overpayment,
            self.company_id.currency_id,
            self.company_id,
            self.payment_date,
        )
        return [
            {
                "name": "Anticipo de cliente",
                "account_id": account.id,
                "partner_id": self.partner_id.id,
                "currency_id": self.currency_id.id,
                "amount_currency": -overpayment,
                "balance": balance,
            }
        ]

    def _l10n_ve_get_advance_payment_vals(self, base_vals, amount, advance):
        self.ensure_one()
        vals = dict(base_vals)
        vals["amount"] = amount
        vals["write_off_line_vals"] = []
        vals["l10n_ve_register_origin"] = True
        vals["l10n_ve_is_advance_application"] = True
        vals["memo"] = f"Aplicacion anticipo {advance.payment_id.display_name or advance.name}"
        return vals

    def _l10n_ve_reconcile_advance_lines(self, to_process):
        for vals in to_process:
            advance_id = vals.get("l10n_ve_advance_id")
            payment = vals.get("payment")
            if not advance_id or not payment:
                continue
            advance = self.env["l10n_ve.advance.payment"].browse(advance_id).exists()
            if not advance:
                continue
            liquidity_lines = payment.move_id.line_ids.filtered(
                lambda line: line.account_id == self._l10n_ve_get_advance_account()
                and line.parent_state == "posted"
                and not line.reconciled
            )
            if not liquidity_lines:
                continue
            reconcile_lines = (
                liquidity_lines[:1]
                + advance.move_line_id.filtered(
                    lambda line: line.parent_state == "posted" and not line.reconciled
                )
            )
            if len(reconcile_lines) > 1:
                reconcile_lines.reconcile()

    def _create_payment_vals_from_wizard(self, batch_result):
        vals = super()._create_payment_vals_from_wizard(batch_result)
        vals["l10n_ve_register_origin"] = True
        return vals

    def _create_payment_vals_from_batch(self, batch_result):
        vals = super()._create_payment_vals_from_batch(batch_result)
        vals["l10n_ve_register_origin"] = True
        return vals

    def _create_payments(self):
        self.ensure_one()
        batches = []
        for batch in self.batches:
            batch_account = self._get_batch_account(batch)
            if self.require_partner_bank_account and (not batch_account or not batch_account.allow_out_payment):
                continue
            batches.append(batch)
        if not batches:
            raise UserError(
                "To record payments with %(payment_method)s, the recipient bank account must be manually validated. You should go on the partner bank account in order to validate it."
                % {"payment_method": self.payment_method_line_id.name}
            )
        first_batch_result = batches[0]
        edit_mode = self.can_edit_wizard and (len(first_batch_result["lines"]) == 1 or self.group_payment)
        to_process = []
        if edit_mode:
            self._l10n_ve_validate_forced_advance_date()
            self._l10n_ve_validate_forced_advance_amount(first_batch_result)
            base_vals = self._create_payment_vals_from_wizard(first_batch_result)
            plan = self._l10n_ve_prepare_advance_plan(first_batch_result, self.amount)
            due_after_advance = self.currency_id.round(max(plan["due_amount"] - plan["apply_total"], 0.0))
            if plan["bank_amount"] > 0:
                bank_vals = dict(base_vals)
                bank_vals["amount"] = plan["bank_amount"]
                writeoffs = self._l10n_ve_build_overpayment_writeoff(plan["bank_amount"], due_after_advance)
                if writeoffs:
                    bank_vals.setdefault("write_off_line_vals", [])
                    bank_vals["write_off_line_vals"] += writeoffs
                to_process.append(
                    {
                        "create_vals": bank_vals,
                        "to_reconcile": first_batch_result["lines"],
                        "batch": first_batch_result,
                    }
                )
            for item in plan["items"]:
                if item["amount_currency"] <= 0:
                    continue
                to_process.append(
                    {
                        "create_vals": self._l10n_ve_get_advance_payment_vals(
                            base_vals,
                            item["amount_currency"],
                            item["advance"],
                        ),
                        "to_reconcile": first_batch_result["lines"],
                        "batch": first_batch_result,
                        "l10n_ve_advance_id": item["advance"].id,
                    }
                )
        else:
            if not self.group_payment:
                lines_to_pay = (
                    self._get_total_amounts_to_pay(batches)["lines"]
                    if self.installments_mode in ("next", "overdue", "before_date")
                    else self.line_ids
                )
                new_batches = []
                for batch_result in batches:
                    for line in batch_result["lines"]:
                        if line not in lines_to_pay:
                            continue
                        new_batches.append(
                            {
                                **batch_result,
                                "payment_values": {
                                    **batch_result["payment_values"],
                                    "payment_type": "inbound" if line.balance > 0 else "outbound",
                                },
                                "lines": line,
                            }
                        )
                batches = new_batches
            for batch_result in batches:
                self._l10n_ve_validate_forced_advance_date()
                self._l10n_ve_validate_forced_advance_amount(batch_result)
                base_vals = self._create_payment_vals_from_batch(batch_result)
                requested_amount = base_vals["amount"]
                plan = self._l10n_ve_prepare_advance_plan(batch_result, requested_amount)
                due_after_advance = self.currency_id.round(max(plan["due_amount"] - plan["apply_total"], 0.0))
                if plan["bank_amount"] > 0:
                    bank_vals = dict(base_vals)
                    bank_vals["amount"] = plan["bank_amount"]
                    writeoffs = self._l10n_ve_build_overpayment_writeoff(plan["bank_amount"], due_after_advance)
                    if writeoffs:
                        bank_vals.setdefault("write_off_line_vals", [])
                        bank_vals["write_off_line_vals"] += writeoffs
                    to_process.append(
                        {
                            "create_vals": bank_vals,
                            "to_reconcile": batch_result["lines"],
                            "batch": batch_result,
                        }
                    )
                for item in plan["items"]:
                    if item["amount_currency"] <= 0:
                        continue
                    to_process.append(
                        {
                            "create_vals": self._l10n_ve_get_advance_payment_vals(
                                base_vals,
                                item["amount_currency"],
                                item["advance"],
                            ),
                            "to_reconcile": batch_result["lines"],
                            "batch": batch_result,
                            "l10n_ve_advance_id": item["advance"].id,
                        }
                    )
        lines = sum((batch_result["lines"] for batch_result in batches), self.env["account.move.line"])
        from_sibling_companies = bool(lines) and self._from_sibling_companies(lines)
        if from_sibling_companies and lines.company_id.root_id not in self.env.companies:
            self.env.context = {**self.env.context, "dont_redirect_to_payments": True}
        wizard = self.sudo() if from_sibling_companies else self
        payments = self.env["account.payment"]
        if to_process:
            payments = wizard.with_context(clean_context(self.env.context))._init_payments(to_process, edit_mode=edit_mode)
            wizard._post_payments(to_process, edit_mode=edit_mode)
            wizard._reconcile_payments(to_process, edit_mode=edit_mode)
            wizard._l10n_ve_reconcile_advance_lines(to_process)
        return payments.sudo(flag=False)
