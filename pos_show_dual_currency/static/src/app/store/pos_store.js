/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { PosData } from "@point_of_sale/app/models/data_service";
// import { formatMonetary } from "@web/views/fields/formatters"; // Possible missing module in some asset bundles

// Patch PosData to intercept the load_data result
patch(PosData.prototype, {
    async loadInitialData() {
        const response = await super.loadInitialData(...arguments);
        if (!response || response.error) {
            console.warn(">>>>>>>> FAILED to load initial data or server error. PosData response:", response);
            return;
        }

        if (response && response.res_currency_ref) {
            console.log(">>>>>>>> Intercepted res_currency_ref in PosData Root:", response.res_currency_ref);
            // Aseguramos que el DataService tenga acceso directo si se inyectó en la raíz
            this.res_currency_ref = response.res_currency_ref;
        } else if (response && response["pos.session"]) {
            const sessionModel = response["pos.session"];
            if (sessionModel && (sessionModel.res_currency_ref || (sessionModel.data && sessionModel.data[0]))) {
                const res_currency_ref = sessionModel.res_currency_ref || (sessionModel.data && sessionModel.data[0] ? sessionModel.data[0].res_currency_ref : null);
                if (res_currency_ref) {
                    console.log(">>>>>>>> Intercepted res_currency_ref in PosData response:", res_currency_ref);
                    this.res_currency_ref = res_currency_ref;
                }
            } else {
                 console.log(">>>>>>>> res_currency_ref NOT found in RPC response for pos.session", sessionModel);
            }
        }

        return response;
    }
});

