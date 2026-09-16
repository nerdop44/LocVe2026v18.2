# Agent Operations & Rules

## Reglas de Ejecución Operativa

1. **Regla de Oro:** Siempre leer y actualizar el archivo `trazabilidad.md` como fuente única de verdad del historial y de los cambios.
2. **Uso del Navegador (DOM):** El uso del subagente de navegador web es EXCLUSIVAMENTE para PRUEBAS FUNCIONALES y validación de las tareas, y SOLO debe utilizarse cuando el Ing. Nerdo lo autorice expresamente.
3. **Restricción del DOM:** Nunca utilizar el DOM o la interfaz gráfica para implementar cambios lógicos, crear configuraciones críticas que deben ir en código o modificar acciones del servidor. Toda solución escalable debe ser desarrollada a nivel de código fuente en los módulos `.py` y `.xml`.
4. **Compatibilidad Dual:** Cualquier cambio debe funcionar en CE Y EE. Si un cambio requiere un módulo EE específico, documentarlo en `COMPATIBILITY.md`.
5. **No romper:** Antes de modificar un archivo, verificar qué otros módulos lo heredan o dependen de él.

## Checklist Pre-Commit

Antes de cualquier cambio de código:
- [ ] ¿El cambio funciona en CE? (sin módulos EE)
- [ ] ¿El cambio funciona en EE? (con módulos EE)
- [ ] ¿Los `digits` son `(16, 4)` para campos de tasa?
- [ ] ¿La moneda es `"VES"` (no `"VEF"`) en TFHKA?
- [ ] ¿La hora es formato 12h `%I:%M:%S %p` en TFHKA?
- [ ] ¿Se actualizó `trazabilidad.md`?
