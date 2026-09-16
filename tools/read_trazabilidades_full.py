import os

trazabilidades = {
    "Devenalsa": "/home/nerdop/Laboratorio/Clientes Odoo/Por Cimas/Devenalsa/trazabilidad.md",
    "Innovo_UBA": "/home/nerdop/Laboratorio/Clientes Odoo/Por Cimas/Innovo/UBA/trazabilidad.md",
    "Innovo_Seed": "/home/nerdop/Laboratorio/Clientes Odoo/Por Cimas/Innovo/SeedTheSun/trazabilidad.md",
    "Innovo_Sefinca": "/home/nerdop/Laboratorio/Clientes Odoo/Por Cimas/Innovo/Sefinca/trazabilidad.md",
    "Krill": "/home/nerdop/Laboratorio/Clientes Odoo/Por Cimas/Krill/trazabilidad.md",
    "Pajarolandia": "/home/nerdop/Laboratorio/Clientes Odoo/Por Cimas/Pajarolandia/trazabilidad.md",
    "Pajarolandia_pre": "/home/nerdop/Laboratorio/Clientes Odoo/Por Cimas/Pajarolandia antes del 280526/trazabilidad.md"
}

output_path = "/home/nerdop/.gemini/antigravity/brain/9901ea7a-c9eb-422e-9a9b-4bf61f606adc/scratch/trazabilidades_full_extracted.txt"

with open(output_path, 'w', encoding='utf-8') as outfile:
    for label, path in trazabilidades.items():
        if not os.path.exists(path):
            outfile.write(f"\n\n==================================================\n")
            outfile.write(f"=== {label}: NO EXISTE ===\n")
            outfile.write(f"==================================================\n")
            continue
            
        outfile.write(f"\n\n==================================================\n")
        outfile.write(f"=== {label} ===\n")
        outfile.write(f"==================================================\n")
        
        with open(path, 'r', encoding='utf-8', errors='ignore') as infile:
            content = infile.read()
            outfile.write(content)

print(f"LECTURA COMPLETA DE TRAZABILIDADES REALIZADA. Guardada en: {output_path}")
