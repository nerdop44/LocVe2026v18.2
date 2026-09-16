/** @odoo-module */

import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { FiscalPrinterMixin } from "@pos_fiscal_printer/app/utils/printing_mixin";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { NotaCreditoPopUp } from "@pos_fiscal_printer/app/popup/nota_credito_popup";

// Pachacutec: v139 - ReceiptScreen Patch para Odoo 18
// Maneja la integración con la impresora fiscal y asegura el cierre del puerto al finalizar.

const patchConfig = {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.pos = useService("pos"); // Needed for port getter

        // Initialize mixin properties
        Object.assign(this, {
            printerCommands: [],
            printing: false,
            read_s2: false,
            read_Z: false,
            writer: false,
            reader: false,
            verificar_desconexion: false,
        });
    },

    // Define accessors manually
    get port() {
        return this.pos.serialPort;
    },
    set port(serialPort) {
        this.pos.serialPort = serialPort;
    },

    get readerStream() {
        return this.port?.readable?.getReader();
    },

    get order() {
        return this.props?.order || this.pos?.get_order?.() || this.pos?.currentOrder;
    },

    async orderDone() {
        const order = this.props.order;
        const currentOrder = this.order; // El getter prioritiza props.order
        
        console.log("[FISCAL] v180 - Validando estado para Nueva Orden:", {
            props_order_id: order?.id,
            props_order_impresa: order?.impresa,
            props_order_num: order?.num_factura,
            current_order_id: currentOrder?.id,
            current_order_impresa: currentOrder?.impresa,
            current_order_num: currentOrder?.num_factura
        });

        // Pachacutec: v127 - Cierre de seguridad SIEMPRE al terminar el flujo de recibo
        try {
            await this.closePort();
        } catch (e) {
            console.warn("[FISCAL] Error no-crítico cerrando puerto en Nueva Orden:", e);
        }

        // Pachacutec: v180 - Fallback ultra-robusto
        // Consideramos éxito si CUALQUIERA de las referencias tiene la marca de impresión.
        const isImpresa = (order && (order.impresa || order.num_factura)) || 
                         (currentOrder && (currentOrder.impresa || currentOrder.num_factura));

        if (isImpresa) {
            console.log("[FISCAL] Validación exitosa. Avanzando a Nueva Orden.");
            super.orderDone();
        } else {
            console.warn("[FISCAL] No se detectó impresión fiscal en la orden actual.");
            this.dialog.add(ConfirmationDialog, {
                title: _t("Confirmación"),
                body: _t("Debe imprimir el documento fiscal. ¿Desea continuar sin imprimir?"),
                confirm: () => {
                    console.log("[FISCAL] El usuario eligió avanzar sin imprimir (Confirmado).");
                    super.orderDone();
                },
                cancel: () => { 
                    console.log("[FISCAL] Cierre cancelado por el usuario para reintentar impresión.");
                },
            });
        }
    }
};

// Explicitly assign mixin methods.
const mixinMethods = [
    'setPort', 'actionPrint', 'printViaUSB',
    'printViaApi', 'printZViaApi', 'printXViaApi',
    'write', 'write_s2', 'write_Z', 'escribe_leer',
    'setHeader', 'setLines', 'setTotal',
    'printFiscal', 'printNoFiscal', 'printNotaCredito',
    'doPrinting', 'fetchStatusDiagnosis', 'checkFiscalStatus', 'closePort'
];

for (const method of mixinMethods) {
    if (FiscalPrinterMixin[method]) {
        patchConfig[method] = FiscalPrinterMixin[method];
    }
}

patch(ReceiptScreen.prototype, patchConfig);