// Patch PosStore to use the intercepted data
patch(PosStore.prototype, {
    get_currency_ref() {
        // Pachacutec: v18.0.1.1.3 - Resolución de recursión infinita
        // 1. Try accessing from PosData if available (this.data is the data service in Odoo 18)
        if (this.data && this.data.res_currency_ref) {
            const data_ref = this.data.res_currency_ref;
            return Array.isArray(data_ref) ? data_ref[0] : data_ref;
        }

        // 2. Try accessing from session property
        const session = this.pos_session || this.session;
        if (session && session.res_currency_ref) {
            const sess_ref = session.res_currency_ref;
            return Array.isArray(sess_ref) ? sess_ref[0] : sess_ref;
        }

        // 3. Try finding it in the loaded models
        if (this.models && this.models['pos.session']) {
            const sessionModel = this.models['pos.session'];
            const sessionData = sessionModel.data || [sessionModel];
            if (Array.isArray(sessionData) && sessionData.length > 0) {
                const sess = sessionData.find(s => s.id === this.session?.id) || sessionData[0];
                if (sess && sess.res_currency_ref) return sess.res_currency_ref;
            }
        }

        return null;
    },

    // Getter seguro para uso en templates y otras lógicas
    get res_currency_ref() {
        return this.get_currency_ref();
    },

    format_currency_ref(value) {
        try {
            const currency = this.get_currency_ref() || {
                symbol: this.config?.show_currency_symbol || "$",
                position: this.config?.show_currency_position || "after",
                rounding: 0.01,
                decimal_places: 2,
                id: 999999 // Fallback ID
            };
            const amount = typeof value === 'number' ? value : parseFloat(value) || 0;
            const symbol = String(currency.symbol || "");
            const position = String(currency.position || "after");
            const decimals = parseInt(currency.decimal_places) || 2;

            // Pachacutec: Professional Venezuelan Formatting (Dots for thousands, comma for decimals)
            const parts = amount.toFixed(decimals).split('.');
            parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ".");
            const formatted_val = parts.join(',');

            return (position === 'before' ? symbol + ' ' : '') +
                formatted_val +
                (position === 'after' ? ' ' + symbol : '');
        } catch (e) {
            console.warn("Manual formatting in format_currency_ref failed:", e);
            const fallback_amount = typeof value === 'number' ? value : parseFloat(value) || 0;
            return fallback_amount.toFixed(2);
        }
    },

    getAmountInRefCurrency(amount, fromMainCurrency = false) {
        if (!amount && amount !== 0) return "";
        let rate = 1.0;
        let active_currency_ref = this.res_currency_ref;

        // Reconstruct res_currency_ref from config if missing
        if (!active_currency_ref && this.config) {
            active_currency_ref = {
                symbol: this.config.show_currency_symbol || "$",
                position: this.config.show_currency_position || "after",
                rounding: 0.01,
                decimal_places: 2,
                rate: this.config.show_currency_rate || 1.0,
            };
        }

        if (active_currency_ref && active_currency_ref.rate) {
            rate = active_currency_ref.rate;
        } else {
            rate = this.config.show_currency_rate;
        }

        if (typeof rate !== 'number') {
            rate = parseFloat(rate);
        }
        if (isNaN(rate) || rate === 0) rate = 1;

        let final_val = 0;
        const ref_symbol = active_currency_ref ? active_currency_ref.symbol : (this.config.show_currency_symbol || '$');

        // UNIFIED MATH (Pachacutec v18.0.1.0.95): 
        // Odoo Standard conversion uses MULTIPLICATION for Target = Base * rate
        // base_amount here is RefCurrency amount.
        if (fromMainCurrency) {
            // Odoo logic: USD = Bs * (USD/Bs_rate)
            final_val = amount * rate;
        } else {
            // From Ref to Main (Inverse): Bs = USD / (USD/Bs_rate)
            final_val = amount / rate;
        }

        return this.format_currency_ref(final_val);
    },

    getProductPriceFormatted(product, ref = false) {
        try {
            if (!product) return "";

            // Pachacutec: Priorizamos los campos cargados directamente del backend para evitar desincronización
            if (ref && product.list_price_usd && product.list_price_usd > 0) {
                // Si el producto tiene el campo maestro USD inyectado y es mayor a cero, lo usamos directamente
                return this.format_currency_ref(product.list_price_usd);
            }

            // Para el precio principal (Bs), usamos el campo lst_price nativo que ya viene calculado desde el backend
            let price = product.lst_price || 0;

            // Incluimos impuestos si aplica (la lógica nativa get_price podría ser necesaria para pricelists)
            if (this.pricelist) {
                try {
                    price = product.get_price(this.pricelist, 1);
                } catch (e) { }
            }

            const price_with_tax = this.get_product_price_with_tax(product, price);

            if (ref) {
                // Fallback si no hay list_price_usd: dividir por la tasa del sistema
                return this.getAmountInRefCurrency(price_with_tax, true);
            }

            const currency = this.currency || this.models["res.currency"].get(this.config.currency_id[0]) || { rounding: 0.01, symbol: "Bs", position: "after", decimal_places: 2 };

            if (currency) {
                // Pachacutec: Eliminamos la multiplicación redundante por rate. 
                // Aplicamos el mismo formato profesional (puntos para miles, comas para decimales)
                const decimals = currency.decimal_places || 2;
                const parts = price_with_tax.toFixed(decimals).split('.');
                parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ".");
                const formatted_val = parts.join(',');

                const curr_sym = typeof currency.symbol === 'symbol' ? '' : (currency.symbol || '');
                return (currency.position === 'before' ? curr_sym + ' ' : '') +
                    formatted_val +
                    (currency.position === 'after' ? ' ' + curr_sym : '');
            }
            return "" + price_with_tax.toFixed(2);
        } catch (e) {
            console.error("Error in getProductPriceFormatted:", e);
            return "";
        }
    },

    get_product_price_with_tax(product, price) {
        if (!product.taxes_id || product.taxes_id.length === 0) return price;

        let taxes = [];
        // 1. Try checking this.taxes (Odoo 16/17 style)
        if (this.taxes) {
            taxes = this.taxes.filter(t => product.taxes_id.includes(t.id));
        } else if (this.taxes_by_id) {
            taxes = product.taxes_id.map(id => this.taxes_by_id[id]).filter(Boolean);
        }

        // 2. Try checking Odoo 18 models service style
        if (taxes.length === 0 && this.models && this.models['account.tax']) {
            try {
                // If it's a DataStore collection
                const taxModel = this.models['account.tax'];
                if (typeof taxModel.getAll === 'function') {
                    taxes = taxModel.getAll().filter(t => product.taxes_id.includes(t.id));
                } else if (Array.isArray(taxModel)) {
                    taxes = taxModel.filter(t => product.taxes_id.includes(t.id));
                } else if (taxModel.data) {
                    taxes = taxModel.data.filter(t => product.taxes_id.includes(t.id));
                }
            } catch (e) { console.error("Error accessing models['account.tax']", e); }
        }

        if (taxes.length === 0) return price;

        try {
            // Compute taxes
            // Logic adapted for Odoo 18/Owl where compute_all might be a utility
            // or we use a simplified calculation for display if compute_all is missing

            const currency = this.currency || this.models["res.currency"].get(this.config.currency_id[0]);
            if (typeof this.compute_all === 'function' && currency) {
                // compute_all(taxes, price, quantity, currency)
                var all_taxes = this.compute_all(taxes, price, 1, currency.id);
                return all_taxes.total_included;
            } else if (this.get_taxes_after_fp) {
                // Fallback if compute_all is missing logic (unlikely in POS)
                return price;
            }
        } catch (error) {
            console.error("Error calculating tax:", error);
            return price;
        }
        return price;
    },

    get show_currency_rate_display() {
        // Pachacutec: v18.0.1.0.95 - Visual clarity for cashiers
        // We show the BCV rate (e.g. 477.14) even if internal rate is 0.002
        if (this.res_currency_ref && this.res_currency_ref.rate_ve) {
             return parseFloat(this.res_currency_ref.rate_ve).toFixed(4);
        }
        const rate = this.config.show_currency_rate_ve || (this.config.show_currency_rate > 0 ? (1.0 / this.config.show_currency_rate) : 0);
        return parseFloat(rate).toFixed(4);
    }
});
