import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";
import { EventBus } from "@odoo/owl";

patch(PosStore.prototype, {
    async setup(...args) {
        await super.setup(...args);

        // Initialize global exchange currency
        this.exchange_currency_id = null;

        // Initialize event bus for currency changes
        this.currencyEventBus = new EventBus();
    },

    /**
     * Set the global exchange currency for the POS session
     */
    setExchangeCurrency(currency) {
        const oldCurrency = this.exchange_currency_id;
        this.exchange_currency_id = currency;

        // Emit change event for reactive updates
        if (oldCurrency !== currency) {
            this.currencyEventBus.trigger("change:exchange_currency_id", currency);
        }
    },

    /**
     * Get the global exchange currency for the POS session
     */
    getExchangeCurrency() {
        return this.exchange_currency_id || this.company?.currency_id;
    },

    /**
     * Get the exchange currency for display (used by UI)
     */
    getExchangeCurrencyForDisplay() {
        return this.exchange_currency_id;
    }
});
