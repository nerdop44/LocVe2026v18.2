# Project Context — Krill Fiscal (LocVe v18.2 Unificado)

## Proyecto y Entorno
- **Nombre:** LocVe Unificado (CE + EE) — Localización Venezolana Odoo v18 para Krill Energy.
- **Cliente:** Krill Energy (`Krill Fiscal`).
- **Directorio Local:** `/home/nerdop/Laboratorio/Clientes Odoo/Por Cimas/Krill/Krill Fiscal`
- **Proyecto Padre:** `/home/nerdop/Laboratorio/Clientes Odoo/Por Cimas/Krill`
- **Repositorio Oficial Git:** `git@github.com:nerdop44/LocVe2026v18.2.git` (rama `main`)

## Entorno de Despliegue en Odoo.sh
- **Prueba / Staging (ACTIVO):** `ssh 38165808@krillenergy-prueba-38165808.dev.odoo.com`
- **Producción (BLOQUEADO / DELICADO):** `ssh 34200710@krillenergy.odoo.com` (Únicamente previa autorización explícita del Ing. Nerdo).

## Framework y Arquitectura Técnico-Fiscal
- **Framework:** Odoo 18.0 (Community **Y** Enterprise).
- **Control de Versiones:** Git.
- **Sistema Multimoneda:** Odoo configurado para manejar escenarios duales en Venezuela (Base USD con Tasa BCV dinámica). Las soluciones deben ser agnósticas de la moneda base para evitar errores de tipo de cambio.

## Reglas de Arquitectura y Negocio
1. **Dual Compatibility Obligatoria:** Todo código debe funcionar en CE **Y** EE. No hay excepciones.
2. **Soluciones Escalables (Código sobre Interfaz):** Cualquier modificación en la lógica de negocio debe hacerse a nivel de código (modelos, vistas XML, actions), NUNCA modificando mediante la interfaz de Odoo.
3. **Cero Parcheo Invasivo:** No modificar el core de Odoo. Las funcionalidades deben extenderse estrictamente mediante la herencia del ORM (`_inherit`).
4. **Manejo Nativo:** Priorizar el uso de los métodos nativos de Odoo (por ejemplo, `reconcile()` de las `account.move.line`) para resolver operaciones contables.
5. **Cumplimiento SENIAT (Providencia 0071):** Las modificaciones contables y fiscales deben cumplir de manera estricta con las providencias vigentes de Venezuela. Prohibidas líneas con `price_unit <= 0.0` salvo cuando se indique `discount == 100.0` (muestras / bonificaciones a título gratuito).
6. **Precisión Decimal:** Campos Float de tasa de cambio: siempre `digits=(16, 4)` y `round(x, 4)`.
7. **Moneda TFHKA (Imprenta Digital):** Siempre `"VES"` (nunca `"VEF"`). Hora: siempre formato 12h `%I:%M:%S %p` (minúsculas). Usar parámetro `_retry=False` en renovaciones de token para evitar recursión 401.
