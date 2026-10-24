#!/usr/bin/env python3
"""Pasa cada expediente ficticio por el flujo de prueba y guarda la respuesta cruda (ALCOA+: nada se pisa).
Uso: python3 correr_casos.py DEV|TEST [--etiqueta v1] [--solo CASO-001,...]"""
import argparse, csv, json, os, subprocess, time, datetime, glob

URL = "<URL_DEL_WEBHOOK>"
ap = argparse.ArgumentParser()
ap.add_argument("particion", choices=["DEV", "TEST"])
ap.add_argument("--etiqueta", default="v1")
ap.add_argument("--solo", default="")
a = ap.parse_args()

gt = {r["caso"]: r for r in csv.DictReader(open("casos/ground_truth.csv", encoding="utf-8"))}
casos = sorted(c for c, r in gt.items() if r["particion"] == a.particion)
if a.solo:
    casos = [c for c in casos if c in a.solo.split(",")]
corrida = f"{a.particion}_{a.etiqueta}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
out = os.path.join("corridas", corrida); os.makedirs(out)
if a.particion == "TEST":
    marca = "corridas/TEST_YA_CORRIDO.txt"
    with open(marca, "a") as fh:
        fh.write(f"{corrida}\n")

for c in casos:
    archivos = sorted(glob.glob(f"casos/{a.particion}/{c}/*"))
    cmd = ["curl", "-s", "-m", "300", "-X", "POST", URL, "-F", "expediente="]
    for i, f in enumerate(archivos):
        cmd += ["-F", f"file{i}=@{f}"]
    t0 = time.time()
    res = subprocess.run(cmd, capture_output=True, text=True)
    dt = round(time.time() - t0, 1)
    try:
        data = json.loads(res.stdout)
    except Exception:
        data = {"error": "respuesta no JSON", "raw": res.stdout[:2000]}
    data["_segundos"] = dt
    json.dump(data, open(os.path.join(out, c + ".json"), "w"), ensure_ascii=False, indent=1)
    print(c, data.get("resultado", data.get("error", data.get("message"))), f"{dt}s", flush=True)
print("CORRIDA", out)
