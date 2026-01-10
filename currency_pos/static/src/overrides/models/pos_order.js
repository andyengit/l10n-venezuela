import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    setup(vals) {
        super.setup(vals);
        // Initialize exchange_currency_id
        this.exchange_currency_id = vals.exchange_currency_id || null;
    },

    /**
     * Get the current exchange currency for display (used by UI)
     */
    get_exchange_currency_for_display() {
        return this.exchange_currency_id;
    }
});
