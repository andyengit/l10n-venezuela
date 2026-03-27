from odoo import Command
from odoo.tests import tagged

from odoo.addons.l10n_ve_igtf.tests.common import TestL10nVeIgtfCommon


@tagged("post_install", "-at_install")
class TestTfhkaPayloadTaxTotals(TestL10nVeIgtfCommon):
    USD_BS_INVERSE_RATE = 466.6014

    @staticmethod
    def _parse_tfhka_decimal(value):
        if value is None:
            return 0.0
        return float(str(value).replace(",", "."))

    def _get_sale_tax_by_percent(self, percent):
        domain = [
            ("company_id", "=", self.company.id),
            ("type_tax_use", "=", "sale"),
            ("amount_type", "=", "percent"),
            ("amount", "=", float(percent)),
        ]
        tax = self.env["account.tax"].search(domain, limit=1)
        self.assertTrue(tax, "Impuesto de venta %(pct)s%% no encontrado para la compania." % {"pct": percent})
        return tax

    def _prepare_demo_invoice_line_commands(self):
        t16 = self._get_sale_tax_by_percent(16)
        t8 = self._get_sale_tax_by_percent(8)
        t31 = self._get_sale_tax_by_percent(31)
        t0 = self._get_sale_tax_by_percent(0)
        return [
            Command.create(
                {
                    "name": "Producto IVA 16",
                    "quantity": 1.0,
                    "price_unit": 22.99,
                    "account_id": self.revenue_account.id,
                    "tax_ids": [Command.set([t16.id])],
                }
            ),
            Command.create(
                {
                    "name": "Producto IVA 8",
                    "quantity": 1.0,
                    "price_unit": 2.44,
                    "account_id": self.revenue_account.id,
                    "tax_ids": [Command.set([t8.id])],
                }
            ),
            Command.create(
                {
                    "name": "Producto IVA 31",
                    "quantity": 1.0,
                    "price_unit": 800.33,
                    "account_id": self.revenue_account.id,
                    "tax_ids": [Command.set([t31.id])],
                }
            ),
            Command.create(
                {
                    "name": "Producto Exento",
                    "quantity": 1.0,
                    "price_unit": 3.34,
                    "account_id": self.revenue_account.id,
                    "tax_ids": [Command.set([t0.id])],
                }
            ),
        ]

    def _set_usd_bs_rate(self, inverse_bs_per_usd):
        Rate = self.env["res.currency.rate"]
        rate = Rate.search(
            [
                ("name", "=", self.test_date),
                ("currency_id", "=", self.usd.id),
                ("company_id", "=", self.company.id),
            ],
            limit=1,
        )
        vals = {"inverse_company_rate": float(inverse_bs_per_usd)}
        if rate:
            rate.write(vals)
        else:
            Rate.create(
                {
                    "name": self.test_date,
                    "currency_id": self.usd.id,
                    "company_id": self.company.id,
                    **vals,
                }
            )
        self.env["res.currency"].invalidate_model(["inverse_rate"])

    def _assert_totales_company_matches_tax_totals(self, move, totales):
        move.invalidate_recordset(["tax_totals"])
        tt = move.tax_totals or {}
        self.assertTrue(tt, "La factura debe tener tax_totals.")
        places = 2
        base_amt = float(tt.get("base_amount") or 0.0)
        tax_amt = float(tt.get("tax_amount") or 0.0)
        total_amt = float(tt.get("total_amount") or 0.0)
        self.assertAlmostEqual(
            self._parse_tfhka_decimal(totales.get("subtotal")),
            base_amt,
            places=places,
            msg="Totales.subtotal debe coincidir con tax_totals.base_amount (moneda compania).",
        )
        self.assertAlmostEqual(
            self._parse_tfhka_decimal(totales.get("totalIVA")),
            tax_amt,
            places=places,
            msg="Totales.totalIVA debe coincidir con tax_totals.tax_amount (moneda compania).",
        )
        self.assertAlmostEqual(
            self._parse_tfhka_decimal(totales.get("montoTotalConIVA")),
            base_amt + tax_amt,
            places=places,
            msg="montoTotalConIVA debe ser base + impuestos de lineas (sin IGTF inyectado en base/tax raiz).",
        )
        self.assertAlmostEqual(
            self._parse_tfhka_decimal(totales.get("totalAPagar")),
            total_amt,
            places=places,
            msg="Totales.totalAPagar debe coincidir con tax_totals.total_amount (incluye IGTF si aplica).",
        )

    def _assert_totales_otra_moneda_matches_tax_totals(self, move, otra):
        move.invalidate_recordset(["tax_totals"])
        tt = move.tax_totals or {}
        self.assertTrue(tt)
        places = 2
        self.assertAlmostEqual(
            self._parse_tfhka_decimal(otra.get("subtotal")),
            float(tt.get("base_amount_currency") or 0.0),
            places=places,
            msg="totalesOtraMoneda.subtotal vs tax_totals.base_amount_currency.",
        )
        self.assertAlmostEqual(
            self._parse_tfhka_decimal(otra.get("totalIVA")),
            float(tt.get("tax_amount_currency") or 0.0),
            places=places,
            msg="totalesOtraMoneda.totalIVA vs tax_totals.tax_amount_currency.",
        )
        self.assertAlmostEqual(
            self._parse_tfhka_decimal(otra.get("montoTotalConIVA")),
            float(tt.get("base_amount_currency") or 0.0)
            + float(tt.get("tax_amount_currency") or 0.0),
            places=places,
            msg="montoTotalConIVA (otra) vs base+tax en moneda documento.",
        )
        self.assertAlmostEqual(
            self._parse_tfhka_decimal(otra.get("totalAPagar")),
            float(tt.get("total_amount_currency") or 0.0),
            places=places,
            msg="totalesOtraMoneda.totalAPagar vs tax_totals.total_amount_currency.",
        )

    def _widget_reconciled_payment_lines(self, invoice):
        invoice.invalidate_recordset()
        widget = invoice.invoice_payments_widget or {}
        content = widget.get("content") or []
        lines = list(content.values()) if isinstance(content, dict) else list(content)
        return [
            line
            for line in lines
            if line.get("account_payment_id") and not line.get("is_exchange")
        ]

    def _assert_widget_and_formas_pago_split_usd_then_ves(
        self,
        invoice,
        pay_usd,
        pay_ves,
        residual_usd_before_ves,
        amount_ves_registered,
        totales,
        first_payment_net_usd=100.0,
    ):
        lines_by_pay = {
            line["account_payment_id"]: line for line in self._widget_reconciled_payment_lines(invoice)
        }
        self.assertIn(pay_usd.id, lines_by_pay, "Widget debe incluir el pago en USD.")
        self.assertIn(pay_ves.id, lines_by_pay, "Widget debe incluir el pago en VES.")
        usd_line = lines_by_pay[pay_usd.id]
        ves_line = lines_by_pay[pay_ves.id]
        inv_cur_id = invoice.currency_id.id
        self.assertEqual(usd_line.get("currency_id"), inv_cur_id)
        self.assertEqual(
            ves_line.get("currency_id"),
            inv_cur_id,
            "El widget muestra montos conciliados en moneda del documento (USD), no en VES.",
        )

        self.assertIn(
            "l10n_ve_net_amount",
            usd_line,
            "Linea USD con IGTF debe exponer l10n_ve_net_amount en el widget.",
        )
        self.assertAlmostEqual(
            float(usd_line["l10n_ve_net_amount"]),
            float(first_payment_net_usd),
            places=2,
            msg="La cuota neta aplicada a la factura en la primera forma de pago debe coincidir con la intencion (USD).",
        )
        gross_usd = float(usd_line.get("amount") or 0.0)
        exp_gross_usd = invoice._tfhka_forma_pago_amount_payment_currency(pay_usd)
        self.assertAlmostEqual(
            gross_usd,
            exp_gross_usd,
            places=2,
            msg="Monto bruto USD en widget debe coincidir con la forma de pago TFHKA (base + IGTF en USD).",
        )

        self.assertAlmostEqual(
            float(ves_line.get("amount") or 0.0),
            float(residual_usd_before_ves),
            places=2,
            msg="Linea del segundo pago en el widget debe mostrar el saldo restante en moneda factura (USD).",
        )

        self.assertAlmostEqual(
            invoice._tfhka_net_reconciled_from_payment_invoice_currency(pay_usd),
            float(first_payment_net_usd),
            places=2,
        )
        self.assertAlmostEqual(
            invoice._tfhka_net_reconciled_from_payment_invoice_currency(pay_ves),
            float(residual_usd_before_ves),
            places=2,
        )
        self.assertAlmostEqual(
            float(pay_ves.amount),
            float(amount_ves_registered),
            places=2,
            msg="El account.payment en VES debe conservar el monto introducido en bolivares.",
        )

        formas = totales.get("formasPago") or []
        self.assertEqual(len(formas), 2)
        by_mon = {}
        for row in formas:
            m = (row.get("moneda") or "")[:3]
            by_mon.setdefault(m, []).append(row)
        self.assertIn("USD", by_mon)
        ves_keys = [k for k in by_mon if k in ("VES", "VEF", "BSD")]
        self.assertTrue(ves_keys, "Debe existir una forma de pago en bolivares.")
        usd_row = by_mon["USD"][0]
        ves_row = by_mon[ves_keys[0]][0]
        self.assertAlmostEqual(
            self._parse_tfhka_decimal(usd_row.get("monto")),
            exp_gross_usd,
            places=2,
            msg="formasPago USD debe usar el monto en moneda de pago (bruto IGTF).",
        )
        lines_float = []
        for row in formas:
            lines_float.append({**row, "monto": self._parse_tfhka_decimal(row.get("monto"))})
        sum_formas_comp = invoice._tfhka_formas_pago_sum_company_currency(lines_float)
        tot_apagar_comp = self._parse_tfhka_decimal(totales.get("totalAPagar"))
        self.assertAlmostEqual(
            sum_formas_comp,
            tot_apagar_comp,
            places=2,
            msg="Suma formas de pago en moneda compania debe cerrar con totalAPagar.",
        )

    def test_formas_pago_ves_incluye_sobrepago_cuando_un_solo_documento(self):
        invoice = self._create_customer_invoice(100.0, self.ves)
        over = self.ves.round(invoice.amount_total * 1.5)
        pay = self._register_invoice_payment(
            invoice=invoice,
            amount=over,
            currency=self.ves,
            apply_igtf=False,
            igtf_included=False,
        )
        invoice.invalidate_recordset()
        self.assertEqual(invoice.payment_state, "paid")
        payload = invoice._tfhka_build_documento_electronico_payload()
        totales = payload["documentoElectronico"]["encabezado"]["totales"]
        formas = totales.get("formasPago") or []
        self.assertEqual(len(formas), 1)
        self.assertEqual((formas[0].get("moneda") or "")[:3], "VES")
        monto = self._parse_tfhka_decimal(formas[0].get("monto"))
        self.assertAlmostEqual(monto, float(pay.amount), places=2)
        lines_float = [{**formas[0], "monto": monto}]
        sum_comp = invoice._tfhka_formas_pago_sum_company_currency(lines_float)
        tot_ap = self._parse_tfhka_decimal(totales.get("totalAPagar"))
        self.assertGreater(
            sum_comp,
            tot_ap,
            "Con sobrepago, la suma de formas (Bs pagados) debe superar el total a pagar del documento.",
        )

    def test_payload_totales_matches_tax_totals_ves_posted_no_payment(self):
        invoice = (
            self.env["account.move"]
            .with_company(self.company)
            .create(
                {
                    "move_type": "out_invoice",
                    "company_id": self.company.id,
                    "journal_id": self.sale_journal.id,
                    "partner_id": self.partner.id,
                    "currency_id": self.ves.id,
                    "invoice_date": self.test_date,
                    "date": self.test_date,
                    "invoice_line_ids": self._prepare_demo_invoice_line_commands(),
                }
            )
        )
        invoice.action_post()
        payload = invoice._tfhka_build_documento_electronico_payload()
        totales = payload["documentoElectronico"]["encabezado"]["totales"]
        self._assert_totales_company_matches_tax_totals(invoice, totales)
        self.assertNotIn("totalesOtraMoneda", payload["documentoElectronico"]["encabezado"])

    def test_payload_totales_matches_tax_totals_usd_posted_no_payment(self):
        self._set_usd_bs_rate(self.USD_BS_INVERSE_RATE)
        invoice = (
            self.env["account.move"]
            .with_company(self.company)
            .create(
                {
                    "move_type": "out_invoice",
                    "company_id": self.company.id,
                    "journal_id": self.sale_journal.id,
                    "partner_id": self.partner.id,
                    "currency_id": self.usd.id,
                    "invoice_date": self.test_date,
                    "date": self.test_date,
                    "invoice_line_ids": self._prepare_demo_invoice_line_commands(),
                }
            )
        )
        invoice.action_post()
        payload = invoice._tfhka_build_documento_electronico_payload()
        enc = payload["documentoElectronico"]["encabezado"]
        totales = enc["totales"]
        otra = enc.get("totalesOtraMoneda")
        self.assertTrue(otra, "Factura en moneda extranjera debe generar totalesOtraMoneda.")
        self._assert_totales_company_matches_tax_totals(invoice, totales)
        self._assert_totales_otra_moneda_matches_tax_totals(invoice, otra)

    def test_payload_totales_matches_tax_totals_after_usd_payment_with_igtf(self):
        self._set_usd_bs_rate(self.USD_BS_INVERSE_RATE)
        invoice = (
            self.env["account.move"]
            .with_company(self.company)
            .create(
                {
                    "move_type": "out_invoice",
                    "company_id": self.company.id,
                    "journal_id": self.sale_journal.id,
                    "partner_id": self.partner.id,
                    "currency_id": self.usd.id,
                    "invoice_date": self.test_date,
                    "date": self.test_date,
                    "invoice_line_ids": self._prepare_demo_invoice_line_commands(),
                }
            )
        )
        invoice.action_post()
        igtf_rate = (self.company.l10n_ve_igtf_percent or 0.0) / 100.0
        first_payment_net_usd = 100.0
        amount_usd_gross_for_100_net = (
            self.usd.round(first_payment_net_usd / (1.0 - igtf_rate))
            if igtf_rate and igtf_rate < 1.0
            else first_payment_net_usd
        )
        pay_usd = self._register_invoice_payment(
            invoice=invoice,
            amount=amount_usd_gross_for_100_net,
            currency=self.usd,
            apply_igtf=True,
            igtf_included=False,
        )
        invoice.invalidate_recordset()
        residual_usd = invoice.amount_residual
        self.assertGreater(
            residual_usd,
            0.0,
            "Debe quedar saldo tras abonar 100 USD netos al documento (pago bruto con IGTF).",
        )
        amount_ves = self.ves.round(
            self.usd._convert(residual_usd, self.ves, self.company, self.test_date)
        )
        pay_ves = self._register_invoice_payment(
            invoice=invoice,
            amount=amount_ves,
            currency=self.ves,
            apply_igtf=False,
            igtf_included=False,
        )
        invoice.invalidate_recordset()
        self.assertTrue(
            self.usd.is_zero(invoice.amount_residual),
            "Tras 100 USD netos + resto en VES no debe quedar residual en USD (residual=%s)."
            % (invoice.amount_residual,),
        )
        payload = invoice._tfhka_build_documento_electronico_payload()
        enc = payload["documentoElectronico"]["encabezado"]
        totales = enc["totales"]
        otra = enc.get("totalesOtraMoneda")
        self.assertTrue(otra)
        self._assert_widget_and_formas_pago_split_usd_then_ves(
            invoice,
            pay_usd,
            pay_ves,
            residual_usd,
            amount_ves,
            totales,
            first_payment_net_usd=first_payment_net_usd,
        )
        self._assert_totales_company_matches_tax_totals(invoice, totales)
        self._assert_totales_otra_moneda_matches_tax_totals(invoice, otra)
