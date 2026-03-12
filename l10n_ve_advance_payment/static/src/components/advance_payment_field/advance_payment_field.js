/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { formatDate, deserializeDate } from "@web/core/l10n/dates";

import { formatMonetary } from "@web/views/fields/formatters";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component } from "@odoo/owl";

export class AdvancePaymentField extends Component {
    static props = { ...standardFieldProps };
    static template = "l10n_ve_advance_payment.AdvancePaymentField";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
    }

    getInfo() {
        const info = this.props.record.data[this.props.name] || {
            content: [],
            outstanding: true,
            title: "",
            move_id: this.props.record.resId,
        };
        for (const [key, value] of Object.entries(info.content || [])) {
            value.index = key;
            value.amount_formatted = formatMonetary(value.amount, {
                currencyId: value.currency_id,
            });
            if (value.date) {
                value.formattedDate = formatDate(deserializeDate(value.date));
            }
        }
        return {
            lines: info.content || [],
            title: info.title,
            moveId: info.move_id,
        };
    }

    async applyAdvance(moveId, advanceId) {
        const action = await this.orm.call(
            this.props.record.resModel,
            "l10n_ve_action_open_register_from_advance",
            [moveId, advanceId],
            {}
        );
        if (action) {
            await this.action.doAction(action, {
                onClose: async () => {
                    await this.props.record.model.root.load();
                },
            });
        }
    }
}

export const advancePaymentField = {
    component: AdvancePaymentField,
    supportedTypes: ["json", "char"],
};

registry.category("fields").add("l10n_ve_advance_payment", advancePaymentField);
