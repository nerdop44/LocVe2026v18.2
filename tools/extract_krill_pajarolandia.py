import re

filepath = "/home/nerdop/.gemini/antigravity/brain/9901ea7a-c9eb-422e-9a9b-4bf61f606adc/scratch/trazabilidades_full_extracted.txt"
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')

# Extraer el rango de Krill (líneas 751 a 2780)
# Extraer el rango de Pajarolandia (líneas 2781 a 3880)

def extract_section_summary(start_line, end_line, output_name):
    section_lines = lines[start_line - 1:end_line]
    output_lines = []
    
    # Buscamos títulos de sesiones, objetivos, logros y cambios
    capture = False
    for i, line in enumerate(section_lines):
        line_num = start_line + i
        if line.startswith("## Sesión:") or line.startswith("### ") or line.startswith("## ") or "Objetivo" in line or "Logros" in line:
            output_lines.append(f"[L{line_num}] {line}")
            capture = True
        elif capture and (line.startswith("- [") or line.startswith("  - [") or line.startswith("- ") or line.startswith("  - ") or line.startswith("1. ") or line.startswith("2. ") or line.startswith("3. ") or line.strip() == ""):
            # Capturamos viñetas de cambios
            if line.strip():
                output_lines.append(f"  [L{line_num}] {line}")
        else:
            capture = False
            
    with open(f"/home/nerdop/.gemini/antigravity/brain/9901ea7a-c9eb-422e-9a9b-4bf61f606adc/scratch/{output_name}.txt", 'w', encoding='utf-8') as out_f:
        out_f.write('\n'.join(output_lines))

extract_section_summary(750, 2780, "krill_summary")
extract_section_summary(2781, 3880, "pajarolandia_summary")
print("EXTRACCIÓN DE RESÚMENES COMPLETADA.")
