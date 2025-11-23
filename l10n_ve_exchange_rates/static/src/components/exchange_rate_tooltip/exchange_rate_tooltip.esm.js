/** @odoo-module **/

import {Component, onWillStart, useState} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";
import {Dropdown} from "@web/core/dropdown/dropdown";
import {DropdownItem} from "@web/core/dropdown/dropdown_item";
import {registry} from "@web/core/registry";

export class ExchangeRateTooltip extends Component {
    static components = {Dropdown, DropdownItem};
    setup() {
        this.orm = useService("orm");
        this.state = useState({
            rates: [],
            company_currency: null,
            loading: false,
            showTooltip: false,
        });
        const d = new Date();
        this.currentDate = d.toLocaleString();

        onWillStart(() => this.getRates());
    }

    async getRates() {
        this.state.loading = true;
        try {
            const data = await this.orm.call(
                "res.currency",
                "get_exchange_rates",
                [],
                {}
            );
            this.state.rates = data.rates;
            this.state.company_currency = data.company_currency;
        } catch (error) {
            console.error("Error fetching exchange rates:", error);
        } finally {
            this.state.loading = false;
        }
    }
}

ExchangeRateTooltip.template = "l10n_ve_exchange_rates.ExchangeRateTooltip";

registry.category("systray").add("ExchangeRateTooltip", {
    Component: ExchangeRateTooltip,
    sequence: 1,
});
