/** @odoo-module */
import { _t } from "@web/core/l10n/translation";
import { NotaCreditoPopUp } from "@pos_fiscal_printer/app/popup/nota_credito_popup";
import { DataHelper } from "./data_helper";

const encoder = new TextEncoder();
const CHAR_MAP = {
    "ñ": "n", "Ñ": "N", "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u",
    "Á": "A", "É": "E", "Í": "I", "Ó": "O", "Ú": "U", "ä": "a", "ë": "e",
    "ï": "i", "ö": "o", "ü": "u", "Ä": "A", "Ë": "E", "Ï": "I", "Ö": "O", "Ü": "U",
};
const EXPRESSION = new RegExp(`[${Object.keys(CHAR_MAP).join("")}]`, "g");

// Pachacutec: v67 - cleanText RADICAL (NFD + UpperCase) - Preservando espacios
export function cleanText(string) {
    if (!string) return "";
    try {
        let clean = string.normalize("NFD");
        clean = clean.replace(/[\u0300-\u036f]/g, "");
        clean = clean.replace(/ñ/g, "n").replace(/Ñ/g, "N");
        clean = clean.toUpperCase();
        clean = clean.replace(/[^\x20-\x7E]/g, "");
        // Pachacutec: v67 - Eliminar .trim() para que el padding de 40 sea exacto
        return clean.replace(/[!|*]/g, " ");
    } catch (e) {
        console.error("Error en cleanText v67:", e);
        return String(string).toUpperCase().replace(/[^\x20-\x7E]/g, "");
    }
}

// Pachacutec: v66 - Restauración Estricta XOR v16 (1 solo byte de Checksum)
// Pachacutec: v73 - Restauración XOR Binario (1 solo byte)
// Requisito final HKA: 1 solo byte binario para el checksum.
// Pachacutec: v96 - Protocolo Híbrido Validado (XOR Inteligente)
// - Cabeceras ('i'): El Checksum (LRC) es DATA ^ ETX. STX (2) queda FUERA. Correcto para ACK.
// - Ventas/Pagos ('!', ' ', '2', etc.): El Checksum DEBE incluir STX (2) para el "Resultado 9".
// Pachacutec: v168 - Motor de Checksum de Grado Industrial (Manual Fidelity)
// - Eliminado: Bucle for...of (Causaba truncado errático en Chrome Assets).
// - Implementado: Bucle de índice tradicional sobre Uint8Array (Integridad 100%).
// - LRC = [DATA XOR CMD] ^ ETX. STX (2) queda FUERA según Manual Pág. 17.
export function toBytes(command) {
    const encoder = new TextEncoder();
    const data = encoder.encode(command);
    const ETX = 3;
    const STX = 2;

    let lrc = 0;
    // Bucle robusto sobre el buffer de bytes real
    for (let i = 0; i < data.length; i++) {
        lrc ^= data[i];
    }
    lrc ^= ETX;

    // Construcción atómica de la trama: [STX, DATA, ETX, LRC]
    const frame = new Uint8Array(data.length + 3);
    frame[0] = STX;
    frame.set(data, 1);
    frame[data.length + 1] = ETX;
    frame[data.length + 2] = lrc;

    return frame;
}

