
import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

class PosUomRepair(models.AbstractModel):
    _name = 'pos.uom.repair'
    _description = 'Reparación Estructural de Unidades de Medida para POS'

    @api.model
    def run_structural_repair(self):
        """
        Pachacutec: v18.0.1.0.88 - SANEAMIENTO ESTRUCTURAL DE BD (Migración v16 Fix)
        Realiza una limpieza profunda de las UoM para asegurar estabilidad en el POS.
        """
        _logger.info("[UOM Fix] Iniciando saneamiento estructural de base de datos...")
        
        # 1. Corregir Categoría de 'kg' si está mal (Común en migraciones)
        self._repair_uom_categories()
        
        # 2. Alinear Variantes con Templates (Eliminar discrepancias físicas en BD)
        self._align_variants_uom()
        
        _logger.info("[UOM Fix] Saneamiento estructural completado.")

    @api.model
    def _repair_uom_categories(self):
        # Buscamos la categoría estándar de Peso
        weight_category = self.env['uom.category'].search([
            '|', ('name', 'ilike', 'Peso'), ('name', 'ilike', 'Weight')
        ], limit=1)
        
        if not weight_category:
            _logger.warning("[UOM Fix] No se encontró una categoría de 'Peso'.")
            return

        # Buscamos la UoM 'kg'
        kg_uom = self.env['uom.uom'].search([
            '|', ('name', '=', 'kg'), ('name', 'ilike', 'kilogram')
        ], limit=1)
        
        if kg_uom and kg_uom.category_id.id != weight_category.id:
            _logger.warning("[UOM Fix] Corrigiendo categoría de UoM '%s': %s -> %s", 
                            kg_uom.name, kg_uom.category_id.name, weight_category.name)
            kg_uom.write({'category_id': weight_category.id})

    @api.model
    def _align_variants_uom(self):
        # Odoo 18: uom_id está en product_template por delegación.
        # Solo intentamos el saneamiento SQL si la columna física existe (residuo de v16).
        self.env.cr.execute("""
            SELECT count(*) FROM information_schema.columns 
            WHERE table_name = 'product_product' AND column_name = 'uom_id'
        """)
        column_exists = self.env.cr.fetchone()[0]
        
        if column_exists:
            _logger.info("[UOM Fix] Detectada columna física uom_id en product_product. Verificando discrepancias...")
            self.env.cr.execute("""
                SELECT p.id 
                FROM product_product p
                JOIN product_template t ON p.product_tmpl_id = t.id
                WHERE p.uom_id IS NOT NULL AND p.uom_id != t.uom_id
            """)
            mismatched_ids = [r[0] for r in self.env.cr.fetchall()]
            
            if mismatched_ids:
                products = self.env['product.product'].browse(mismatched_ids)
                for p in products:
                    p.write({
                        'uom_id': p.product_tmpl_id.uom_id.id,
                        'uom_po_id': p.product_tmpl_id.uom_id.id
                    })
        
        # Saneamiento estándar vía ORM (Seguro en v18)
        inconsistent_products = self.env['product.template'].search([]).filtered(
            lambda t: t.uom_id.category_id != t.uom_po_id.category_id
        )
        if inconsistent_products:
            for t in inconsistent_products:
                t.write({'uom_po_id': t.uom_id.id})
