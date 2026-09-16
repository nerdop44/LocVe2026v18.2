import os
import subprocess

repos = [
    # Devenalsa
    ("/home/nerdop/Laboratorio/Clientes Odoo/Por Cimas/Devenalsa", "Devenalsa (Principal)"),
    ("/home/nerdop/Laboratorio/Clientes Odoo/Por Cimas/Devenalsa/lov18resp1", "Devenalsa (Submódulo)"),
    # Innovo UBA
    ("/home/nerdop/Laboratorio/Clientes Odoo/Por Cimas/Innovo/UBA", "Innovo UBA (Principal)"),
    ("/home/nerdop/Laboratorio/Clientes Odoo/Por Cimas/Innovo/UBA/lov18resp1", "Innovo UBA (Submódulo)"),
    # Innovo SeedTheSun
    ("/home/nerdop/Laboratorio/Clientes Odoo/Por Cimas/Innovo/SeedTheSun", "Innovo SeedTheSun (Principal)"),
    ("/home/nerdop/Laboratorio/Clientes Odoo/Por Cimas/Innovo/SeedTheSun/lov18resp1", "Innovo SeedTheSun (Submódulo)"),
    # Innovo Sefinca
    ("/home/nerdop/Laboratorio/Clientes Odoo/Por Cimas/Innovo/Sefinca", "Innovo Sefinca (Principal)"),
    ("/home/nerdop/Laboratorio/Clientes Odoo/Por Cimas/Innovo/Sefinca/lov18resp1", "Innovo Sefinca (Submódulo)"),
    # Krill
    ("/home/nerdop/Laboratorio/Clientes Odoo/Por Cimas/Krill/Fase I/lov18resp1", "Krill (Localización - Fase I)"),
    ("/home/nerdop/Laboratorio/Clientes Odoo/Por Cimas/Krill/Fase II/Custom_Krill", "Krill (Custom - Fase II)"),
    # Pajarolandia
    ("/home/nerdop/Laboratorio/Clientes Odoo/Por Cimas/Pajarolandia", "Pajarolandia (Principal)"),
]

output_path = "/home/nerdop/.gemini/antigravity/brain/9901ea7a-c9eb-422e-9a9b-4bf61f606adc/scratch/git_commits_report.txt"

with open(output_path, 'w', encoding='utf-8') as f:
    f.write("==================================================\n")
    f.write("INFORME DETALLADO DE COMMITS (MAYO - JUNIO - JULIO 2026)\n")
    f.write("==================================================\n\n")
    
    for path, label in repos:
        if not os.path.exists(path):
            f.write(f"=== {label} ===\n")
            f.write(f"Ruta no existe: {path}\n\n")
            continue
            
        if not os.path.exists(os.path.join(path, ".git")):
            # Puede ser que no sea repo git directo o requiera buscar en carpetas
            f.write(f"=== {label} ===\n")
            f.write(f"No es un repositorio git: {path}\n\n")
            continue
            
        f.write(f"=== {label} ===\n")
        f.write(f"Ruta: {path}\n")
        
        # Ejecutar git log desde el 2026-05-01
        try:
            cmd = [
                "git", "log", 
                "--since=2026-05-01", 
                "--until=2026-07-25",
                "--pretty=format:COMMIT: %h | FECHA: %cd | AUTOR: %an%nMENSAJE: %s%n%b%n--------------------------------------------------"
            ]
            result = subprocess.run(cmd, cwd=path, capture_output=True, text=True, check=True)
            if result.stdout.strip():
                f.write(result.stdout.strip() + "\n\n")
            else:
                f.write("Sin commits en este rango de fechas.\n\n")
        except Exception as e:
            f.write(f"Error al ejecutar git log: {e}\n\n")

print(f"ANÁLISIS DE COMMITS COMPLETADO. Guardado en: {output_path}")
