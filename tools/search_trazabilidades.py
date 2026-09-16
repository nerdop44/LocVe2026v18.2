import re

filepath = "/home/nerdop/.gemini/antigravity/brain/9901ea7a-c9eb-422e-9a9b-4bf61f606adc/scratch/trazabilidades_full_extracted.txt"
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')

# Palabras clave de cambios importantes
keywords = [
    r'tasa', r'round', r'redondeo', r'igtf', r'retencion', r'municipal', 
    r'libro', r'secuencia', r'correlativo', r'impresora', r'fiscal', 
    r'pos', r'bcv', r'trm', r'is_company_usd', r'voucher', r'exento'
]

pattern = re.compile('|'.join(keywords), re.IGNORECASE)

matches = []
for idx, line in enumerate(lines):
    if pattern.search(line):
        matches.append(idx)

# Agrupar coincidencias cercanas para no duplicar contexto
grouped_matches = []
current_group = []
for m in matches:
    if not current_group:
        current_group.append(m)
    elif m - current_group[-1] <= 5:
        current_group.append(m)
    else:
        grouped_matches.append(current_group)
        current_group = [m]
if current_group:
    grouped_matches.append(current_group)

# Escribir fragmentos con contexto de 3 líneas antes y después
output_path = "/home/nerdop/.gemini/antigravity/brain/9901ea7a-c9eb-422e-9a9b-4bf61f606adc/scratch/trazabilidades_context.txt"
with open(output_path, 'w', encoding='utf-8') as f:
    for idx, group in enumerate(grouped_matches):
        start = max(0, group[0] - 3)
        end = min(len(lines), group[-1] + 4)
        f.write(f"\n--- FRAGMENTO {idx+1} (Líneas {start+1}-{end}) ---\n")
        for i in range(start, end):
            # Marcar la línea que coincide
            prefix = ">>> " if i in group else "    "
            f.write(f"{prefix}[L{i+1}] {lines[i]}\n")

print(f"ANÁLISIS DE CONTEXTO COMPLETADO. Guardado en: {output_path}")
