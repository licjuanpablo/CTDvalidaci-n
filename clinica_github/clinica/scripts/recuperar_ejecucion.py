#!/usr/bin/env python3
"""Recupera la salida de una ejecución del flujo cuya respuesta HTTP se perdió (corte del cliente), sin volver a correr el caso.
Identifica el caso por el conjunto exacto de nombres de archivo. Uso: python3 recuperar_ejecucion.py <corrida> <particion> <id_ejecucion>..."""
import json, subprocess, os, sys
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Requiere acceso a la API de n8n (header X-N8N-API-KEY); no se incluye ninguna clave.
B = "https://server.licjuanpablo.com.ar/api/v1"
corr, part, ids = sys.argv[1], sys.argv[2], sys.argv[3:]
casos = {c: sorted(os.listdir(f"casos/{part}/{c}")) for c in os.listdir(f"casos/{part}")}
for i in ids:
    d = json.loads(subprocess.run(["curl", "-s", f"{B}/executions/{i}?includeData=true"], capture_output=True, text=True).stdout)
    if d.get("status") != "success": print(i, "estado", d.get("status")); continue
    rd = d["data"]["resultData"]["runData"]
    files = sorted(x["fileName"] for x in rd["Obtener todos los textos"][0]["data"]["main"][0][0]["json"]["data"])
    c = next((c for c, fs in casos.items() if fs == files), None)
    out = rd["Reglas clínicas + ALCOA timestamp"][0]["data"]["main"][0][0]["json"]
    out["_segundos"] = None; out["_recuperado_de_ejecucion_n8n"] = i
    p = f"corridas/{corr}/{c}.json"
    print(i, c, out["asignar_a"], out["dictamen"], "ya existe" if os.path.exists(p) else "guardado")
    if c and not os.path.exists(p): json.dump(out, open(p, "w"), ensure_ascii=False, indent=1)
