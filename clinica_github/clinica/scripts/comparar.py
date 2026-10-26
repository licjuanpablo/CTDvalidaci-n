#!/usr/bin/env python3
"""Compara una corrida del flujo clínico contra la referencia (ground_truth.csv).
Positivo = expediente que DEBE objetarse. Métricas: sensibilidad (objetar), especificidad, exactitud del dictamen,
exactitud de la asignación Calidad/Clínica/Ambas, motivos de objeción esperados y observaciones esperadas.
Uso: python3 comparar.py corridas/<carpeta>"""
import csv, json, os, sys
from math import comb

AQUI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # raíz de clinica/

def ic95(x, n):  # Clopper-Pearson exacto
    if n == 0: return (float("nan"), float("nan"))
    def cdf(k, p): return sum(comb(n, i) * p**i * (1 - p)**(n - i) for i in range(k + 1))
    def bus(f, lo=0.0, hi=1.0):
        for _ in range(60):
            m = (lo + hi) / 2
            lo, hi = (m, hi) if f(m) else (lo, m)
        return (lo + hi) / 2
    lo = 0.0 if x == 0 else bus(lambda p: 1 - cdf(x - 1, p) < 0.025)
    hi = 1.0 if x == n else bus(lambda p: cdf(x, p) > 0.025)
    return lo, hi

def fmt(x, n):
    if n == 0: return "—"
    lo, hi = ic95(x, n)
    return f"{x}/{n} = {x/n:.0%} (IC95 {lo:.0%}–{hi:.0%})"

corr = sys.argv[1].rstrip("/")
CASOS = sys.argv[2] if len(sys.argv) > 2 else "casos"
gt = {r["caso"]: r for r in csv.DictReader(open(os.path.join(AQUI, CASOS, "ground_truth.csv"), encoding="utf-8"))}
filas = []
for f in sorted(os.listdir(corr)):
    if not f.endswith(".json") or not f.startswith("CLIN-"): continue
    c = f[:-5]; g = gt[c]; d = json.load(open(os.path.join(corr, f)))
    dic = {"Objetar": "OBJETAR", "Apto para evaluación": "APTO"}.get(d.get("dictamen"), "ERROR")
    cods_obj = sorted({o["codigo"] for o in d.get("objeciones", [])})
    cods_obs = sorted({o["codigo"] for o in d.get("observaciones", [])} | {o["codigo"] for o in d.get("informacion", [])})
    exp_obj = [x for x in g["objeciones_esperadas"].split(";") if x]
    exp_obs = [x for x in g["observaciones_esperadas"].split(";") if x]
    filas.append({
        "caso": c, "escenario": g["escenario"], "variante": g["variante"],
        "dictamen_esperado": g["dictamen_esperado"], "dictamen_sistema": dic, "ok_dictamen": dic == g["dictamen_esperado"],
        "asignacion_esperada": g["asignacion_esperada"], "asignacion_sistema": d.get("asignar_a", "ERROR"),
        "ok_asignacion": d.get("asignar_a") == g["asignacion_esperada"],
        "objeciones_esperadas": ";".join(exp_obj), "objeciones_sistema": ";".join(cods_obj),
        "ok_motivos": all(x in cods_obj for x in exp_obj) and (bool(exp_obj) or not cods_obj),
        "motivos_extra": ";".join(x for x in cods_obj if x not in exp_obj),
        "observaciones_esperadas": ";".join(exp_obs), "observaciones_sistema": ";".join(cods_obs),
        "ok_observaciones": all(x in cods_obs for x in exp_obs),
        "ia": d.get("extraccion_ia", {}).get("estado"), "ia_asignacion": d.get("extraccion_ia", {}).get("sugerencia_asignacion"),
        "detalle": d.get("DETALLE", d.get("error", d.get("message", ""))), "segundos": d.get("_segundos")})

tp = sum(f["dictamen_sistema"] == "OBJETAR" and f["dictamen_esperado"] == "OBJETAR" for f in filas)
fn = sum(f["dictamen_sistema"] != "OBJETAR" and f["dictamen_esperado"] == "OBJETAR" for f in filas)
tn = sum(f["dictamen_sistema"] == "APTO" and f["dictamen_esperado"] == "APTO" for f in filas)
fp = sum(f["dictamen_sistema"] != "APTO" and f["dictamen_esperado"] == "APTO" for f in filas)
n = len(filas)
L = [f"# Resultados {os.path.basename(corr)}", "", f"Casos: {n} (deben objetarse: {tp+fn}; aptos: {tn+fp})", "",
     "| Métrica | Valor |", "|---|---|",
     f"| Sensibilidad (objeta los que deben objetarse) | {fmt(tp, tp+fn)} |",
     f"| Especificidad (no objeta los aptos) | {fmt(tn, tn+fp)} |",
     f"| Exactitud del dictamen | {fmt(tp+tn, n)} |",
     f"| Exactitud de la asignación Calidad/Clínica/Ambas | {fmt(sum(f['ok_asignacion'] for f in filas), n)} |",
     f"| Motivo de objeción correcto (incluye todos los esperados, sin objeciones en aptos) | {fmt(sum(f['ok_motivos'] for f in filas), n)} |",
     f"| Observaciones/información esperadas presentes | {fmt(sum(f['ok_observaciones'] for f in filas if f['observaciones_esperadas']), sum(1 for f in filas if f['observaciones_esperadas']))} |"]
ia_ok = [f for f in filas if f["ia_asignacion"]]
if ia_ok:
    L.append(f"| Sugerencia de asignación de Gemini (no vinculante) | {fmt(sum(f['ia_asignacion'] == f['asignacion_esperada'] for f in ia_ok), len(ia_ok))} |")
L += ["", "IC 95 % exacto de Clopper-Pearson.", "", "## Matriz de asignación (filas = esperado, columnas = sistema)", "",
      "| | Calidad | Clínica | Ambas | otro |", "|---|---|---|---|---|"]
for e in ("Calidad", "Clínica", "Ambas"):
    fs = [f for f in filas if f["asignacion_esperada"] == e]
    L.append(f"| {e} | " + " | ".join(str(sum(f["asignacion_sistema"] == s for f in fs)) for s in ("Calidad", "Clínica", "Ambas")) +
             f" | {sum(f['asignacion_sistema'] not in ('Calidad','Clínica','Ambas') for f in fs)} |")
L += ["", "## Errores", ""]
for f in filas:
    errs = [k for k in ("ok_dictamen", "ok_asignacion", "ok_motivos", "ok_observaciones") if not f[k]]
    if errs:
        L.append(f"- {f['caso']} ({f['escenario']}{' ' + f['variante'] if f['variante'] else ''}): {', '.join(e[3:] for e in errs)} — "
                 f"esperado {f['dictamen_esperado']}/{f['asignacion_esperada']}/[{f['objeciones_esperadas']}]/[{f['observaciones_esperadas']}]; "
                 f"sistema {f['dictamen_sistema']}/{f['asignacion_sistema']}/[{f['objeciones_sistema']}]/[{f['observaciones_sistema']}]. {f['detalle'][:400]}")
open(os.path.join(corr, "resultados.md"), "w").write("\n".join(L))
with open(os.path.join(corr, "detalle.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(filas[0].keys())); w.writeheader(); w.writerows(filas)
print("\n".join(L))
