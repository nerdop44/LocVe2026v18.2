# 🏆 Hito de Éxito: Base Fiscal Odoo 18 (HKA-NG) 
**Fecha: 01/04/2026**
**Versión Estable: 18.0.1.7.7**

Este archivo certifica que se ha alcanzado la estabilidad total en la impresión fiscal para el modelo HKA-NG en Odoo 18, logrando paridad funcional con la v16.

### 📜 Reglas de Oro de Estabilidad
1. **Paridad v16**: El motor de comunicación debe ser síncrono y esperar ACK (6) por cada comando.
2. **RIF Blindado**: Todo RIF numérico debe ser precedido por 'V' para evitar NAK (21).
3. **Sin Metadatos**: No usar comandos `80*` dentro de facturas fiscales (causan NAK).
4. **Secuencia NG**: El comando `i03` es el disparador de cabecera y el `199` es el cierre mandatorio.
5. **Cierre de Puerto**: El puerto DEBE cerrarse al finalizar `actionPrint` para liberar el hardware.
6. **LRC Íntegro**: El cálculo del LRC no debe incluir el STX (2).

### 🚀 Log de Éxito Confirmado
- Handshake inicial OK.
- Transmisión de ítems OK.
- Cierre fiscal 199 OK.
- Lectura de S1 y extracción de número fiscal OK.

*Este respaldo sirve como punto de restauración ante cualquier regresión futura.*
