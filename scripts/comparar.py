#!/usr/bin/env python3
"""Compara una corrida contra la referencia. Positivo = expediente que DEBE objetarse.
Uso: python3 comparar.py corridas/<carpeta>"""
import csv, json, os, re, sys, unicodedata
from math import comb

def norm(s):
    s = unicodedata.normalize("NFD", (s or "").lower())
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s#./-]", " ", "".join(ch for ch in s if unicodedata.category(ch) != "Mn"))).strip()

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

def campo_ia(txt, nombre):
    m = re.search(rf"{nombre}\s*:\**\s*([^\n]+)", txt or "", re.I)
    return m.group(1).strip().strip("*").strip() if m else ""

def veredicto_ia(txt):
    t = (txt or "").upper()
    m = re.search(r"PASO 4.*", t, re.S)
    seg = m.group(0) if m else t
    if "OBJETAR" in seg: return "OBJETAR"
    if "VALIDAR" in seg: return "VALIDAR"
    return "SIN RESPUESTA"

corr = sys.argv[1].rstrip("/")
gt = {r["caso"]: r for r in csv.DictReader(open("casos/ground_truth.csv", encoding="utf-8"))}
filas = []
for f in sorted(os.listdir(corr)):
    if not f.endswith(".json"): continue
    c = f[:-5]; g = gt[c]; d = json.load(open(os.path.join(corr, f)))
    reglas = {"OBJECION": "OBJETAR", "VALIDACION": "VALIDAR"}.get(d.get("resultado"), "ERROR")
    ia = d.get("respuestaIA", "")
    fila = {"caso": c, "escenario": g["escenario"], "esperado": g["veredicto_esperado"],
            "sistema_reglas": reglas, "ok_reglas": reglas == g["veredicto_esperado"],
            "ia_sugiere": veredicto_ia(ia), "ok_ia": veredicto_ia(ia) == g["veredicto_esperado"],
            "detalle_sistema": d.get("DETALLE", d.get("error", "")),
            "segundos": d.get("_segundos")}
    for campo, col in (("EXPEDIENTE", "expediente_esperado"), ("PRODUCTO", "producto_esperado"),
                       ("EMPRESA", "empresa_esperada"), ("IFA", "ifa_esperado")):
        val = campo_ia(ia, campo)
        fila["ia_" + campo.lower()] = val
        fila["ok_" + campo.lower()] = norm(val) == norm(g[col])
    filas.append(fila)

def metricas(clave):
    tp = sum(f[clave] == "OBJETAR" and f["esperado"] == "OBJETAR" for f in filas)
    fn = sum(f[clave] != "OBJETAR" and f["esperado"] == "OBJETAR" for f in filas)
    tn = sum(f[clave] == "VALIDAR" and f["esperado"] == "VALIDAR" for f in filas)
    fp = sum(f[clave] != "VALIDAR" and f["esperado"] == "VALIDAR" for f in filas)
    return tp, fn, tn, fp

L = [f"# Resultados {os.path.basename(corr)}", "", f"Casos: {len(filas)}", ""]
L += ["| Componente | Sensibilidad (detecta los que deben objetarse) | Especificidad (no objeta los correctos) | Exactitud |", "|---|---|---|---|"]
for nombre, clave in (("Veredicto final (reglas)", "sistema_reglas"), ("Sugerencia del modelo (Gemini)", "ia_sugiere")):
    tp, fn, tn, fp = metricas(clave)
    s, e = ic95(tp, tp + fn), ic95(tn, tn + fp)
    L.append(f"| {nombre} | {tp}/{tp+fn} ({s[0]:.0%}–{s[1]:.0%}) | {tn}/{tn+fp} ({e[0]:.0%}–{e[1]:.0%}) | {tp+tn}/{len(filas)} |")
L += ["", "IC 95 % exacto de Clopper-Pearson.", "", "| Campo extraído por el modelo | Aciertos |", "|---|---|"]
for k in ("expediente", "producto", "empresa", "ifa"):
    L.append(f"| {k} | {sum(f['ok_'+k] for f in filas)}/{len(filas)} |")
L += ["", "## Errores del veredicto final", ""]
for f in filas:
    if not f["ok_reglas"]:
        L.append(f"- {f['caso']} ({f['escenario']}): esperado {f['esperado']}, sistema {f['sistema_reglas']}. {f['detalle_sistema']}")
L += ["", "## Errores de extracción", ""]
for f in filas:
    for k, col in (("expediente", "expediente_esperado"), ("producto", "producto_esperado"), ("empresa", "empresa_esperada"), ("ifa", "ifa_esperado")):
        if not f["ok_" + k]:
            L.append(f"- {f['caso']} {k}: esperado «{gt[f['caso']][col]}», modelo «{f['ia_'+k]}»")
open(os.path.join(corr, "resultados.md"), "w").write("\n".join(L))
with open(os.path.join(corr, "detalle.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(filas[0].keys())); w.writeheader(); w.writerows(filas)
print("\n".join(L))
