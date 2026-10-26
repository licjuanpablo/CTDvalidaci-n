#!/usr/bin/env python3
"""Pasa cada expediente ficticio por el flujo clínico de prueba y guarda la respuesta cruda (ALCOA+: nada se pisa).
Uso: python3 correr_casos.py DEV|TEST [--etiqueta v1] [--solo CLIN-D01,...] [--sin-ia] [--debug] [--paralelo 3]"""
import argparse, csv, json, os, subprocess, time, datetime, glob
from concurrent.futures import ThreadPoolExecutor

AQUI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # raíz de clinica/
URL = "https://server.licjuanpablo.com.ar/webhook/validacion-ctd-clinica-4e9b2c"
ap = argparse.ArgumentParser()
ap.add_argument("particion", choices=["DEV", "TEST"])
ap.add_argument("--etiqueta", default="v1"); ap.add_argument("--solo", default="")
ap.add_argument("--sin-ia", action="store_true"); ap.add_argument("--debug", action="store_true")
ap.add_argument("--paralelo", type=int, default=1)
ap.add_argument("--corrida", default="", help="continuar una corrida existente (por tandas); no repite casos ya corridos")
ap.add_argument("--casos", default="casos", help="carpeta de casos (casos_devx = DEV ampliado, semilla 7777)")
a = ap.parse_args()

gt = {r["caso"]: r for r in csv.DictReader(open(os.path.join(AQUI, a.casos, "ground_truth.csv"), encoding="utf-8"))}
casos = sorted(c for c, r in gt.items() if r["particion"] == a.particion)
if a.solo:
    casos = [c for c in casos if c in a.solo.split(",")]
corrida = a.corrida or f"{'DEVX_' if a.casos != 'casos' else ''}{a.particion}_{a.etiqueta}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
out = os.path.join(AQUI, "corridas", corrida); os.makedirs(out, exist_ok=True)
if a.particion == "TEST" and a.casos == "casos":
    marca = os.path.join(AQUI, "corridas", "TEST_YA_CORRIDO.txt")
    previas = open(marca).read().split() if os.path.exists(marca) else []
    if previas and corrida not in previas:
        raise SystemExit("TEST ya fue corrido (" + ", ".join(previas) + "): no se corre otra vez")
    if corrida not in previas:
        with open(marca, "a") as fh:
            fh.write(f"{corrida}\n")
casos = [c for c in casos if not os.path.exists(os.path.join(out, c + ".json"))]

def correr(c):
    archivos = sorted(glob.glob(os.path.join(AQUI, f"{a.casos}/{a.particion}/{c}/*")))
    cmd = ["curl", "-s", "-m", "600", "-X", "POST", URL, "-F", "expediente="]
    if a.sin_ia: cmd += ["-F", "sin_ia=1"]
    if a.debug: cmd += ["-F", "debug=1"]
    for i, f in enumerate(archivos):
        cmd += ["-F", f"file{i}=@{f};filename={os.path.basename(f)}"]
    t0 = time.time()
    res = subprocess.run(cmd, capture_output=True, text=True)
    dt = round(time.time() - t0, 1)
    try:
        data = json.loads(res.stdout)
    except Exception:
        data = {"error": "respuesta no JSON", "raw": res.stdout[:2000]}
    data["_segundos"] = dt
    json.dump(data, open(os.path.join(out, c + ".json"), "w"), ensure_ascii=False, indent=1)
    return f"{c} {data.get('asignar_a', '')} {data.get('dictamen', data.get('error', data.get('message', data.get('version', ''))))} {dt}s"

with ThreadPoolExecutor(a.paralelo) as ex:
    for linea in ex.map(correr, casos):
        print(linea, flush=True)
print("CORRIDA", out)
