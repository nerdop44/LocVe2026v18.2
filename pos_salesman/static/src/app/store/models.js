/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/app/models/pos_order";

// Pachacutec: v18 - Registro formal del campo en el esquema para evitar errores de getIndexMaps
// Nota: Odoo 18 requiere que las definiciones de campos sean consistentes en el arranque
try {
    PosOrder.fields = {
        ...PosOrder.fields,
        salesman_id: { type: "many2one", model: "hr.employee" },
    };
} catch(e) { console.error("[FISCAL] Error al registrar campos en PosOrder:", e); }

patch(PosOrder.prototype, {
    setup(_attr, options) {
        super.setup(...arguments);
        // Inicialización reactiva segura
        if (!this.salesman_id) this.salesman_id = null;
    },
    
    // Pachacutec: v204 - Aislamiento total. El vendedor es solo un campo informativo.
    // NUNCA debe tocar el objeto 'cashier' de la sesión.
    set_salesman_id(salesman) {
        try {
            // Guardamos el registro pero nos aseguramos de no disparar efectos secundarios en pos.cashier
            this.salesman_id = salesman;
            console.log(`[FISCAL] Vendedor asignado al pedido ${this.id || 'nuevo'}:`, salesman?.name || "Ninguno");
        } catch(e) {
            console.error("[FISCAL] Error reactivo al asignar vendedor:", e);
        }
    },
    
    get_salesman_id() {
        return this.salesman_id;
    },
    
    get_salesman_name() {
        return (this.salesman_id && typeof this.salesman_id === 'object') ? this.salesman_id.name : "";
    },

    // Odoo 18 maneja la serialización automáticamente si el campo está en fields,
    // pero mantenemos export_as_JSON por compatibilidad con el backend
    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.salesman_id = (this.salesman_id && typeof this.salesman_id === 'object') ? this.salesman_id.id : (this.salesman_id || false);
        return json;
    },
});

