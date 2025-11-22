import os

# Nombre del módulo
MODULE_NAME = "l10n_ve_igtf_pro"

# Estructura de archivos y contenido
files = {
    f"{MODULE_NAME}/__init__.py": """from . import models""",
    f"{MODULE_NAME}/__manifest__.py": """# -*- coding: utf-8 -*-
{
    'name': 'Venezuela - IGTF Profesional (Odoo 18)',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Localizations',
    'author': 'Tu Partner de Confianza',
    'summary': 'Gestión integral del IGTF (3%) para Venezuela',
    'description': \"\"\"
        Módulo completo para la gestión del IGTF en Venezuela.
        Características:
        1. Configuración de % y Cuenta Contable en Ajustes.
        2. Selección de Diarios que aplican IGTF (Zelle, Efectivo USD).
        3. Cálculo automático del asiento de IGTF al pagar (si es pago exacto + impuesto aparte).
        4. Manejo de "Monto Todo Incluido" en el Wizard de Pagos (detecta diferencia como IGTF).
        5. Widget visual en la Factura para ver el estado del pago del IGTF.
    \"\"\",
    'depends': ['account'],
    'data': [
        'views/res_config_settings_view.xml',
        'views/account_journal_view.xml',
        'views/account_move_view.xml',
        'views/account_payment_register_view.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}
""",
    f"{MODULE_NAME}/models/__init__.py": """from . import res_company
from . import res_config_settings
from . import account_journal
from . import account_payment
from . import account_move
from . import account_payment_register
""",
    f"{MODULE_NAME}/models/res_company.py": """from odoo import fields, models

class ResCompany(models.Model):
    _inherit = 'res.company'

    igtf_percentage = fields.Float(string="Porcentaje IGTF", default=3.0)
    igtf_account_id = fields.Many2one('account.account', string="Cuenta Contable IGTF (Pasivo)")
""",
    f"{MODULE_NAME}/models/res_config_settings.py": """from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    igtf_percentage = fields.Float(related='company_id.igtf_percentage', readonly=False)
    igtf_account_id = fields.Many2one(related='company_id.igtf_account_id', readonly=False, domain="[('deprecated', '=', False)]")
""",
    f"{MODULE_NAME}/models/account_journal.py": """from odoo import fields, models

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    apply_igtf = fields.Boolean(string="Aplica IGTF (Venezuela)", help="Marca esta casilla si los pagos en este diario deben generar IGTF (ej. Zelle, Efectivo Divisa).")
""",
    f"{MODULE_NAME}/models/account_payment.py": """from odoo import models, fields, Command, _
from odoo.exceptions import UserError

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def action_post(self):
        res = super(AccountPayment, self).action_post()
        for payment in self:
            if payment.journal_id.apply_igtf and payment.amount > 0:
                self._create_igtf_entry(payment)
        return res

    def _create_igtf_entry(self, payment):
        company = payment.company_id
        if not company.igtf_account_id:
            return # Si no hay cuenta configurada, no bloqueamos, solo ignoramos.

        # IMPORTANTE: Evitar duplicidad.
        # Si el pago ya tiene una línea de diferencia (write-off) apuntando a la cuenta IGTF
        # (generada por el Wizard), entonces NO creamos este asiento automático extra.
        existing_igtf_line = payment.move_id.line_ids.filtered(
            lambda l: l.account_id == company.igtf_account_id
        )
        if existing_igtf_line:
            return

        tax_amount = payment.amount * (company.igtf_percentage / 100.0)

        move_vals = {
            'ref': f'IGTF: {payment.name}',
            'date': payment.date,
            'journal_id': payment.journal_id.id,
            'company_id': company.id,
            'move_type': 'entry',
            'line_ids': [],
        }

        # Lógica:
        # Inbound (Cliente paga): Debitamos Banco (Entra el dinero del impuesto) / Acreditamos IGTF por Pagar
        # Outbound (Pagamos Proveedor): Debitamos Gasto IGTF / Acreditamos Banco

        account_debit = payment.destination_account_id # Temporal
        account_credit = company.igtf_account_id.id

        if payment.payment_type == 'outbound':
            account_debit = company.igtf_account_id.id
            account_credit = payment.journal_id.default_account_id.id

        currency_id = payment.currency_id.id

        # Línea 1
        move_vals['line_ids'].append(Command.create({
            'name': f'IGTF Base {payment.amount}',
            'account_id': account_debit if payment.payment_type == 'outbound' else payment.journal_id.default_account_id.id,
            'debit': tax_amount if payment.payment_type == 'outbound' else 0.0,
            'credit': 0.0 if payment.payment_type == 'outbound' else tax_amount,
            'currency_id': currency_id,
            'amount_currency': tax_amount if payment.payment_type == 'outbound' else -tax_amount,
        }))

        # Línea 2 (Impuesto)
        move_vals['line_ids'].append(Command.create({
            'name': 'Impuesto IGTF (3%)',
            'account_id': account_credit if payment.payment_type == 'outbound' else company.igtf_account_id.id,
            'debit': 0.0 if payment.payment_type == 'outbound' else tax_amount,
            'credit': tax_amount if payment.payment_type == 'outbound' else 0.0,
            'currency_id': currency_id,
            'amount_currency': -tax_amount if payment.payment_type == 'outbound' else tax_amount,
        }))

        move = self.env['account.move'].create(move_vals)
        move.action_post()
""",
    f"{MODULE_NAME}/models/account_payment_register.py": """from odoo import models, fields, api

class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    igtf_included = fields.Boolean(string="Pago incluye IGTF (3%)")

    @api.onchange('igtf_included', 'amount')
    def _onchange_igtf_included(self):
        if not self.igtf_included:
            return

        # Si hay un pago en exceso (payment_difference > 0), lo asignamos al IGTF
        if self.payment_difference > 0:
            self.payment_difference_handling = 'reconcile'
            self.writeoff_account_id = self.company_id.igtf_account_id.id
            self.writeoff_label = 'IGTF Percibido (Incluido en pago)'

    def _create_payment_vals_from_wizard(self, batch_result):
        payment_vals = super()._create_payment_vals_from_wizard(batch_result)
        if self.igtf_included and self.payment_difference > 0:
            payment_vals.update({
                'writeoff_account_id': self.company_id.igtf_account_id.id,
                'writeoff_label': 'IGTF Percibido (Incluido en pago)',
            })
        return payment_vals
""",
    f"{MODULE_NAME}/models/account_move.py": """from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    igtf_status = fields.Selection([
        ('not_applicable', 'No Aplica'),
        ('pending', 'Pendiente'),
        ('partial', 'Parcial'),
        ('paid', 'Pagado')
    ], string="Estado IGTF", compute='_compute_igtf_status', store=False)

    igtf_amount_estimated = fields.Monetary(string="IGTF Estimado (3%)", compute='_compute_igtf_status', currency_field='company_currency_id')
    igtf_amount_paid = fields.Monetary(string="IGTF Registrado", compute='_compute_igtf_status', currency_field='company_currency_id')
    company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id')

    @api.depends('state', 'payment_state', 'currency_id', 'amount_total')
    def _compute_igtf_status(self):
        for move in self:
            if move.move_type not in ('out_invoice', 'out_refund') or move.currency_id == move.company_id.currency_id:
                move.igtf_status = 'not_applicable'
                move.igtf_amount_estimated = 0.0
                move.igtf_amount_paid = 0.0
                continue

            amount_converted = move.currency_id._convert(
                move.amount_total, move.company_id.currency_id, move.company_id, move.date or fields.Date.today()
            )
            igtf_estimated = amount_converted * (move.company_id.igtf_percentage / 100.0)
            move.igtf_amount_estimated = igtf_estimated

            igtf_paid_acc = 0.0
            reconciled_partials = move._get_all_reconciled_invoice_partials()

            for partial in reconciled_partials:
                counterpart_line = partial['counterpart_line_id']
                payment_move = counterpart_line.move_id

                # 1. Buscar asientos IGTF vinculados por referencia
                domain = [('ref', '=', f'IGTF: {payment_move.name}'), ('company_id', '=', move.company_id.id)]
                igtf_moves = self.env['account.move'].search(domain)
                for igtf_move in igtf_moves:
                    igtf_paid_acc += igtf_move.amount_total

                # 2. Buscar si el pago en sí mismo tiene el IGTF embebido (Caso Wizard con writeoff)
                # Buscamos líneas en ese pago que apunten a la cuenta IGTF
                embedded_igtf = payment_move.line_ids.filtered(lambda l: l.account_id == move.company_id.igtf_account_id)
                for line in embedded_igtf:
                    # El monto en la moneda de la compañía
                    igtf_paid_acc += abs(line.balance)

            move.igtf_amount_paid = igtf_paid_acc

            if igtf_paid_acc >= (igtf_estimated - 0.10):
                move.igtf_status = 'paid'
            elif igtf_paid_acc > 0:
                move.igtf_status = 'partial'
            else:
                move.igtf_status = 'pending'

    def action_register_manual_igtf(self):
        return {
            'name': 'Registrar IGTF Manual',
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment.register',
            'view_mode': 'form',
            'context': {
                'active_model': 'account.move',
                'active_ids': self.ids,
                'default_communication': f'IGTF Manual: {self.name}',
            },
            'target': 'new',
        }
""",
    f"{MODULE_NAME}/views/res_config_settings_view.xml": """<odoo>
    <record id="res_config_settings_view_form_igtf" model="ir.ui.view">
        <field name="name">res.config.settings.view.form.inherit.igtf</field>
        <field name="model">res.config.settings</field>
        <field name="inherit_id" ref="account.res_config_settings_view_form"/>
        <field name="arch" type="xml">
            <xpath expr="//block[@id='analytic']" position="after">
                <block title="Impuesto IGTF (Venezuela)" id="venezuela_igtf">
                    <setting string="Configuración IGTF">
                        <div class="content-group">
                            <div class="row mt16">
                                <label for="igtf_percentage" class="col-lg-3 o_light_label"/>
                                <field name="igtf_percentage"/>
                            </div>
                            <div class="row mt16">
                                <label for="igtf_account_id" class="col-lg-3 o_light_label"/>
                                <field name="igtf_account_id"/>
                            </div>
                        </div>
                    </setting>
                </block>
            </xpath>
        </field>
    </record>
</odoo>
""",
    f"{MODULE_NAME}/views/account_journal_view.xml": """<odoo>
    <record id="view_account_journal_form_igtf" model="ir.ui.view">
        <field name="name">account.journal.form.inherit.igtf</field>
        <field name="model">account.journal</field>
        <field name="inherit_id" ref="account.view_account_journal_form"/>
        <field name="arch" type="xml">
            <xpath expr="//field[@name='type']" position="after">
                <field name="apply_igtf"/>
            </xpath>
        </field>
    </record>
</odoo>
""",
    f"{MODULE_NAME}/views/account_move_view.xml": """<odoo>
    <record id="view_move_form_igtf_widget" model="ir.ui.view">
        <field name="name">account.move.form.igtf.widget</field>
        <field name="model">account.move</field>
        <field name="inherit_id" ref="account.view_move_form"/>
        <field name="arch" type="xml">
            <xpath expr="//group[@name='sale_total_group']" position="after">
                <group name="igtf_dashboard" string="Control IGTF (Venezuela)"
                       invisible="currency_id == company_currency_id">
                    <field name="company_currency_id" invisible="1"/>
                    <div class="o_row">
                        <span class="text-muted">Estado: </span>
                        <field name="igtf_status" widget="badge"
                               decoration-success="igtf_status == 'paid'"
                               decoration-warning="igtf_status == 'partial'"
                               decoration-danger="igtf_status == 'pending'"
                               decoration-muted="igtf_status == 'not_applicable'"/>
                    </div>
                    <field name="igtf_amount_estimated" widget="monetary" options="{'currency_field': 'company_currency_id'}"/>
                    <field name="igtf_amount_paid" widget="monetary" options="{'currency_field': 'company_currency_id'}"/>
                    <div class="mt8">
                        <button name="action_register_manual_igtf"
                                type="object"
                                string="Registrar IGTF Faltante"
                                class="btn btn-sm btn-outline-primary"
                                icon="fa-money"
                                invisible="igtf_status == 'paid'"/>
                    </div>
                </group>
            </xpath>
        </field>
    </record>
</odoo>
""",
    f"{MODULE_NAME}/views/account_payment_register_view.xml": """<odoo>
    <record id="view_account_payment_register_form_igtf" model="ir.ui.view">
        <field name="name">account.payment.register.form.igtf</field>
        <field name="model">account.payment.register</field>
        <field name="inherit_id" ref="account.view_account_payment_register_form"/>
        <field name="arch" type="xml">
            <xpath expr="//field[@name='amount']" position="after">
                <field name="igtf_included" widget="boolean_toggle"
                       invisible="currency_id == company_currency_id"/>
            </xpath>
            <xpath expr="//group[@name='group_payment_difference']" position="attributes">
                <attribute name="invisible">payment_difference == 0.0 or igtf_included</attribute>
            </xpath>
        </field>
    </record>
</odoo>
""",
}


def create_module():
    # Crear directorio principal
    if not os.path.exists(MODULE_NAME):
        os.makedirs(MODULE_NAME)
        print(f"Carpeta '{MODULE_NAME}' creada.")

    # Crear subdirectorios
    subdirs = ["models", "views"]
    for subdir in subdirs:
        path = os.path.join(MODULE_NAME, subdir)
        if not os.path.exists(path):
            os.makedirs(path)
            print(f"Carpeta '{path}' creada.")

    # Crear archivos
    for filepath, content in files.items():
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Archivo '{filepath}' creado.")

    print("\n¡Módulo generado exitosamente!")
    print("Pasos siguientes:")
    print("1. Copia la carpeta 'l10n_ve_igtf_pro' a tu directorio de addons de Odoo.")
    print("2. Reinicia el servicio de Odoo.")
    print("3. Actualiza la lista de aplicaciones e instala el módulo.")


if __name__ == "__main__":
    create_module()
