# Agent Operations & Rules — Krill Fiscal

## Reglas de Ejecución Operativa

1. **Regla de Oro:** Siempre leer y actualizar el archivo `trazabilidad.md` como fuente única de verdad del historial y de los cambios.
2. **Restricción de Entorno Odoo.sh:** Producción (`34200710`) es **ESTRICTAMENTE DELICADO Y CONGELADO**. Cualquier prueba, despliegue preliminar o actualización se realizará exclusivamente en el entorno de **PRUEBAS** (`38165808`).
3. **Restricción del Área de Trabajo:** Prohibido modificar archivos fuera del directorio de este proyecto (`/home/nerdop/Laboratorio/Clientes Odoo/Por Cimas/Krill/Krill Fiscal`) sin autorización previa del Ing. Nerdo.
4. **Uso del Navegador (DOM):** El uso del subagente de navegador web es EXCLUSIVAMENTE para PRUEBAS FUNCIONALES y validación de las tareas, y SOLO debe utilizarse cuando el Ing. Nerdo lo autorice expresamente.
5. **Restricción del DOM:** Nunca utilizar el DOM o la interfaz gráfica para implementar cambios lógicos o crear configuraciones críticas que deben ir en código. Toda solución escalable debe ser desarrollada a nivel de código fuente en los módulos `.py` y `.xml`.
6. **Compatibilidad Dual:** Cualquier cambio debe funcionar en CE Y EE. Si un cambio requiere un módulo EE específico, documentarlo en `COMPATIBILITY.md`.
7. **No romper:** Antes de modificar un archivo, verificar qué otros módulos lo heredan o dependen de él.

## Checklist Pre-Commit / Pre-Push (Prueba Odoo.sh)

Antes de cualquier cambio o despliegue a Prueba:
- [ ] ¿El cambio funciona en CE? (sin módulos EE)
- [ ] ¿El cambio funciona en EE? (con módulos EE)
- [ ] ¿Los `digits` son `(16, 4)` para campos de tasa?
- [ ] ¿La moneda es `"VES"` (no `"VEF"`) en TFHKA?
- [ ] ¿La hora es formato 12h `%I:%M:%S %p` en TFHKA?
- [ ] ¿Se verificó `discount == 100.0` para muestras gratuitas SENIAT 0071?
- [ ] ¿El destino de push es EXCLUSIVAMENTE el entorno de Pruebas (`38165808`)?
- [ ] ¿Se actualizó `trazabilidad.md`?
