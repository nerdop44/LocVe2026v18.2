/** @odoo-module */

export class DataHelper {
    /**
     * @param {Object} pos - The POS instance
     * @param {Number} pmId - Payment Method ID
     * @returns {String} - 2-character printer code (default "01")
     */
    static getPaymentMethodCode(pos, pmId) {
        if (!pmId) return "01";
        const id = typeof pmId === 'object' ? pmId.id : pmId;

        // 1. Intentar desde el modelo reactivo (Odoo 18 Store)
        const pm = pos.models['pos.payment.method']?.get(id);
        if (pm) {
            if (pm.x_printer_code) {
                console.log(`[FISCAL] DataHelper - Código hallado en Modelo para PM ${pm.name} (${id}): ${pm.x_printer_code}`);
                return pm.x_printer_code.padStart(2, "0");
            } else {
                console.warn(`[FISCAL] DataHelper - PM ${pm.name} (${id}) NO tiene x_printer_code configurado.`);
            }
        }

        // 2. Intentar desde Datos Crudos (Safe Box)
        const rawData = pos.data?.["pos.payment.method"] || [];
        const found = rawData.find(r => r.id === id);
        if (found) {
            if (found.x_printer_code) {
                console.log(`[FISCAL] DataHelper - Código hallado en Data Cruda para PM ${found.name} (${id}): ${found.x_printer_code}`);
                return found.x_printer_code.padStart(2, "0");
            } else {
                console.warn(`[FISCAL] DataHelper - PM ${found.name} en Data Cruda NO tiene x_printer_code.`);
            }
        }

        console.warn(`[FISCAL] DataHelper - Fallback '01' para PM ID ${id}`);
        return "01";
    }

    /**
     * @param {Object} pos - The POS instance
     * @param {Object} partner - The Partner object
     * @returns {String} - Sanitized RIF (e.g., V12345678)
     */
    static getFullVat(pos, partner) {
        if (!partner) return "V00000000";
        
        // Pachacutec: v202 - Reconstrucción Blindada con Padding Mandatorio
        const rawVat = (partner.vat || "").toString().toUpperCase().replace(/[^A-Z0-9]/g, "");
        let prefix = "V";
        let numericPart = "";

        if (rawVat.match(/^[A-Z]\d+$/)) {
            prefix = rawVat.substring(0, 1);
            numericPart = rawVat.substring(1);
        } else if (rawVat.match(/^\d+$/)) {
            prefix = partner.prefix_vat || "V";
            numericPart = rawVat;
        } else {
            // Caso fallback si el VAT está muy mal formado o vacío
            return rawVat || "V00000000";
        }

        // Padding mandatorio a 8 dígitos (Total 9 chars con prefijo)
        // Evita el NAK 21 en impresoras HKA para RIFs de personas naturales de 7 dígitos.
        const paddedNumeric = numericPart.padStart(8, "0");
        const finalVat = `${prefix}${paddedNumeric}`;
        
        console.log(`[FISCAL] DataHelper - RIF Normalizado: ${rawVat} -> ${finalVat}`);
        return finalVat;
    }
}
