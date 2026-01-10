import { Component, xml } from "@odoo/owl";
import { formatMonetary } from "@web/views/fields/formatters";
import { usePos } from "@point_of_sale/app/store/pos_hook";

export class CurrencyRatesWidget extends Component {
    static template = "currency_pos.CurrencyRatesWidget";
    static props = {};

    setup() {
        super.setup();
        this.pos = usePos();
        this.formatMonetary = formatMonetary;
    }

    mounted() {
    }

    get rates() {
        const rates = [];

        if (!this.pos || !this.pos.models) {
            return rates;
        }

        const currencyModel = this.pos.models["res.currency"];

        if (!currencyModel) {
            return rates;
        }

        const companyCurrencyId = this.pos.company?.currency_id?.id;

        currencyModel.forEach((currency) => {
            if (currency.id === companyCurrencyId) {
                return;
            }

            // Usar inverse_rate para la conversión (1 unidad de la moneda base = inverse_rate unidades de esta moneda)
            const rate = currency.inverse_rate || currency.rate || 1;

            rates.push({
                currency: currency,
                rate: rate,
                date: null,
            });
        });

        return rates;
    }

    get companyCurrency() {
        return this.pos?.company?.currency_id;
    }
}
