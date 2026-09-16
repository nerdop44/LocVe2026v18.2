/** @odoo-module */

import { ProductProduct } from "@point_of_sale/app/models/product_product";
import { PosPayment } from "@point_of_sale/app/models/pos_payment";
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { PosData } from "@point_of_sale/app/models/data_service";
import DevicesSynchronisation from "@point_of_sale/app/store/devices_synchronisation";
import { patch } from "@web/core/utils/patch";
import { roundDecimals } from "@web/core/utils/numbers";

// Pachacutec: v18 - Registro formal de campos para evitar errores de getIndexMaps
// PosOrderline es un módulo independiente, podemos registrarlo aquí.
PosOrderline.fields = {
    ...PosOrderline.fields,
    x_is_igtf_line: { type: "boolean" },
};

// v18.0.1.0.48 - ESTABILIZACIÓN REACTIVA
// Eliminamos splice destructivos y reforzamos bloqueos globales para evitar
// colisiones con syncAllOrders de Odoo 18.

window.__pachacutec_global_lock = false;

// 1. Identificación del Producto IGTF
patch(ProductProduct.prototype, {
    get isIgtfProduct() {
        const config = this.models?.["pos.config"]?.getFirst();
        return config?.x_igtf_product_id ? config.x_igtf_product_id[0] === this.id : false;
    }
});

// 2. Bloqueo de Sincronización (Evita cascadas reactivas durante purgas)
patch(PosData.prototype, {
    localDeleteCascade(record, removeFromServer = false) {
        window.__pachacutec_global_lock = true;
        try {
            return super.localDeleteCascade(...arguments);
        } catch (e) {
            console.error("Pachacutec: localDeleteCascade crash suppressed:", e);
            return true;
        } finally {
            window.__pachacutec_global_lock = false;
        }
    }
});

patch(DevicesSynchronisation.prototype, {
    processDeletedRecords(deletedRecords) {
        window.__pachacutec_global_lock = true;
        try {
            return super.processDeletedRecords(...arguments);
        } catch (e) {
            console.error("Pachacutec: processDeletedRecords crash suppressed during sync:", e);
            return true;
        } finally {
            window.__pachacutec_global_lock = false;
        }
    }
});

// 3. Lógica de Divisas en Pagos
patch(PosPayment.prototype, {
    get isForeignExchange() {
        return this.payment_method_id?.x_is_foreign_exchange || false;
    },
    set_amount(value) {
        if (window.__pachacutec_global_lock) return super.set_amount(value);
        
        const config = this.models?.["pos.config"]?.getFirst();
        let amount = value;
        if (this.isForeignExchange && this.pos_order_id && config) {
            const rate = config.show_currency_rate;
            if (rate && rate > 0 && rate < 1) {
                amount = value / rate;
            }
        }
        super.set_amount(amount);
        
        if (this.pos_order_id && !window.__pachacutec_global_lock && typeof this.pos_order_id.refreshIGTF === "function") {
            try {
                this.pos_order_id.refreshIGTF();
            } catch (e) {
                console.warn("Pachacutec: refreshIGTF failed during set_amount", e);
            }
        }
    }
});

// 4. Identificación de Línea IGTF
patch(PosOrderline.prototype, {
    setup() {
        super.setup(...arguments);
        this.x_is_igtf_line = this.x_is_igtf_line || false;
        if (this.product_id?.isIgtfProduct) {
            this.x_is_igtf_line = true;
        }
    },
    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.x_is_igtf_line = json.x_is_igtf_line;
    },
    export_as_JSON() {
        const result = super.export_as_JSON();
        result.x_is_igtf_line = this.x_is_igtf_line;
        return result;
    },
    export_for_printing() {
        const json = super.export_for_printing(...arguments);
        json.x_is_igtf_line = this.x_is_igtf_line;
        return json;
    }
});