// FiscalPrinterMixin as a plain object with methods only.
// Getters for 'port' and 'readerStream' must be defined on the component ensuring this mixin.
export const FiscalPrinterMixin = {
    async setPort() {
        try {
            if (!this.port) {
                const ports = await navigator.serial.getPorts();
                console.log("Puertos ya autorizados:", ports.length);
                let port;

                // Detailed info for debugging
                for (const p of ports) {
                    const info = p.getInfo();
                    console.log("Info puerto:", info);
                }

                // If there's only one authorized port, we might try it, but safer to request if it fails
                if (ports.length === 1) {
                    port = ports[0];
                    console.log("Intentando reutilizar puerto único autorizado...");
                } else {
                    console.log("Solicitando selección de puerto al usuario...");
                    port = await navigator.serial.requestPort();
                }

                // Pachacutec: v133 - BAUD 9600 (Alineación Éxito v16)
                const parity = "even";
                const baudRate = 9600;
                console.warn("[FISCAL] v133 - Alineación Éxito v16: 9600 baudios, Parity: Even");

                try {
                    await port.open({
                        baudRate: baudRate,
                        parity: parity,
                        dataBits: 8,
                        stopBits: 1,
                    });
                    console.log("Puerto abierto exitosamente a 9600.");
                } catch (e) {
                    if (e.name === "InvalidStateError") {
                        console.log("El puerto ya estaba abierto. Continuando...");
                    } else if (ports.length >= 1 && (e.name === "NetworkError" || e.name === "SecurityError")) {
                        console.warn("Fallo al reutilizar puerto persistente (" + e.name + "), solicitando nuevo...");
                        port = await navigator.serial.requestPort();
                        await port.open({
                            baudRate: baudRate,
                            parity: parity,
                            dataBits: 8,
                            stopBits: 1,
                        });
                    } else {
                        throw e;
                    }
                }
                this.port = port;
            }
            return true;
        } catch (error) {
            console.error("Error crítico en setPort:", error);
            let msg = _t("Error al abrir el puerto serial.");
            if (error.name === "NetworkError") {
                msg = _t("El puerto está siendo usado por otra aplicación o no tiene permisos.");
            }
            this.env.services.notification.add(msg + " (" + error.name + ")", { type: "danger" });
            this.port = false;
            return false;
        }
    },

    async escribe_leer(command, is_linea, is_retry = false) {
        if (!this.port) return false;
        var comando_cod = toBytes(command);
        console.log("Escribiendo comando: ");
        console.log(command)
        console.log("Comando codificado: ");
        console.log(comando_cod);

        this.writer = this.port.writable.getWriter();
        var signals_to_send = { dataTerminalReady: true };
        if (this.pos.config.connection_type === "usb_serial") {
            signals_to_send = { requestToSend: true };
        }
        try {
            await this.port.setSignals(signals_to_send);
        } catch (e) {
            console.warn("Error al setear señales (normal en emuladores):", e);
        }

        var signals = { clearToSend: true, dataSetReady: true };
        try {
            signals = await this.port.getSignals();
            console.log("signals: ", signals);
        } catch (e) {
            console.warn("Error al leer señales (normal en emuladores):", e);
        }

        if (this.pos.config.connection_type === "usb_serial") {
            console.log("signals DSR: ", signals.dataSetReady);
            console.log("signals CTS: ", signals.clearToSend);
        } else {
            console.log("signals CTS: ", signals.clearToSend);
            console.log("signals DSR: ", signals.dataSetReady);
        }
        if (signals.clearToSend || signals.dataSetReady) {
            await new Promise(
                (res) => setTimeout(() => res(this.writer.write(comando_cod)), 20)
            );
            await this.writer.releaseLock();
            this.writer = false;
            if (this.read_Z) {
                console.log("Esperando 12 seundos para leer Z o X....");
                await new Promise(
                    (res) => setTimeout(() => res(), 12000)
                );
            }
            console.log("Empezando lectura");
            while (!this.port.readable) {
                console.log("Esperando puerto");
                if (this.reader) {
                    await this.reader.releaseLock();
                    this.reader = false;
                }
                await new Promise(
                    (res) => setTimeout(() => res(), 50)
                );
            }

            await new Promise(
                (res) => setTimeout(() => res(), 10)
            );
            if (this.reader) {
                await this.reader.releaseLock();
                this.reader = false;
            }
            if (this.port.readable) {
                this.reader = this.port.readable.getReader();
                var leer = true;
            } else {
                var leer = false;
            }

            var esperando = 0;
            var responseData = [];
            while (leer) {
                try {
                    const { value, done } = await this.reader.read();
                    if (value && value.byteLength >= 1) {
                        console.log("Respuesta de comando: ", value, " Byte 0: ", value[0]);
                        
                        // Si es un comando de status (S1, S2, S3), la impresora responde con STX (2) + DATA + ETX (3) + LRC
                        if (command.length === 2 && command.startsWith("S") && value[0] === 2) {
                            responseData = Array.from(value);
                            console.log("[FISCAL] v74 - Respuesta Status detectada:", responseData);
                            leer = false;
                            await this.reader.releaseLock();
                            this.reader = false;
                            return responseData; // Devolvemos la trama completa
                        } else if (value[0] == 6) {
                            console.log("Comando aceptado (ACK)");
                            leer = false;
                            await this.reader.releaseLock();
                            this.reader = false;
                            return true;
                        } else {
                            // Pachacutec: v256 - Gestión Inteligente de NAK
                            if (command === "7") {
                                console.log("[FISCAL] v256 - Impresora limpia (NAK 21 en CMD 7). Procediendo sin alarmar al usuario.");
                            } else {
                                console.error("[FISCAL] v256 - Comando RECHAZADO (NAK ", value[0], ").");
                                this.env.services.notification.add(_t("Error Fiscal: Comando Rechazado (NAK ").concat(value[0], ")."), { type: "danger" });
                            }
                            
                            leer = false;
                            await this.reader.releaseLock();
                            this.reader = false;
                            
                            /* 
                            // Pachacutec: v201 - Bloque de anulación comentado para evitar corte anticipado
                            await new Promise((res) => setTimeout(() => res(), 100));
                            this.writer = this.port.writable.getWriter();
                            const unlockCmd = toBytes("7");
                            await new Promise(res => setTimeout(async () => {
                                await this.writer.write(unlockCmd);
                                res();
                            }, 150));
                            await this.writer.releaseLock();
                            this.writer = false;
                            */
                            
                            return false; // Retorna false para indicar fallo mandatorio
                        }
                    } else {
                        console.log("No hay datos...");
                        esperando++;
                        await new Promise(res => setTimeout(res, 200));
                    }
                    if (esperando > 20) {
                        console.error("[FISCAL] Timeout esperando respuesta");
                        this.printing = false;
                        leer = false;
                        break;
                    }
                } catch (error) {
                    console.error("Error al leer puerto:", error);
                    leer = false;
                } finally {
                    if (this.reader) {
                        try { 
                            await this.reader.cancel();
                            await this.reader.releaseLock(); 
                        } catch (e) { }
                        this.reader = false;
                    }
                }
            }
            return false;
        } else {
            console.log("Error signals CTS: ", signals);
            this.printing = false;
            return false;
        }
    },

    async write() {
        this.modal_imprimiendo = Swal.fire({
            title: 'Imprimiendo',
            text: 'Por favor espere.',
            imageUrl: '/pos_fiscal_printer/static/src/image/impresora.gif',
            imageWidth: 100,
            imageHeight: 100,
            imageAlt: 'Imprimiendo',
            allowOutsideClick: false,
            allowEscapeKey: false,
            allowEnterKey: false,
            showConfirmButton: false,
        });

        // ELIMINADO: v86 - Limpieza inicial (Comando 7)
        // Se elimina en v87 porque causaba NAK innecesario en algunos equipos.
        
        const TIME = this.pos.config.x_fiscal_commands_time || 750;
        this.printing = true;
        let print_success = true;
        console.log("Comandos a enviar: ", this.printerCommands);
        
        for (const command of this.printerCommands) {
            var is_linea = false;
            if (command.substring(0, 1) === ' ' || command.substring(0, 1) === '!' || command.substring(0, 1) === 'd' || command.substring(0, 1) === '-') {
                is_linea = true;
            }
            if (this.printing) {
                console.log(`[FISCAL] v255 - Procesando Comando: ${command}`);
                let success = await new Promise((res) => {
                    const extra_delay = (command === '3' || command.substring(0, 1) === '1') ? 1000 : 0;
                    setTimeout(async () => {
                        const res_ok = await this.escribe_leer(command, is_linea);
                        res(res_ok);
                    }, TIME + extra_delay);
                });

                if (!success) {
                    const isPreventive = (command === '7' || command.startsWith('i'));
                    if (isPreventive) {
                        console.warn(`[FISCAL] v255 - Ignorando NAK en comando preventivo (${command}). Manteniendo flujo activo.`);
                        this.printing = true; // REFUERZO: Asegurar que el flag de impresión siga activo
                        continue;
                    }

                    if (command.startsWith('2')) {
                        const code = command.substring(1, 3);
                        const amountStr = command.substring(3);
                        const currentTotalLen = amountStr.length;
                        const newIntPad = (currentTotalLen === 17) ? 10 : 15;
                        const altTotalLen = newIntPad + 2;
                        const rawInt = amountStr.substring(0, currentTotalLen - 2).replace(/^0+/, '');
                        const rawDec = amountStr.substring(currentTotalLen - 2);
                        const altAmountStr = rawInt.padStart(newIntPad, "0") + rawDec;
                        const retryCommand = "2" + code + altAmountStr;
                        
                        console.warn(`[FISCAL] v255 - NAK 21 en Pago. Probando Fallback (${altTotalLen} dig):`, retryCommand);
                        const retrySuccess = await this.escribe_leer(retryCommand, false);
                        if (retrySuccess) {
                            console.log(`[FISCAL] v255 - Reintento exitoso con ${altTotalLen} dígitos.`);
                            this.printing = true; // REFUERZO
                            continue; 
                        }
                    }

                    console.error("[FISCAL] v255 - Error CRÍTICO en comando mandatorio:", command);
                    print_success = false;
                    this.printing = false;
                    break;
                }
            }
        }

        this.modal_imprimiendo.close();
        if (print_success) {
            console.log("Comandos finalizados con éxito");
            if (this.order) {
                this.order.impresa = true;
                Swal.fire({
                    position: 'top-end',
                    icon: 'success',
                    title: 'Impresión finalizada con éxito',
                    showConfirmButton: false,
                    timer: 1500
                });
            }
        } else {
            console.error("Error en impresion, factura anulada o incompleta");
            Swal.fire({
                position: 'top-end',
                icon: 'error',
                title: 'Error en impresion, factura anulada',
                showConfirmButton: false,
                timer: 2500
            });
        }

        window.clearTimeout(this.timeout);
        this.printerCommands = [];
        this.printing = false;

        this.writer = false;
        if (this.read_s2 && print_success) {
            //mandar comando S2 y leer
            await this.write_s2();

        }
        if (this.read_Z) {
            //mandar comando Z y leer
            const { confirmed } = await this.showPopup("ReporteZPopUp", { cancelKey: "Q", confirmKey: "Y" });
            if (confirmed) {
                await this.write_Z();
            }

        }
        console.log("Factura finalizada.");
    },

    async write_s2() {
        this.writer = this.port.writable.getWriter();
        const TIME = this.pos.config.x_fiscal_commands_time || 750;
        this.printerCommands = ["S1"];
        this.printerCommands = this.printerCommands.map(toBytes);
        console.log("Escribiendo S1", this.printerCommands);
        for (const command of this.printerCommands) {
            await new Promise(
                (res) => setTimeout(() => res(this.writer.write(command)), TIME)
            );
        }
        window.clearTimeout(this.timeout);
        this.printerCommands = [];
        await this.writer.releaseLock();
        this.writer = false;
        var signals_to_send = { dataTerminalReady: true };
        if (this.pos.config.connection_type === "usb_serial") {
            signals_to_send = { requestToSend: true };
        }
        try {
            await this.port.setSignals(signals_to_send);
        } catch (e) {
            console.warn("Error al setear señales (normal en emuladores):", e);
        }

        console.log("Leyendo S1", this.port.readable)

        var signals = { clearToSend: true, dataSetReady: true };
        try {
            signals = await this.port.getSignals();
            console.log("signals: ", signals);
        } catch (e) {
            console.warn("Error al leer señales (normal en emuladores):", e);
        }

        if (this.pos.config.connection_type === "usb_serial") {
            console.log("signals DSR: ", signals.dataSetReady);
            console.log("signals CTS: ", signals.clearToSend);
        } else {
            console.log("signals CTS: ", signals.clearToSend);
            console.log("signals DSR: ", signals.dataSetReady);
        }
        if (signals.clearToSend || signals.dataSetReady) {
            if (this.reader) {
                this.reader.releaseLock();
                this.reader = false;
            }
            if (this.port.readable) {
                this.reader = this.port.readable.getReader();
            }
            var leer = true;
            var contador = 0;
            while (this.port.readable && leer) {
                try {
                    while (leer) {
                        const { value, done } = await this.reader.read();
                        var string = new TextDecoder().decode(value);
                        console.warn("[FISCAL] Respuesta S1 recibida:", string);
                        
                        if (string.length > 0) {
                            // Pachacutec: v36 - CAPTURA ROBUSTA CON REGEX (Compatible con cualquier impresora HKA)
                            // Buscamos una secuencia de dígitos (generalmente 8 o más) que represente el número fiscal
                            const match = string.match(/\d{5,15}/g); 
                            if (match && match.length > 0) {
                                // El número de factura suele ser el último o penúltimo grupo de números grandes
                                // En HKA-NG el reporte S1 devuelve varios campos, el correlativo es clave.
                                const num_factura = match[match.length - 1]; 
                                console.warn("[FISCAL] Numero de factura extraído con Regex: ", num_factura);
                                this.order.num_factura = num_factura.padStart(8, "0");
                                leer = false;
                                break;
                            } else {
                                contador++;
                                await new Promise(res => setTimeout(res, 200));
                                if (contador > 15) { leer = false; break; }
                            }
                        } else {
                            contador++;
                            await new Promise(res => setTimeout(res, 200));
                            if (contador > 15) { leer = false; break; }
                        }
                    }
                } catch (error) {
                    leer = false;
                    console.error("Error en lectura write_s2:", error);
                } finally {
                    leer = false;
                    if (this.reader) {
                        try {
                            await this.reader.cancel();
                            await this.reader.releaseLock();
                        } catch (e) {
                            console.warn("[FISCAL] Error al liberar reader en write_s2:", e);
                        }
                        this.reader = false;
                    }
                }
            }

            // Pachacutec: v37 - Persistencia garantizada del estado 'impresa'
            if (this.order.num_factura) {
                console.log("[FISCAL] v180 - Marcando orden ante todas las referencias disponibles.");
                
                // Pachacutec: v180 - Asignación directa y robusta
                this.order.impresa = true;
                
                // Fallback: Si props.order es diferente, actualizarlo también
                if (this.props?.order && this.props.order !== this.order) {
                    this.props.order.impresa = true;
                    this.props.order.num_factura = this.order.num_factura;
                }

                await this.orm.call(
                    'pos.order',
                    'set_num_factura',
                    [this.order.id, this.order.name, this.order.num_factura]
                );
            } else {
                console.error("[FISCAL] v180 - Imposible marcar como impresa: número de factura no extraído.");
            }

        }

        this.printerCommands = [];
        this.read_s2 = false;
    },

    async write_Z() {
        this.read_Z = true;
        const TIME = this.pos.config.x_fiscal_commands_time || 750;
        
        // Pachacutec: v182 - REPORTE Z DINÁMICO (Sin manejo manual de writer para evitar TypeError)
        this.printerCommands = ["I0Z"]; 
        const command = this.printerCommands[0];
        
        const success = await this.escribe_leer(command, false);
        if (!success) {
            console.error("[FISCAL] v182 - Error al solicitar Reporte Z.");
            this.read_Z = false;
            return;
        }

        window.clearTimeout(this.timeout);
        this.printerCommands = [];
        
        // Espera de seguridad para el firmware durante el proceso de impresión física del Z
        await new Promise(
            (res) => setTimeout(() => res(), 12000)
        );
        
        console.log("Leyendo respuesta extendida del Z Report...");
        this.reader = false;
        if (this.port.readable) {
            this.reader = this.port.readable.getReader();
        }

        while (this.port.readable && this.read_Z) {
            try {
                while (this.read_Z) {
                    const { value, done } = await this.reader.read();
                    if (done) {
                        console.log("Lectura finalizada.");
                        this.read_Z = false;
                        if (this.reader) {
                            this.reader.releaseLock();
                            this.reader = false;
                        }
                        break;
                    }
                    var string = new TextDecoder().decode(value);
                    console.log(string);
                    const myArray = string.split('\n');
                    console.log(myArray);
                    // Break loop after receiving data to prevent hanging
                    if (string.length > 0) {
                        this.read_Z = false;
                        break;
                    }
                }
            } catch (error) {
                console.error("Error en lectura write_Z:", error);
                this.read_Z = false;
            } finally {
                if (this.reader) {
                    try {
                        this.reader.releaseLock();
                    } catch (e) { }
                    this.reader = false;
                }
            }
        }

        this.printerCommands = [];
        this.read_Z = false;
    },

    async actionPrint() {
        if (this.pos.config.connection_type === "api") {
            return this.printViaApi();
        }

        if (this.printing_lock) {
            console.warn("[FISCAL] Bloqueo de concurrencia activo. Esperando...");
            return;
        }
        this.printing_lock = true;
        try {
            const result = await this.setPort();
            if (!result) return;
            await this.write();
        } finally {
            await this.closePort();
            this.printing_lock = false;
        }
    },

    async printViaUSB() {
        console.log("Detectando dispositivos via USB");
        let devices = await navigator.usb.getDevices();
        devices.forEach(device => {
            alert(device);
            if (device.productName === "Fiscal Printer") {
                console.log("Impresora Fiscal encontrada");
                this.device = device;
            }
        });
        Swal.fire({
            icon: 'error',
            title: 'Error en impresion, conexión via USB no disponible',
            showConfirmButton: true,
        });
    },

    async printZViaApi() {
        console.log("Imprimiendo Reporte Z via API");
        this.modal_imprimiendo = Swal.fire({
            title: 'Imprimiendo',
            text: 'Por favor espere.',
            imageUrl: '/pos_fiscal_printer/static/src/image/impresora.gif',
            imageWidth: 100,
            imageHeight: 100,
            imageAlt: 'Imprimiendo',
            allowOutsideClick: false,
            allowEscapeKey: false,
            allowEnterKey: false,
            showConfirmButton: false,
            timer: 1500
        });
        var url = this.pos.config.api_url + "/zreport/print";
        try {
            const response = await fetch(url, {
                headers: {
                    'Bypass-Tunnel-Reminder': 'true'
                },
                credentials: 'include'
            });
            if (response.ok) {
                Swal.fire({
                    position: 'top-end',
                    icon: 'success',
                    title: 'Impresión finalizada con éxito',
                    showConfirmButton: false,
                    timer: 1500
                });
            } else {
                Swal.fire({
                    icon: 'error',
                    title: 'Error en impresión',
                    showConfirmButton: true,
                });
            }
        } catch (error) {
            console.error("Error en printZViaApi:", error);
            Swal.fire({
                icon: 'error',
                title: 'Error de conexión con la API',
                text: error.message,
                showConfirmButton: true,
            });
        } finally {
            if (this.modal_imprimiendo) {
                this.modal_imprimiendo.close();
            }
        }
    },

    async printXViaApi() {
        console.log("Imprimiendo Reporte X via API");
        this.modal_imprimiendo = Swal.fire({
            title: 'Imprimiendo',
            text: 'Por favor espere.',
            imageUrl: '/pos_fiscal_printer/static/src/image/impresora.gif',
            imageWidth: 100,
            imageHeight: 100,
            imageAlt: 'Imprimiendo',
            allowOutsideClick: false,
            allowEscapeKey: false,
            allowEnterKey: false,
            showConfirmButton: false,
            timer: 1500
        });
        var url = this.pos.config.api_url + "/xreport/print";
        try {
            const response = await fetch(url, {
                headers: {
                    'Bypass-Tunnel-Reminder': 'true'
                },
                credentials: 'include'
            });
            if (response.ok) {
                Swal.fire({
                    position: 'top-end',
                    icon: 'success',
                    title: 'Impresión finalizada con éxito',
                    showConfirmButton: false,
                    timer: 1500
                });
            } else {
                Swal.fire({
                    icon: 'error',
                    title: 'Error en impresión',
                    showConfirmButton: true,
                });
            }
        } catch (error) {
            console.error("Error en printXViaApi:", error);
            Swal.fire({
                icon: 'error',
                title: 'Error de conexión con la API',
                text: error.message,
                showConfirmButton: true,
            });
        } finally {
            if (this.modal_imprimiendo) {
                this.modal_imprimiendo.close();
            }
        }
    },

    async printViaApi() {
        console.log("Imprimiendo via API");
        this.modal_imprimiendo = Swal.fire({
            title: 'Imprimiendo',
            text: 'Por favor espere.',
            imageUrl: '/pos_fiscal_printer/static/src/image/impresora.gif',
            imageWidth: 100,
            imageHeight: 100,
            imageAlt: 'Imprimiendo',
            allowOutsideClick: false,
            allowEscapeKey: false,
            allowEnterKey: false,
            showConfirmButton: false,
        });

        const commands = this.printerCommands; // v52 - No mas map(sanitize) aqui
        console.warn("[FISCAL] printViaApi - Comandos a enviar:", commands);

        var body = JSON.stringify({
            params: {
                cmd: commands
            }
        });

        var url = this.pos.config.api_url + "/print_pos_ticket";

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Bypass-Tunnel-Reminder': 'true'
                },
                body: body,
                credentials: 'include'
            });

            this.modal_imprimiendo.close();

            if (response.ok) {
                const data = await response.json();
                const result = data.result;

                if (result) {
                    console.warn("[FISCAL] printViaApi - Resultado de la API:", result);
                    if (result.state && result.state.lastInvoiceNumber) {
                        this.order.impresa = true;
                        console.log("Finalizada con factura " + result.state.lastInvoiceNumber.toString());
                        this.order.num_factura = result.state.lastInvoiceNumber.toString();

                        // Use this.pos.orm.call if available, or this.orm.call
                        const orm = this.orm || this.env?.services?.orm;
                        if (orm) {
                            await orm.call(
                                'pos.order',
                                'set_num_factura',
                                [this.order.id, this.order.name, this.order.num_factura]
                            );
                        }

                        Swal.fire({
                            position: 'top-end',
                            icon: 'success',
                            title: 'Impresión finalizada con éxito',
                            showConfirmButton: false,
                            timer: 1500
                        });
                    } else {
                        console.log("No hay numero de factura");
                        Swal.fire({
                            position: 'top-end',
                            icon: 'success',
                            title: 'Impresión finalizada con éxito y sin número de factura',
                            showConfirmButton: false,
                            timer: 1500
                        });
                    }
                } else {
                    Swal.fire({
                        icon: 'error',
                        title: 'Error en impresión',
                        text: (data.error && data.error.message) || 'Respuesta vacía',
                        showConfirmButton: true,
                    });
                }
            } else {
                Swal.fire({
                    icon: 'error',
                    title: 'Error en comunicación con la API: ' + response.status,
                    showConfirmButton: true,
                });
            }
        } catch (error) {
            this.modal_imprimiendo.close();
            console.error("Error en printViaApi:", error);
            Swal.fire({
                icon: 'error',
                title: 'Error al conectar con la API',
                text: error.message,
                showConfirmButton: true,
            });
        }
    },

    async read() {
        window.clearTimeout(this.timeout);
        // ... (read implementation kept to avoid large duplication but ensured presence)
        console.log("Leyendo", this.port.readable)
        while (this.port.readable) {
            console.log("Leyendo");
            try {
                while (true) {
                    const { value, done } = await this.reader.read();

                    if (done) {
                        console.log("Done");
                        break;
                    }

                    (value) && console.log(value);
                }
            } catch (error) {
                console.error(error);
            } finally {
                await Promise.all([
                    this.writer?.releaseLock(),
                    this.reader.releaseLock(),
                ]);
            }
        }

        this.printerCommands = [];
        this.reader.releaseLock();
        this.reader = false;
    },

    get order() {
        return this.props?.order || this.pos?.get_order?.() || this.pos?.currentOrder;
    },

    async doPrinting(mode) {
        console.log("[FISCAL] v196 - Iniciando doPrinting, validando códigos...");
        const payments = this.order.payment_ids || [];
        
        const missingCodes = payments.filter(p => {
            const pmId = p.payment_method_id?.id || p.payment_method_id;
            const pCode = DataHelper.getPaymentMethodCode(this.pos, pmId);
            
            console.log(`[FISCAL] v196 - Pago ID: ${p.id}, PM ID: ${pmId}, Código Detectado: ${pCode}`);
            
            return !pCode || pCode === "01"; // Si es el fallback '01', alertamos (podría ser intencional o error)
        });

        if (missingCodes.length > 0) {
            console.warn("Algunos métodos de pago no tienen código de impresora en el modelo, se usará '01' por defecto.");
        }
        if (this.order.impresa) {
            this.env.services.notification.add(_t("Documento impreso en máquina fiscal"), { type: "danger" });
            return;
        }
        this.printerCommands = [];
        switch (mode) {
            case "noFiscal":
                this.printNoFiscal();
                break;
            case "fiscal":
                this.read_s2 = true;
                this.printFiscal();
                break;
            case "notaCredito":
                this.read_s2 = true;
                const result = await this.printNotaCredito();
                if (!result) return;
                break;
        }

        if (this.pos.config.connection_type === "api") {
            await this.printViaApi();
        } else {
            await this.actionPrint();
        }
    },

    // Pachacutec: v95 - Apertura Total v16 (6 comandos: iR*/iS*/i00-i03)
    // Validado: i03 es el disparador mandatorio en muchos firmwares HKA.
    setHeader(payload) {
        const order = this.pos.get_order();
        const client = order?.get_partner?.() || order?.partner;
        
        // Pachacutec: v208 - Anulación Preventiva de Emergencia
        // Si la impresora quedó abierta por un error anterior, el comando 7 la libera.
        // Si ya está cerrada, la impresora simplemente devolverá un NAK/ACK inofensivo.
        this.printerCommands.push("7");

        // Pachacutec: v194 - Recuperación vía DataHelper (Blindaje de Prefijo)
        const vat = DataHelper.getFullVat(this.pos, client);
        
        const cleanName = cleanText(client?.name || "CLIENTE GENERAL").substring(0, 30);
        const cleanAddr = cleanText(client?.street || "SIN DIRECCION").substring(0, 30);
        const cleanPhone = cleanText(client?.phone || "No tiene").substring(0, 30);
        const cleanEmail = cleanText(client?.email || "No tiene").substring(0, 30);
        
        this.printerCommands.push(`iR*${vat}`);
        this.printerCommands.push(`iS*${cleanName}`);

        this.printerCommands.push(`i00Telefono:  ${cleanPhone}`);
        this.printerCommands.push(`i01Direccion: ${cleanAddr}`);
        this.printerCommands.push(`i02Email:     ${cleanEmail}`);
        this.printerCommands.push(`i03Ref:       ${cleanText(order.name || "").substring(0, 30)}`);
        
        console.warn("[FISCAL] v172 - Cabecera v16 Simplicity:", {vat, cleanName});
    },

    setTotal() {
        console.log("[FISCAL] v200 - setTotal Corregido (Sin comando 199)");
        
        // Comando 3 (Subtotal) -> Bloquea a Estado de Pago
        // Pachacutec: v217 - Paridad v16: Se ELIMINA el comando '3' (Subtotal)
        // En algunos firmwares, el subtotal bloquea el flujo de abonos parciales (CMD 2).

        // Lógica de Pagos Dinámicos (Odoo 18)
        const payments = this.order.payment_ids || [];
        const positivePayments = payments.filter(p => (p.amount || 0) > 0);

        if (positivePayments.length === 0) {
            console.warn("[FISCAL] v200 - No se hallaron pagos positivos, usando fallback 101");
            this.printerCommands.push("101");
        } else {
            positivePayments.forEach((payment, index) => {
                const isLast = (index === positivePayments.length - 1);
                
                const pmId = payment.payment_method_id?.id || payment.payment_method_id;
                const code = DataHelper.getPaymentMethodCode(this.pos, pmId);
                
                // Pachacutec: v218 - ARQUITECTURA DINÁMICA (Universal Compatibility)
                // Se hereda el selector de v16 para decidir el padding según el hardware:
                // - Flag 30: Padding 15 (Modelos NG / Alta Capacidad).
                // - Flag 00 / Default: Padding 10 (Modelos Estándar / Legacy).
                // Pachacutec: v230 - PRIORIDAD MODERNA (NG Default)
                // Usamos Padding 15 (17 dig totales) por defecto para modelos modernos.
                // El motor de reintento en 'write' bajará a 10 (12 dig) si es necesario.
                const flag_21 = this.pos.config.flag_21 || "30"; 
                const flag_pad = (flag_21 === "00") ? 10 : 15;
                
                if (isLast) {
                    // Pachacutec: v217 - Paridad v16: Comando 1 (Totalización) SIN MONTO.
                    // Indica a la impresora cerrar la factura con el saldo restante.
                    console.warn(`[FISCAL] v218 - Protocolo [Flag ${flag_21}]: Cierre Final (CMD 1 + Code):`, {code});
                    this.printerCommands.push("1" + code);
                } else {
                    // Pachacutec: v225 - Padding Maestro v16 (10/15 + 2 decimales siempre)
                    const rawAmount = Math.abs(payment.amount);
                    const integerPart = Math.floor(rawAmount);
                    const decimalPart = Math.round((rawAmount - integerPart) * 100);
                    const amountStr = String(integerPart).padStart(flag_pad, "0") + String(decimalPart).padStart(2, "0");
                    
                    console.log(`[FISCAL] v218 - Protocolo [Flag ${flag_21} - Pad ${flag_pad+2}]: Abono Parcial (CMD 2):`, { code, amountStr });
                    this.printerCommands.push("2" + code + amountStr);
                }
            });
        }

        // Pachacutec: v206 - Restauración controlada del comando 199 (Finalizar y Cortar)
        // Se envía al final para asegurar el paper-feed y corte en Bixolon/HKA-NG
        this.printerCommands.push("199");
        
        console.log("[FISCAL] v206 - Cierre Fiscal y Corte Finalizado.");
    },

    printFiscal() {
        this.setHeader();
        this.setLines("GF");
        this.setTotal();
    },

    setLines(char) {
        console.warn("[FISCAL] setLines - Inicio con char:", char);
        this.order.lines
            .forEach((line) => {
                // Pachacutec: v42 - Declaración de variables con ámbito correcto
                let tax_ids = [];
                let tax_records = [];

                try {
                    // Pachacutec: v41 - Resolución Ultra-Segura Odoo 18
                    const raw_taxes = line.tax_ids;
                    
                    if (raw_taxes) {
                        if (Array.isArray(raw_taxes)) {
                            tax_ids = raw_taxes.map(t => Number(typeof t === 'object' ? t.id : t));
                        } else if (raw_taxes.records) {
                            tax_ids = raw_taxes.records.map(r => Number(r.id));
                        } else if (typeof raw_taxes === 'object' && raw_taxes !== null) {
                            // Caso Proxy de record único o set
                            tax_ids = (raw_taxes.id) ? [Number(raw_taxes.id)] : [];
                        }
                    }

                    // Fallback a producto si tax_ids sigue vacío
                    if (tax_ids.length === 0 && line.product_id) {
                        const product = this.pos.models["product.product"]?.get(line.product_id.id || line.product_id);
                        const p_taxes = product?.taxes_id;
                        if (p_taxes) {
                            if (Array.isArray(p_taxes)) tax_ids = p_taxes.map(id => Number(id));
                            else if (p_taxes.records) tax_ids = p_taxes.records.map(r => Number(r.id));
                        }
                    }

                    // Limpieza e IDs únicos
                    tax_ids = [...new Set(tax_ids)].filter(id => id);
                    console.warn("[FISCAL] tax_ids normalizados (v42):", tax_ids);

                    // Resolver contra el modelo global de POS (DataStore en v18)
                    const tax_model = this.pos.models["account.tax"];
                    if (tax_model) {
                        // Pachacutec: v58 - Acceso Estricto a Modelo Reactivo Odoo 18
                        tax_records = tax_ids
                            .map(id => {
                                const rec = tax_model.get(id);
                                if (rec) {
                                    console.warn("[FISCAL] v58 - Impuesto Detectado:", id, " Amount:", rec.amount);
                                }
                                return rec;
                            })
                            .filter(t => t); 
                        
                        if (tax_records.length === 0) {
                            console.error("[FISCAL] v58 - FALLO CRÍTICO: No se hallaron impuestos para IDs:", tax_ids);
                            // Log de emergencia para depurar el DataStore
                            try {
                                const all_ids = tax_model.getAll().map(t => t.id);
                                console.warn("[FISCAL] v58 - IDs disponibles en account.tax:", all_ids.join(", "));
                            } catch(e) {}
                        }
                    } else {
                        console.error("[FISCAL] v58 - DataStore 'account.tax' NO EXISTE!");
                    }
                    
                } catch (e) {
                    console.error("[FISCAL] Error crítico en setLines v50:", e);
                }

                // Pachacutec: v41 - Determinación de Carácter Fiscal (Seguro Social)
                let tag = (char === "GC") ? "d0" : " "; // Default exento
                
                if (tax_records.length > 0) {
                    const first_tax = tax_records[0];
                    const type = first_tax.x_tipo_alicuota || first_tax.attr?.x_tipo_alicuota;
                    // v55 - Uso de amount como respaldo (IVA 16% es General)
                    const amount = first_tax.amount !== undefined ? first_tax.amount : (first_tax.attr?.amount || 0);

                    console.warn("[FISCAL] v55 - Analizando Tax:", {type, amount});

                    if (type === 'general' || amount === 16) tag = '!'; // v77: ! = 16% (General)
                    else if (type === 'reducido' || amount === 8 || amount === 12) tag = '"';
                    else if (type === 'adicional' || amount === 31) tag = '#';
                    else tag = ' '; // Espacio = Exento
                } 
                // Pachacutec: v56 - Failsafe: Si hay IDs pero no records, usar espacio (Exento) por seguridad
                else if (tax_ids.length > 0) {
                    console.warn("[FISCAL] v56 - Failsafe: IDs presentes pero records vacíos. Usando ' ' (Exento)");
                    tag = ' ';
                } else {
                    tag = ' '; // Exento
                }

                // Cálculo de precios y cantidades (v16 alignment)
                let unitPrice = line.get_unit_display_price ? line.get_unit_display_price() : (line.price_unit || 0);
                if (line.get_all_prices) {
                    const all_prices = line.get_all_prices();
                    unitPrice = all_prices.priceWithoutTaxBeforeDiscount / (line.qty || 1);
                }

                // Pachacutec: v157 - Restauración de Estructura Exacta v16 (Fuente de Verdad)
                // Basado en el skill hka_fiscal_expert: 16 Precio + 17 Cantidad + Pipes
                let price = String(Math.round((unitPrice || 0) * 100)).padStart(16, '0').slice(-16);
                let quantity = String(Math.round(Math.abs(line.qty || line.quantity || 0) * 1000)).padStart(17, '0').slice(-17);
                
                let command = tag + price + quantity;
                
                const code_clean = cleanText(line.product_id?.default_code || "");
                if (code_clean) {
                    command += `|${code_clean.substring(0, 10)}|`;
                } else {
                    // Pachacutec: v158 - Doble tubería para campo vacío (NG Standard)
                    command += `||`; 
                }
                
                command += cleanText(line.product_id?.display_name || line.product_name || "Producto").substring(0, 30);
                
                console.warn("[FISCAL] v157 - Línea Ensamblada (HKA-NG):", command);
                this.printerCommands.push(command);

                if (line.discount > 0) {
                    let disc = line.discount.toFixed(2).replace(".", ",").replace(",", "").padStart(4, "0");
                    this.printerCommands.push("p-" + disc);
                }

                if (line.customer_note) {
                    this.printerCommands.push((char === "GC" ? "A##" : "@##") + sanitize(line.customer_note) + "##");
                }
            });
        
        // Pachacutec: v74 - Guardia de Último Minuto para IGTF (Aseguramiento Fiscal)
        // Si el pedido tiene un monto de IGTF pero la línea física no aparece en 'lines'
        // (por latencia reactiva de Odoo 18), generamos el comando virtualmente.
        try {
            const igtf_monto = this.order.x_igtf_amount;
            const has_igtf_line = (this.order.lines || []).some(l => l && l.x_is_igtf_line);
            if (igtf_monto > 0.01 && !has_igtf_line) {
                console.warn("[FISCAL] v74 - LÍNEA IGTF NO HALLADA EN 'lines'. Generando comando virtual...");
                let price = String(Math.round(igtf_monto * 100)).padStart(16, '0').slice(-16);
                let quantity = String(1000).padStart(17, '0').slice(-17); // Cantidad 1.000 (3 decimales)
                let tag = ' '; // Tag Exento para IGTF percibido
                let virtual_cmd = tag + price + quantity + "||IGTF 3%";
                this.printerCommands.push(virtual_cmd);
                console.log("[FISCAL] v74 - Comando virtual IGTF añadido:", virtual_cmd);
            }
        } catch (e) {
            console.error("[FISCAL] Error en guardia IGTF v74:", e);
        }
    },

    printNoFiscal() {
        this.order.lines
            .forEach((line) => {
                const name = cleanText(line.product_id?.display_name || "");
                const code = line.product_id?.default_code || "";
                this.printerCommands.push(`80 ${name} [${code}]`);
                this.printerCommands.push(`80*x${line.qty} ${(line.get_price_with_tax()).toFixed(2).replace(".", ",")}`);
            });

        if (this.order.amount_return) {
            this.printerCommands.push("80*CAMBIO: " + (this.order.amount_return).toFixed(2).replace(".", ","));
        }
        this.printerCommands.push("81 TOTAL: " + (this.order.get_total_with_tax()).toFixed(2).replace(".", ","));
    },

    async printNotaCredito() {
        const { confirmed, payload } = await this.env.services.dialog.add(NotaCreditoPopUp);
        if (!confirmed) return false;
        this.setHeader(payload);
        this.setLines("GC");
        this.setTotal();
        return true;
    },

    async closePort() {
        if (this.port) {
            try {
                // Pachacutec: v178 - Liberación defensiva de streams antes de cerrar
                if (this.reader) {
                    try { 
                        await this.reader.cancel(); 
                        await this.reader.releaseLock();
                    } catch (e) {}
                    this.reader = false;
                }
                if (this.writer) {
                    try { await this.writer.releaseLock(); } catch (e) {}
                    this.writer = false;
                }
                await this.port.close();
                console.log("[FISCAL] Puerto cerrado exitosamente.");
            } catch (e) {
                console.warn("[FISCAL] Error al cerrar puerto:", e);
            } finally {
                this.port = false;
            }
        }
    },

    // Pachacutec: v139 - Stubs para compatibilidad de parche
    async checkFiscalStatus() {
        console.warn("[FISCAL] checkFiscalStatus no implementado en este firmware.");
        return true;
    },

    async fetchStatusDiagnosis() {
        console.warn("[FISCAL] fetchStatusDiagnosis no implementado en este firmware.");
        return [];
    }
};
