/** @odoo-module **/

import {patch} from "@web/core/utils/patch";
import {AccountPaymentField} from "@account/components/account_payment_field/account_payment_field";

patch(AccountPaymentField.prototype, {
    async removeMoveReconcile(moveId, partialId) {
        const action = await this.orm.call(
            this.props.record.resModel,
            "l10n_ve_igtf_get_unreconcile_action",
            [moveId, partialId],
            {}
        );
        if (action) {
            this.popover.close();
            let reloaded = false;
            await this.action.doAction(action, {
                onClose: async () => {
                    if (!reloaded) {
                        reloaded = true;
                        await this.props.record.model.root.load();
                    }
                },
            });
            if (!reloaded) {
                await new Promise((resolve) => setTimeout(resolve, 100));
                await this.props.record.model.root.load();
            }
            return;
        }
        this.popover.close();
        await this.orm.call(
            this.props.record.resModel,
            "js_remove_outstanding_partial",
            [moveId, partialId],
            {}
        );
        await this.props.record.model.root.load();
    },
});