// 5. Gestión de Pedido y Protección de Memoria
patch(PosOrder.prototype, {
    // Reducción del Escudo: Solo detección, nunca alteración directa del arreglo (NO splice)
    _pachacutec_is_ghost(line) {
        return line && typeof line.getIndexMaps !== "function";
    },

    get_total_with_tax() {
        let total = super.get_total_with_tax();
        // Pachacutec: v75 - Sincronización de Total Visual
        // Evitamos que el widget se ponga en cero si falta el IGTF físico
        const igtf_monto = this.x_igtf_amount;
        const has_igtf_line = (this.lines || []).some(l => l && l.x_is_igtf_line);
        if (igtf_monto > 0.01 && !has_igtf_line) {
            return total + igtf_monto;
        }
        return total;
    },

    get_total_without_tax() {
        let total = super.get_total_without_tax();
        // Pachacutec: v75 - Subtotal Virtual
        // Si no hay línea de IGTF física, sumamos el monto virtual al subtotal
        // para que la UI de Odoo 18 no colapse a 0,00 Bs.
        const igtf_monto = this.x_igtf_amount;
        const has_igtf_line = (this.lines || []).some(l => l && l.x_is_igtf_line);
        if (igtf_monto > 0.01 && !has_igtf_line) {
            return total + igtf_monto;
        }
        return total;
    },

    getDisplayData() {
        return super.getDisplayData(...arguments);
    },

    get total_with_igtf() {
        return this.get_total_with_tax();
    },

    get sale_total_without_igtf() {
        return this.get_total_with_tax() - this.x_igtf_amount;
    },

    get igtf_base_bs() {
        // Pachacutec: v76 - Base de cálculo del IGTF (Suma de montos en divisas)
        const paymentLines = (this.payment_ids || []).filter(p => p && p.payment_method_id);
        return paymentLines
            .filter((p) => p.isForeignExchange)
            .map((p) => p.amount || 0)
            .reduce((prev, current) => prev + current, 0);
    },

    get x_igtf_amount() {
        if (window.__pachacutec_global_lock || !this.models) return 0;
        try {
            const paymentLines = (this.payment_ids || []).filter(p => p && p.payment_method_id);
            const foreignPayments = paymentLines.filter((p) => p.isForeignExchange);
            
            const igtf_monto = foreignPayments
                .map(({ amount, payment_method_id }) => {
                    const percentage = payment_method_id?.x_igtf_percentage || 3.0;
                    return (amount || 0) * (percentage / 100);
                })
                .reduce((prev, current) => prev + current, 0);

            const totalBase = (this.lines || [])
                .filter((p) => p && !p.x_is_igtf_line && !this._pachacutec_is_ghost(p))
                .map((p) => typeof p.get_price_with_tax === "function" ? p.get_price_with_tax() : 0)
                .reduce((prev, current) => prev + current, 0);

            return roundDecimals(Math.min(igtf_monto, totalBase * 0.031), 2);
        } catch (e) {
            return 0;
        }
    },
    set x_igtf_amount(value) { },

    update(vals, opts) {
        if (window.__pachacutec_global_lock) {
            super.update(vals, opts);
            return;
        }
        try {
            super.update(vals, opts);
        } catch (e) {
            if (e.message && e.message.includes("getIndexMaps")) {
                console.warn("Pachacutec: Supressing getIndexMaps crash during update", e);
            } else {
                throw e;
            }
        }
        if (vals.payment_ids && !window.__pachacutec_global_lock) {
            try {
                this.refreshIGTF();
            } catch (e) {
                console.warn("Pachacutec: refreshIGTF failed during update", e);
            }
        }
    },

    remove_paymentline(line) {
        super.remove_paymentline(line);
        if (!window.__pachacutec_global_lock) {
            this.refreshIGTF();
        }
    },

    refreshIGTF() {
        if (!this.models || this.finalized || window.__pachacutec_global_lock) return;
        
        window.__pachacutec_global_lock = true;
        try {
            this.removeIGTF();
            const config = this.models["pos.config"].getFirst();
            const igtf_monto = this.x_igtf_amount;
            const igtfProduct = config?.x_igtf_product_id;

            if (igtf_monto > 0.01 && igtfProduct) {
                const product = this.models["product.product"]?.get(igtfProduct[0]);
                if (product) {
                    const pos = this.pos || this.models["pos.config"]?.getFirst()?.env?.services?.pos || window.pos;
                    if (pos && typeof pos.addLineToCurrentOrder === 'function') {
                        pos.addLineToCurrentOrder(product, {
                            price: igtf_monto,
                            quantity: 1,
                            merge: false,
                            extras: {
                                price_type: "original",
                                x_is_igtf_line: true
                            }
                        }).then(() => {
                            console.log("[IGTF] v74 - Línea añadida con éxito, forzando recalculo y notificación...");
                            if (typeof this.recomputeOrderData === "function") {
                                this.recomputeOrderData();
                            }
                            // Pachacutec: v74 - Disparar evento para que OWL actualice los componentes
                            if (this.models) {
                                this.models.dispatchEvent("change", { record: this });
                            }
                        }).catch(e => console.warn("Pachacutec: Error async adding IGTF line", e));
                    }
                }
            }
        } catch (e) {
            console.error("Pachacutec: Error refreshing IGTF:", e);
        } finally {
            window.__pachacutec_global_lock = false;
        }
    },

    removeIGTF() {
        const linesToRemove = (this.lines || []).filter((l) => l && l.x_is_igtf_line);
        for (const line of linesToRemove) {
            if (line && !this._pachacutec_is_ghost(line) && typeof line.delete === "function") {
                try {
                    line.delete();
                } catch (e) {
                    console.warn("Pachacutec: Error deleting IGTF line", e);
                }
            }
        }
    }
});
