#!/usr/bin/env python3
"""
Generador de expedientes FICTICIOS para validar la versión CLÍNICA del validador formal de trámites CTD
(variaciones post-registro de biológicos, concepto 2302: rótulos, prospectos e información para el paciente).

Todo es inventado: productos, IFA, laboratorios, elaboradores, números de certificado y textos.
Los patrones (tipos documentales, marcadores, formatos de tabla de modificaciones, sello IF del aprobado,
control de cambios con texto tachado conservado o solo resaltado) se calcaron del análisis de expedientes reales
anonimizados (estructura_documental.md), sin copiar texto real ni nombres de personas.

La referencia (ground_truth.csv) se fija ANTES de correr el sistema y se sella con sha256 en manifest.json.
Semilla fija -> reproducible. DEV para ajustar; TEST se corre una sola vez con la versión congelada.

Uso: python3 generar_casos_clinicos.py [--seed 2510] [--out casos]
"""
import argparse, csv, hashlib, json, os, random, re, shutil
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm

# ───────────────────────── catálogos ficticios ─────────────────────────
LABS = [("Biofarma Austral S.A.", "Av. Belgrano 845, CABA"),
        ("Inmunogen Pampa S.A.", "Ruta 8 km 61, Pilar, Buenos Aires"),
        ("Bioterapias del Plata S.R.L.", "Calle 50 N° 1120, La Plata"),
        ("Andes Biologics S.A.", "Av. San Martín 2300, Mendoza"),
        ("Proteica Rioplatense S.A.", "Av. Mitre 3400, Avellaneda"),
        ("Celltech Litoral S.R.L.", "Bv. Oroño 1550, Rosario")]
ELABS = ["Nordwerk Biologika GmbH, Alemania", "Lacustre Biopharma S.p.A., Italia", "Fiordo Biotech AS, Noruega",
         "Celtica Bioprocess Ltd., Irlanda", "Helvetia Zellkultur AG, Suiza", "Biomanufactura Iberia S.L., España"]
PRODS = [
    dict(nombre="ZENTAVIR", ifa="velorizumab", conc="100 mg/4 ml", forma="Concentrado para solución para infusión",
         via="Infusión intravenosa", envase="vial de 4 ml", unidad="vial de 4 ml", q="100 mg", clase="anticuerpo monoclonal humanizado IgG4",
         diana="el receptor de muerte celular programada 1 (PD-1)", indic="melanoma irresecable o metastásico",
         indic2="carcinoma urotelial localmente avanzado o metastásico", dosis="240 mg cada 2 semanas", dosis2="480 mg cada 4 semanas"),
    dict(nombre="NEXOLIMAB", ifa="tralivumab", conc="150 mg/1 ml", forma="Solución inyectable",
         via="Subcutánea", envase="jeringa prellenada de 1 ml", unidad="jeringa prellenada de 1 ml", q="150 mg", clase="anticuerpo monoclonal humano IgG1",
         diana="la interleuquina 13", indic="dermatitis atópica moderada a grave en adultos",
         indic2="dermatitis atópica moderada a grave en adolescentes de 12 a 17 años", dosis="300 mg cada 2 semanas", dosis2="300 mg cada 4 semanas"),
    dict(nombre="ARQUEVIA", ifa="denoquimab", conc="60 mg/1 ml", forma="Solución inyectable en lapicera prellenada",
         via="Subcutánea", envase="lapicera prellenada de 1 ml", unidad="lapicera prellenada de 1 ml", q="60 mg", clase="anticuerpo monoclonal humano IgG2",
         diana="el ligando del receptor activador del factor nuclear kappa B", indic="osteoporosis posmenopáusica con alto riesgo de fractura",
         indic2="pérdida ósea asociada al tratamiento hormonal en varones", dosis="60 mg cada 6 meses", dosis2="60 mg cada 6 meses con suplemento de calcio"),
    dict(nombre="ONCOTRIM", ifa="zalutuximab", conc="420 mg/14 ml", forma="Concentrado para solución para infusión",
         via="Infusión intravenosa", envase="vial de 14 ml", unidad="vial de 14 ml", q="420 mg", clase="anticuerpo monoclonal quimérico IgG1",
         diana="el receptor del factor de crecimiento epidérmico", indic="cáncer colorrectal metastásico con gen RAS no mutado",
         indic2="carcinoma de células escamosas de cabeza y cuello recurrente", dosis="6 mg/kg cada 2 semanas", dosis2="8 mg/kg cada 3 semanas"),
    dict(nombre="RUXALIM", ifa="ruxalimab", conc="200 mg/8 ml", forma="Concentrado para solución para infusión",
         via="Infusión intravenosa", envase="vial de 8 ml", unidad="vial de 8 ml", q="200 mg", clase="anticuerpo monoclonal humanizado IgG1",
         diana="el ligando 1 de muerte programada (PD-L1)", indic="cáncer de pulmón de células no pequeñas avanzado",
         indic2="carcinoma hepatocelular irresecable en combinación", dosis="1200 mg cada 3 semanas", dosis2="1680 mg cada 4 semanas"),
    dict(nombre="GLUFENTA", ifa="insulina fentalog", conc="100 UI/1 ml", forma="Solución inyectable",
         via="Subcutánea", envase="cartucho de 3 ml", unidad="cartucho de 3 ml", q="300 UI", clase="análogo de insulina humana de acción prolongada obtenido por ADN recombinante",
         diana="el receptor de insulina", indic="diabetes mellitus en adultos",
         indic2="diabetes mellitus en niños a partir de 2 años", dosis="una vez al día, a la misma hora", dosis2="una vez al día con titulación semanal"),
    dict(nombre="FILOPEG", ifa="pegrafiltrim", conc="6 mg/0,6 ml", forma="Solución inyectable en jeringa prellenada",
         via="Subcutánea", envase="jeringa prellenada de 0,6 ml", unidad="jeringa prellenada de 0,6 ml", q="6 mg", clase="factor estimulante de colonias de granulocitos pegilado",
         diana="el receptor del factor estimulante de colonias de granulocitos", indic="reducción de la duración de la neutropenia por quimioterapia",
         indic2="movilización de progenitores hematopoyéticos en donantes sanos", dosis="6 mg una vez por ciclo", dosis2="6 mg una vez por ciclo, 24 horas después de la quimioterapia"),
    dict(nombre="HEMOVANT", ifa="octofactor beta", conc="1000 UI/4 ml", forma="Polvo liofilizado y solvente para solución inyectable",
         via="Intravenosa", envase="vial de polvo y jeringa de solvente de 4 ml", unidad="vial", q="1000 UI", clase="factor VIII de coagulación recombinante",
         diana="el factor IX activado en la cascada de coagulación", indic="profilaxis y tratamiento de hemorragias en hemofilia A",
         indic2="profilaxis quirúrgica en pacientes con hemofilia A", dosis="20 a 40 UI/kg cada 2 a 3 días", dosis2="50 UI/kg una vez por semana"),
]
OTROS_NOMBRES = ["VELTRANIX", "CORVALEX", "MIRENZA", "TOLDAVIR", "PRAXELUM", "SOLIDREX"]
EXCIPIENTES = [("Histidina", "3,1 mg"), ("Sacarosa", "82 mg"), ("Polisorbato 80", "0,2 mg"), ("Cloruro de sodio", "5,8 mg"),
               ("Manitol", "40 mg"), ("Ácido acético glacial", "0,6 mg"), ("Glicina", "7,5 mg"), ("Metionina", "1,5 mg")]
EVENTOS = [("neumonitis", "neumonitis"), ("miocarditis", "miocarditis"), ("hepatitis inmunomediada", "hepatitis"),
           ("síndrome de liberación de citoquinas", "síndrome de liberación de citoquinas"), ("reacciones cutáneas graves", "reacciones cutáneas graves"),
           ("colitis", "colitis"), ("uveítis", "uveítis"), ("pancreatitis", "pancreatitis")]
RAM_NUEVAS = ["prurito", "alopecia", "artralgia", "hipotiroidismo", "fatiga", "erupción maculopapular", "mialgia", "conjuntivitis"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

# Encabezados canónicos de cada texto (prospecto 5904/96, información para el paciente, rótulo)
H_PROSP = {"COMPOSICION": "FÓRMULA", "ACCION": "ACCIÓN TERAPÉUTICA", "INDICACIONES": "INDICACIONES",
           "PROPIEDADES": "CARACTERÍSTICAS FARMACOLÓGICAS / PROPIEDADES", "POSOLOGIA": "POSOLOGÍA Y FORMA DE ADMINISTRACIÓN",
           "CONTRAINDICACIONES": "CONTRAINDICACIONES", "ADVERTENCIAS": "ADVERTENCIAS Y PRECAUCIONES", "INTERACCIONES": "INTERACCIONES",
           "POBLACIONES": "EMBARAZO Y LACTANCIA", "RAM": "REACCIONES ADVERSAS", "SOBREDOSIS": "SOBREDOSIFICACIÓN",
           "PRESENTACION": "PRESENTACIÓN", "CONSERVACION": "CONSERVACIÓN", "ELABORADOR": "ELABORADO POR"}
H_IP = {"INDICACIONES": "1. ¿Qué es {n} y para qué se utiliza?", "ADVERTENCIAS": "2. ¿Qué necesita saber antes de usar {n}?",
        "POSOLOGIA": "3. ¿Cómo usar {n}?", "RAM": "4. Posibles efectos adversos", "CONSERVACION": "5. Conservación de {n}",
        "PRESENTACION": "6. Contenido del envase e información adicional"}
H_ROT = {"COMPOSICION": "COMPOSICIÓN", "POSOLOGIA": "POSOLOGÍA", "CONSERVACION": "CONSERVACIÓN", "PRESENTACION": "CONTENIDO",
         "ELABORADOR": "ELABORADO POR"}
NOMBRE_SEC = {"INDICACIONES": "Indicaciones", "PROPIEDADES": "Propiedades farmacológicas", "POSOLOGIA": "Posología y forma de administración",
              "CONTRAINDICACIONES": "Contraindicaciones", "ADVERTENCIAS": "Advertencias y precauciones", "INTERACCIONES": "Interacciones",
              "POBLACIONES": "Embarazo y lactancia", "RAM": "Reacciones adversas", "SOBREDOSIS": "Sobredosificación",
              "COMPOSICION": "Fórmula / composición", "CONSERVACION": "Conservación y período de vida útil", "PRESENTACION": "Presentación",
              "ELABORADOR": "Elaborador"}
NOMBRE_SEC_IP = {"INDICACIONES": "¿Qué es y para qué se utiliza?", "ADVERTENCIAS": "Qué necesita saber antes de usar",
                 "POSOLOGIA": "Cómo usar", "RAM": "Posibles efectos adversos", "CONSERVACION": "Conservación",
                 "PRESENTACION": "Contenido del envase", "COMPOSICION": "Composición", "ELABORADOR": "Elaborador"}
NOMBRE_DOC = {"prospecto": "Prospecto (información para el profesional)", "ip": "Información para el paciente", "rotulo": "Rótulos"}


# ───────────────────────── modelo de textos ─────────────────────────
def base_textos(p, d):
    """Devuelve dict doc -> {'enc': [líneas], 'secs': [(clave, [oraciones])], 'pie': [líneas]} del texto APROBADO."""
    n, ifa = p["nombre"], p["ifa"]
    comp = [f"Cada {p['unidad']} contiene:", f"{ifa.capitalize()} {p['q']}"] + [f"{a} {b}" for a, b in d["excip"]]
    if p["forma"].startswith("Polvo"):
        comp.append("Solvente: agua para inyectables 4 ml")
    else:
        comp.append("Agua para inyectables c.s.p.")
    conserv = [f"Conservar entre {d['tmin']} °C y {d['tmax']} °C (en heladera). No congelar.",
               "Conservar en el envase original para protegerlo de la luz.",
               f"Período de vida útil: {d['vida']} meses."]
    pie = [f"Especialidad medicinal autorizada por el Ministerio de Salud. Certificado N° {d['cert']}.",
           f"Titular: {d['lab']}, {d['dom']}.", "Director Técnico: farmacéutico/a responsable según habilitación.",
           f"Fecha de última revisión: {d['rev_a']}."]
    enc = [f"{n}®", f"{ifa.upper()} {p['conc']}", p["forma"], f"Vía de administración: {p['via']}", "Venta bajo receta archivada",
           "Industria extranjera"]
    prosp = [("COMPOSICION", comp),
             ("ACCION", [f"{p['clase'].capitalize()}. Agente inmunomodulador / biológico."]),
             ("INDICACIONES", [f"{n} está indicado para el tratamiento de pacientes con {p['indic']}."]),
             ("PROPIEDADES", [f"Mecanismo de acción: {ifa} es un {p['clase']} que se une a {p['diana']} y bloquea su actividad.",
                              f"Farmacocinética: la vida media de eliminación es de aproximadamente {d['vm']} días y el estado estacionario se alcanza a las 12 semanas."]),
             ("POSOLOGIA", [f"La dosis recomendada es {p['dosis']}.",
                            "El tratamiento debe ser iniciado y supervisado por un médico con experiencia en la patología.",
                            "No se recomienda reducir la dosis; ante toxicidad se debe interrumpir o suspender el tratamiento."]),
             ("CONTRAINDICACIONES", ["Hipersensibilidad al principio activo o a alguno de los excipientes."]),
             ("ADVERTENCIAS", ["Reacciones de hipersensibilidad: ante una reacción grave se debe suspender la administración e instaurar el tratamiento adecuado.",
                               "Infecciones: se debe evaluar a los pacientes antes de iniciar el tratamiento y vigilar signos de infección."]),
             ("INTERACCIONES", ["No se han realizado estudios formales de interacciones farmacocinéticas."]),
             ("POBLACIONES", ["No hay datos suficientes sobre el uso en mujeres embarazadas. Se desconoce si se excreta en la leche materna."]),
             ("RAM", ["Las reacciones adversas más frecuentes (10 % o más) fueron cefalea, náuseas y reacciones en el sitio de administración.",
                      "Trastornos de la sangre: anemia (frecuente)."]),
             ("SOBREDOSIS", ["No se notificaron casos de sobredosis en los estudios clínicos. Ante la eventualidad de una sobredosificación, "
                             "concurrir al hospital más cercano o comunicarse con un centro de toxicología."]),
             ("PRESENTACION", [f"Envase conteniendo 1 {p['envase']}."]),
             ("CONSERVACION", conserv),
             ("ELABORADOR", [d["elab"]])]
    ip = [("INDICACIONES", [f"{n} contiene el principio activo {ifa}. Se utiliza para tratar {p['indic']}."]),
          ("ADVERTENCIAS", [f"No use {n} si es alérgico al principio activo o a alguno de los demás componentes.",
                            "Consulte a su médico si tiene una infección o si presenta fiebre."]),
          ("POSOLOGIA", [f"Su médico le indicará la dosis. La dosis habitual es {p['dosis']}.", "No interrumpa el tratamiento sin consultar a su médico."]),
          ("RAM", ["Al igual que todos los medicamentos, este medicamento puede producir efectos adversos, aunque no todas las personas los sufran.",
                   "Muy frecuentes: dolor de cabeza, náuseas, enrojecimiento en el sitio de inyección."]),
          ("CONSERVACION", [f"Conservar entre {d['tmin']} °C y {d['tmax']} °C. No congelar. Mantener fuera del alcance de los niños.",
                            f"Período de vida útil: {d['vida']} meses."]),
          ("PRESENTACION", [f"Envase conteniendo 1 {p['envase']}.", f"Composición: cada {p['unidad']} contiene {p['q']} de {ifa}."])]
    rot = [("COMPOSICION", comp),
           ("POSOLOGIA", ["Ver prospecto adjunto."]),
           ("CONSERVACION", conserv[:1] + [f"Vida útil: {d['vida']} meses."]),
           ("PRESENTACION", [f"Envase conteniendo 1 {p['envase']}.", "Lote: ............  Vto.: ............"]),
           ("ELABORADOR", [d["elab"]])]
    return {"prospecto": {"titulo": "PROYECTO DE PROSPECTO — INFORMACIÓN PARA EL PROFESIONAL", "enc": enc, "secs": prosp, "pie": pie},
            "ip": {"titulo": "INFORMACIÓN PARA EL PACIENTE", "enc": enc[:3] + ["Lea todo este prospecto detenidamente antes de empezar a usar el medicamento."], "secs": ip, "pie": pie},
            "rotulo": {"titulo": "PROYECTO DE RÓTULO SECUNDARIO (ESTUCHE)", "enc": enc[:5], "secs": rot, "pie": pie[:3]}}


def copiar(t):
    return {"titulo": t["titulo"], "enc": list(t["enc"]), "secs": [(k, list(v)) for k, v in t["secs"]], "pie": list(t["pie"])}


def sec(t, clave):
    for k, v in t["secs"]:
        if k == clave:
            return v
    raise KeyError(clave)


# ───────────────────────── PDF ─────────────────────────
class Doc:
    def __init__(self, path, sello=None, encabezado_pagina=None):
        self.c = canvas.Canvas(path, pagesize=A4); self.w, self.h = A4; self.sello = sello; self.encp = encabezado_pagina
        self.pag = 1; self._top()
    def _top(self):
        self.y = self.h - 2.0 * cm
        if self.encp:
            self.c.setFont("Helvetica-Bold", 9); self.c.drawString(2.2 * cm, self.y, self.encp); self.y -= 0.7 * cm
    def _pie(self):
        if self.sello:
            self.c.setFont("Helvetica", 7); self.c.drawString(2.2 * cm, 1.3 * cm, self.sello)
            self.c.drawRightString(self.w - 2.2 * cm, 1.3 * cm, f"Página {self.pag}")
    def nl(self, d=0.5):
        self.y -= d * cm
        if self.y < 2.4 * cm:
            self._pie(); self.c.showPage(); self.pag += 1; self._top()
    def txt(self, t, bold=False, size=10, x=2.2):
        self.c.setFont("Helvetica-Bold" if bold else "Helvetica", size); self.c.drawString(x * cm, self.y, t); self.nl()
    def centro(self, t, size=11, bold=True):
        self.c.setFont("Helvetica-Bold" if bold else "Helvetica", size); self.c.drawCentredString(self.w / 2, self.y, t); self.nl(0.55)
    def parrafo(self, t, ancho=98, bold=False, x=2.2):
        linea = ""
        for w in t.split():
            if len(linea) + len(w) + 1 > ancho:
                self.txt(linea, bold, x=x); linea = w
            else:
                linea = (linea + " " + w).strip()
        if linea: self.txt(linea, bold, x=x)
    def fila(self, celdas, xs, anchos):
        """Fila de tabla: cada celda se parte en renglones dentro de su columna."""
        partes = []
        for c_, a in zip(celdas, anchos):
            ls, l = [], ""
            for w in str(c_).split():
                if len(l) + len(w) + 1 > a: ls.append(l); l = w
                else: l = (l + " " + w).strip()
            ls.append(l); partes.append(ls)
        for i in range(max(len(p) for p in partes)):
            self.c.setFont("Helvetica", 9)
            for p, x in zip(partes, xs):
                if i < len(p): self.c.drawString(x * cm, self.y, p[i])
            self.nl(0.45)
        self.nl(0.15)
    def fin(self):
        self._pie(); self.c.save()


def render_texto(path, t, doc, rol, d, comentarios=None, fecha_dup=None):
    """rol: aprobado (sello IF por página) | proyecto | cc_a (texto eliminado conservado + globos) | cc_b (solo encabezado CONTROL DE CAMBIOS)."""
    sello = f"{d['if_'+doc]}   —   Página firmada digitalmente" if rol == "aprobado" else None
    D = Doc(path, sello=sello, encabezado_pagina="CONTROL DE CAMBIOS" if rol == "cc_b" else None)
    D.centro(t["titulo"], 11)
    for l in t["enc"]:
        D.txt(l, bold=l == t["enc"][0])
    D.nl()
    H = H_PROSP if doc == "prospecto" else H_IP if doc == "ip" else H_ROT
    for k, v in t["secs"]:
        if k not in H: continue
        D.txt(H[k].format(n=d["nombre"]), bold=True)
        for o in v:
            D.parrafo(o)
        if comentarios and k in comentarios:
            D.parrafo(comentarios[k])
        D.nl(0.3)
    for l in t["pie"]:
        if fecha_dup and l.startswith("Fecha de última revisión"):
            l = fecha_dup
        D.parrafo(l)
    D.fin()


# ───────────────────────── cambios ─────────────────────────
def aplicar(textos, cambios):
    """cambios: lista de dict(doc, sec, tipo='agrega'|'reemplaza', nuevo, viejo). Devuelve (P, CC-unión)."""
    P = {k: copiar(v) for k, v in textos.items()}
    CC = {k: copiar(v) for k, v in textos.items()}
    for c in cambios:
        if c["doc"] not in P: continue
        sp, sc = sec(P[c["doc"]], c["sec"]), sec(CC[c["doc"]], c["sec"])
        if c["tipo"] == "agrega":
            sp.append(c["nuevo"]); sc.append(c["nuevo"])
        else:
            i = sp.index(c["viejo"]); sp[i] = c["nuevo"]
            j = sc.index(c["viejo"]); sc[j] = c["viejo"] + " " + c["nuevo"]   # el tachado sobrevive como texto en el OCR
    return P, CC


def cambios_clinicos(p, d, r, docs_mod, extra_indic=False):
    ev, ev_ip = r.choice(EVENTOS); ram = r.choice(RAM_NUEVAS); n = p["nombre"]
    cc = []
    tipo = r.choice(["seg", "seg", "posol"])
    if "prospecto" in docs_mod:
        cc.append(dict(doc="prospecto", sec="ADVERTENCIAS", tipo="agrega", clin=True,
                       nuevo=f"{ev.capitalize()}: se han notificado casos de {ev} en pacientes tratados con {p['ifa']}. Se debe vigilar a los pacientes y suspender el tratamiento si se confirma el diagnóstico.",
                       resumen=f"Se incorpora advertencia sobre {ev}."))
        cc.append(dict(doc="prospecto", sec="RAM", tipo="agrega", clin=True,
                       nuevo=f"Experiencia poscomercialización: {ram} (frecuencia no conocida); {ev} (poco frecuente).",
                       resumen=f"Se agregan {ram} y {ev} a la experiencia poscomercialización."))
        if tipo == "posol":
            cc.append(dict(doc="prospecto", sec="POSOLOGIA", tipo="reemplaza", clin=True, viejo=f"La dosis recomendada es {p['dosis']}.",
                           nuevo=f"La dosis recomendada es {p['dosis']}. Como alternativa puede administrarse {p['dosis2']}.",
                           resumen="Se incorpora esquema posológico alternativo."))
    if "ip" in docs_mod:
        cc.append(dict(doc="ip", sec="RAM", tipo="agrega", clin=True,
                       nuevo=f"Frecuencia no conocida: {ram}. Consulte de inmediato a su médico si presenta síntomas de {ev_ip}.",
                       resumen=f"Se agregan {ram} y síntomas de {ev_ip}."))
        cc.append(dict(doc="ip", sec="ADVERTENCIAS", tipo="agrega", clin=True,
                       nuevo=f"Informe a su médico si presenta síntomas que puedan corresponder a {ev_ip}.",
                       resumen=f"Se agrega advertencia sobre {ev_ip}."))
    if extra_indic:
        cc.append(dict(doc="prospecto", sec="INDICACIONES", tipo="agrega", clin=True, nueva_ind=True,
                       nuevo=f"{n} también está indicado, en combinación con quimioterapia, para el tratamiento de pacientes con {p['indic2']}.",
                       resumen=f"Nueva indicación: {p['indic2']}."))
        cc.append(dict(doc="prospecto", sec="POSOLOGIA", tipo="agrega", clin=True,
                       nuevo=f"Para la nueva indicación la dosis recomendada es {p['dosis2']}.", resumen="Posología para la nueva indicación."))
        if "ip" in docs_mod:
            cc.append(dict(doc="ip", sec="INDICACIONES", tipo="agrega", clin=True, nueva_ind=True,
                           nuevo=f"También se utiliza junto con quimioterapia para tratar {p['indic2']}.", resumen="Nueva indicación."))
    return cc


def cambios_calidad(p, d, r, docs_mod, tipo):
    cc = []
    if tipo == "vida_util":
        nv = d["vida"] + 12
        for doc in docs_mod:
            k = "Período de vida útil" if doc != "rotulo" else "Vida útil"
            cc.append(dict(doc=doc, sec="CONSERVACION", tipo="reemplaza", clin=False, calidad=True,
                           viejo=f"{k}: {d['vida']} meses.", nuevo=f"{k}: {nv} meses.",
                           resumen=f"Período de vida útil: {d['vida']} meses → {nv} meses."))
        return cc, ("Período de vida útil", f"{d['vida']} meses", f"{nv} meses")
    if tipo == "conservacion":
        for doc in docs_mod:
            cc.append(dict(doc=doc, sec="CONSERVACION", tipo="agrega", clin=False, calidad=True,
                           nuevo="Una vez fuera de la heladera puede conservarse a temperatura no mayor de 25 °C durante 30 días como máximo.",
                           resumen="Se incorpora condición de conservación fuera de heladera (hasta 25 °C, 30 días)."))
        return cc, ("Condiciones de conservación", f"{d['tmin']} °C a {d['tmax']} °C", f"{d['tmin']} °C a {d['tmax']} °C; hasta 25 °C por 30 días")
    if tipo == "excipiente":
        a, b = d["excip"][-1]
        nb = re.sub(r"[\d,]+", lambda m: str(round(float(m.group(0).replace(",", ".")) * 2, 2)).replace(".", ","), b, count=1)
        for doc in docs_mod:
            if doc == "ip": continue
            cc.append(dict(doc=doc, sec="COMPOSICION", tipo="reemplaza", clin=False, calidad=True, viejo=f"{a} {b}", nuevo=f"{a} {nb}",
                           resumen=f"Fórmula cuali-cuantitativa: {a} {b} → {nb}."))
        return cc, ("Fórmula cuali-cuantitativa", f"{a} {b}", f"{a} {nb}")
    if tipo == "elaborador":
        nuevo = r.choice([e for e in ELABS if e != d["elab"]])
        for doc in docs_mod:
            if doc == "ip": continue
            cc.append(dict(doc=doc, sec="ELABORADOR", tipo="reemplaza", clin=False, calidad=True, viejo=d["elab"], nuevo=d["elab"] + ". Elaborador alternativo: " + nuevo,
                           resumen=f"Se incorpora elaborador alternativo del producto terminado: {nuevo}."))
        return cc, ("Elaboradores", d["elab"], d["elab"] + " / " + nuevo)
    raise ValueError(tipo)


# ───────────────────────── documentos administrativos ─────────────────────────
def nota(path, d, docs_nota, motivo):
    D = Doc(path)
    D.txt(f"Buenos Aires, {d['fecha']}"); D.nl()
    D.centro("NOTA DE PRESENTACIÓN", 12)
    D.txt("Señor Administrador Nacional de la ANMAT"); D.txt("Dirección de Evaluación y Control de Biológicos y Radiofármacos"); D.txt("S / D"); D.nl()
    D.txt(f"Ref.: Concepto 2302 – Modificación de rótulos, prospectos e información para el paciente", bold=True)
    D.txt(f"Expediente N°: {d['expediente']}"); D.nl()
    D.parrafo(f"De nuestra mayor consideración: {d['lab_nota']}, en su carácter de titular del certificado del producto que se detalla, "
              "se dirige a Ud. a fin de solicitar la modificación de los textos que se indican.")
    D.nl(); D.txt("DATOS DEL PRODUCTO", bold=True)
    for k, v in [("Nombre comercial", d["nombre_nota"]), ("IFA", d["ifa_nota"]), ("Concentración", d["conc_nota"]),
                 ("Forma farmacéutica", d["forma_nota"]), ("Certificado N°", d["cert_nota"]), ("Titular", d["lab_nota"])]:
        D.txt(f"{k}: {v}")
    D.nl(); D.txt("MOTIVO DEL TRÁMITE:", bold=True); D.parrafo(motivo); D.nl()
    D.txt("Textos que se presentan:", bold=True)
    for x in docs_nota:
        D.txt(f"• {NOMBRE_DOC[x]}: versión con control de cambios y proyecto.")
    D.nl(); D.parrafo("Se declara que las demás secciones no se encuentran impactadas por el presente trámite.")
    D.txt("Sin otro particular, saludamos a Ud. muy atentamente."); D.nl(1.0)
    D.txt("Firma: Apoderado / Director Técnico"); D.fin()


def formulario(path, d, formato, filas_tabla, docs_tabla, quality_rows, casillas, ddjj_externa=False, clinico=True):
    D = Doc(path)
    D.centro("1.2 FORMULARIO DE SOLICITUD", 12)
    D.centro("Variación post-registro — Productos biológicos", 10, False); D.nl()
    D.txt("DATOS DEL PRODUCTO", bold=True)
    for k, v in [("Nombre comercial", d["nombre_form"]), ("IFA", d["ifa_form"]), ("Concentración", d["conc_form"]),
                 ("Forma farmacéutica", d["forma_form"]), ("Certificado N°", d["cert_form"]), ("Titular", d["lab_form"])]:
        D.txt(f"{k}: {v}")
    D.nl(); D.txt("ALCANCE DE LA APLICACIÓN", bold=True)
    for k, v in casillas:
        D.txt(f"{'[X]' if v else '[ ]'} {k}")
    D.nl()
    if formato == "F3":
        D.txt("TABLA DE MODIFICACIONES — RESUMEN DE LOS CAMBIOS", bold=True)
        D.fila(["Documento", "Sección", "Resumen del cambio"], [2.2, 6.5, 11], [24, 26, 48])
        for f in filas_tabla:
            D.fila([f["doc_txt"], f["sec_txt"], f["resumen"]], [2.2, 6.5, 11], [24, 26, 48])
        for x in ["prospecto", "ip", "rotulo"]:
            if x not in docs_tabla:
                D.fila([NOMBRE_DOC[x], "—", "No hay modificaciones en este ítem."], [2.2, 6.5, 11], [24, 26, 48])
        for q in quality_rows:
            D.fila(["Datos característicos", q[0], f"Aprobado: {q[1]}. Propuesto: {q[2]}."], [2.2, 6.5, 11], [24, 26, 48])
    elif formato == "F2":
        D.txt("FICHA DE MODIFICACIONES", bold=True)
        D.fila(["Dato", "Aprobación anterior", "Modificación propuesta"], [2.2, 8, 13], [30, 28, 34])
        qr = {q[0]: q for q in quality_rows}
        for dato, val in [("Nombre comercial", d["nombre"]), ("Nombre genérico (IFA)", d["ifa"]), ("Concentración", d["conc"]),
                          ("Forma farmacéutica", d["forma"]), ("Fórmula cuali-cuantitativa", "Según certificado"),
                          ("Período de vida útil", f"{d['vida']} meses"), ("Condiciones de conservación", f"{d['tmin']} °C a {d['tmax']} °C"),
                          ("Elaboradores", d["elab"]), ("Condición de expendio", "Venta bajo receta archivada")]:
            if dato in qr:
                D.fila([dato, qr[dato][1], "CON MODIFICACIÓN: " + qr[dato][2]], [2.2, 8, 13], [30, 28, 34])
            else:
                D.fila([dato, val, "SIN MODIFICACIÓN"], [2.2, 8, 13], [30, 28, 34])
        for x in ["prospecto", "ip", "rotulo"]:
            fs = [f for f in filas_tabla if f["doc"] == x]
            if fs:
                D.fila([NOMBRE_DOC[x], "Versión aprobada", "CON MODIFICACIÓN"], [2.2, 8, 13], [30, 28, 34])
                for f in fs:
                    D.fila([f"   Sección {f['sec_txt']}", "", f["resumen"]], [2.2, 8, 13], [30, 28, 34])
            else:
                D.fila([NOMBRE_DOC[x], "Versión aprobada", "SIN MODIFICACIÓN"], [2.2, 8, 13], [30, 28, 34])
    elif formato == "F4":
        D.txt("DECLARACIÓN JURADA — DATOS AFECTADOS Y MODIFICACIÓN SOLICITADA", bold=True)
        for x in ["prospecto", "ip", "rotulo"]:
            D.txt(NOMBRE_DOC[x].upper(), bold=True)
            fs = [f for f in filas_tabla if f["doc"] == x]
            if not fs:
                D.fila(["Datos afectados: N/A", "Modificación solicitada: N/A"], [2.2, 8.5], [36, 58]); continue
            D.fila(["Datos afectados", "Modificación solicitada"], [2.2, 8.5], [36, 58])
            for f in fs:
                D.fila([f["sec_txt"], f"Pág. {f['pag']}: {f['resumen']}"], [2.2, 8.5], [36, 58])
        if quality_rows:
            D.txt("DATOS CARACTERÍSTICOS", bold=True)
        for q in quality_rows:
            D.fila([q[0], f"Aprobado: {q[1]}. Propuesto: {q[2]}."], [2.2, 8.5], [36, 58])
    elif formato == "F6":
        D.txt("ANTECEDENTES Y DESCRIPCIÓN DE LOS CAMBIOS", bold=True)
        D.parrafo("Se actualizan los textos del producto según la información de seguridad de la casa matriz. El detalle de los cambios "
                  "se presenta en la Declaración Jurada de únicos cambios que acompaña a esta solicitud.")
        for q in quality_rows:
            D.parrafo(f"Datos característicos — {q[0]}: aprobado {q[1]}; propuesto {q[2]}.")
    D.nl()
    if clinico and not quality_rows:
        D.parrafo("Se declara que los nuevos textos no incluyen modificaciones de los datos característicos del producto.")
    D.txt("DOCUMENTACIÓN SOPORTE", bold=True)
    D.parrafo("Información de seguridad de la casa matriz (CCDS) y referencias de agencias internacionales, según corresponda.")
    D.nl(); D.txt("Firma: Apoderado / Director Técnico"); D.fin()


def ddjj_cambios(path, d, filas):
    D = Doc(path)
    D.centro("DECLARACIÓN JURADA", 12); D.nl()
    D.parrafo(f"Producto: {d['nombre']} — {d['ifa']} {d['conc']} — Certificado N° {d['cert']}.")
    D.parrafo("Con carácter de declaración jurada expresamos que los únicos cambios introducidos en los textos son los que se detallan a continuación:")
    D.nl()
    D.fila(["#", "Documento", "Sección", "Anterior", "Actual", "Soporte"], [2.2, 3.0, 6.3, 9.6, 12.6, 16.6], [3, 18, 18, 18, 22, 12])
    for i, f in enumerate(filas, 1):
        D.fila([str(i), NOMBRE_DOC[f["doc"]].split(" (")[0], f["sec_txt"], "Texto aprobado", f["resumen"], "CCDS"],
               [2.2, 3.0, 6.3, 9.6, 12.6, 16.6], [3, 18, 18, 18, 22, 12])
    D.nl(); D.txt("Firma: Apoderado / Director Técnico"); D.fin()


def ddjj_no_impactada(path, d, doc):
    D = Doc(path)
    D.centro("DECLARACIÓN JURADA", 12); D.nl()
    D.parrafo(f"Producto: {d['nombre']} — Certificado N° {d['cert']} — Titular: {d['lab']}.")
    D.parrafo(f"Por medio de la presente declaramos con carácter de declaración jurada que la sección {NOMBRE_DOC[doc]} "
              "no se encuentra impactada por el presente trámite. No hay modificaciones en este ítem.")
    D.nl(); D.txt("Firma: Apoderado / Director Técnico"); D.fin()


def certificado(path, d):
    D = Doc(path, sello=d["if_cert"])
    D.centro("REPÚBLICA ARGENTINA — MINISTERIO DE SALUD — ANMAT", 10)
    D.centro("CERTIFICADO DE INSCRIPCIÓN EN EL REGISTRO DE ESPECIALIDADES MEDICINALES (REM)", 10)
    D.centro(f"CERTIFICADO N° {d['cert']}", 12); D.nl()
    D.txt(f"Disposición autorizante: {d['dispo']}")
    D.txt(f"Expediente autorizante N°: {d['exp_aut']}"); D.nl()
    D.txt("1. DATOS DE LA EMPRESA TITULAR", bold=True)
    D.txt(f"Razón Social: {d['lab']}"); D.txt(f"Domicilio: {d['dom']}"); D.nl()
    D.txt("2. DATOS DE LA ESPECIALIDAD MEDICINAL", bold=True)
    for k, v in [("Nombre comercial", d["nombre"]), ("Nombre Genérico (IFA/s)", d["ifa"].upper()), ("Concentración", d["conc"]),
                 ("Forma farmacéutica", d["forma"].upper()), ("Origen", "BIOTECNOLÓGICO"), ("Vía de administración", d["via"].upper()),
                 ("Envase primario", d["envase"]), ("Período de vida útil", f"{d['vida']} MESES"),
                 ("Forma de conservación", f"Desde {d['tmin']} °C hasta {d['tmax']} °C"), ("Condición de expendio", "BAJO RECETA ARCHIVADA")]:
        D.txt(f"{k}: {v}")
    D.txt("Fórmula cuali-cuantitativa por unidad:")
    D.txt(f"   {d['ifa'].capitalize()} {d['q']}")
    for a, b in d["excip"]:
        D.txt(f"   {a} {b}")
    D.txt(f"Indicaciones: {d['indic'].capitalize()}.")
    D.nl(); D.txt("3. DATOS DEL ELABORADOR", bold=True); D.txt(f"Elaborador del producto terminado: {d['elab']}")
    D.nl(); D.txt("4. AUTORIZACIÓN EFECTIVA DE COMERCIALIZACIÓN", bold=True); D.txt("Autorizada.")
    D.fin()


def resumen_clinico(path, d, ingles=False):
    D = Doc(path)
    if ingles:
        D.centro("MODULE 2.5 — CLINICAL OVERVIEW", 12); D.nl()
        for t in [f"This clinical overview summarises the efficacy and safety data supporting the use of {d['nombre']} ({d['ifa']}) in patients with {d['indic2_en']}.",
                  "The pivotal study was a randomised, open-label, multicentre phase 3 trial. The primary endpoint was overall survival and the key secondary endpoint was progression-free survival.",
                  "The safety profile was consistent with the known profile of the product. No new safety signals were identified and the benefit-risk balance is considered positive.",
                  "The most common adverse reactions were fatigue, nausea, rash and infusion-related reactions. Immune-mediated adverse reactions were manageable with established guidelines.",
                  "In conclusion, the data support the proposed new indication and the corresponding updates to the product information."]:
            D.parrafo(t); D.nl(0.3)
    else:
        D.centro("2.5 ASPECTOS CLÍNICOS GENERALES — RESUMEN CLÍNICO", 12); D.nl()
        for t in [f"El presente resumen describe los datos de eficacia y seguridad que sustentan el uso de {d['nombre']} ({d['ifa']}) en pacientes con {d['indic2']}.",
                  "El estudio pivotal fue un ensayo de fase 3, aleatorizado, abierto y multicéntrico. La variable principal fue la supervivencia global.",
                  "El perfil de seguridad fue coherente con el conocido para el producto y no se identificaron nuevas señales.",
                  "Los datos presentados sustentan la nueva indicación propuesta y las modificaciones correspondientes del prospecto."]:
            D.parrafo(t); D.nl(0.3)
    D.fin()


def referencia(path, d, agencia):
    D = Doc(path)
    if agencia == "FDA":
        D.txt("HIGHLIGHTS OF PRESCRIBING INFORMATION", bold=True)
        for t in [f"These highlights do not include all the information needed to use {d['nombre']} safely and effectively. See full prescribing information for {d['nombre']}.",
                  f"{d['nombre']} ({d['ifa']}) injection, for intravenous or subcutaneous use. Initial U.S. Approval: 2021",
                  "RECENT MAJOR CHANGES: Warnings and Precautions (5.3) 10/2026",
                  "FULL PRESCRIBING INFORMATION", "1 INDICATIONS AND USAGE",
                  f"{d['nombre']} is indicated for the treatment of adult patients with the approved indications described in this label.",
                  "5 WARNINGS AND PRECAUTIONS", "5.3 Immune-mediated adverse reactions: monitor patients for signs and symptoms and withhold the product as appropriate.",
                  "6 ADVERSE REACTIONS", "The most common adverse reactions (incidence of 20% or more) were fatigue, rash and nausea."]:
            D.parrafo(t)
    elif agencia == "EMA":
        D.txt("ANEXO I", bold=True); D.txt("FICHA TÉCNICA O RESUMEN DE LAS CARACTERÍSTICAS DEL PRODUCTO", bold=True)
        for t in ["1. NOMBRE DEL MEDICAMENTO", f"{d['nombre']} {d['conc']} concentrado o solución inyectable",
                  "2. COMPOSICIÓN CUALITATIVA Y CUANTITATIVA", f"Cada unidad contiene {d['q']} de {d['ifa']}.",
                  "4.4 Advertencias y precauciones especiales de empleo", "Se debe vigilar a los pacientes para detectar signos y síntomas de reacciones inmunomediadas.",
                  "4.8 Reacciones adversas", "Las reacciones adversas más frecuentes fueron fatiga, erupción y náuseas.",
                  "Agencia Europea de Medicamentos — información del producto (EPAR) en español."]:
            D.parrafo(t)
    else:  # documento de la empresa en inglés (no es referencia de agencia)
        D.txt("COMPANY CORE DATA SHEET (CCDS)", bold=True)
        for t in [f"Product: {d['nombre']} ({d['ifa']}). Version 14.0. This document is the company's internal reference safety information.",
                  "4.4 Special warnings and precautions for use",
                  "Patients should be monitored for signs and symptoms of immune-mediated reactions. Treatment should be withheld or permanently discontinued depending on severity.",
                  "4.8 Undesirable effects",
                  "The following adverse reactions have been identified during post-approval use. Because these reactions are reported voluntarily, it is not always possible to estimate their frequency.",
                  "This document is intended for internal use by the marketing authorisation holder and its affiliates."]:
            D.parrafo(t)
    D.fin()


def soporte_calidad(path, d, alcance):
    D = Doc(path)
    D.centro(d["lab"].upper(), 11); D.centro("DOCUMENTO DECLARADO POR EL REGULADO", 11)
    D.centro("CTD Módulo 3 — Sección 3.2.P.8 Estabilidad", 10, False); D.nl()
    D.txt("1. ALCANCE", bold=True)
    D.parrafo(f"Se presentan los datos de estabilidad y el soporte de calidad del producto {d['nombre']} ({d['ifa']}) que sustentan la modificación: {alcance}.")
    D.txt("2. RESULTADOS", bold=True)
    D.parrafo("Los lotes evaluados cumplieron las especificaciones de liberación y de estabilidad en todos los tiempos estudiados.")
    D.txt("3. CONCLUSIÓN", bold=True); D.parrafo("Los resultados avalan la modificación propuesta.")
    D.fin()


# ───────────────────────── escenarios ─────────────────────────
# (código, descripción, cantidad, asignación esperada, dictamen esperado, objeciones esperadas, observaciones/información esperadas)
ESC = [
    ("completo_clinico", "Expediente clínico completo y coherente", 6, "Clínica", "APTO", [], []),
    ("completo_estilo_b", "Completo; el control de cambios solo tiene resaltado (OCR del CC = proyecto)", 2, "Clínica", "APTO", [], []),
    ("referencia_agencia", "Completo + referencia de agencia (label FDA en inglés o EPAR en español)", 4, "Clínica", "APTO", [], ["REF_AGENCIA"]),
    ("nota_distinta_tabla", "La nota omite un texto que sí figura en la tabla (nota ≠ tabla)", 3, "Clínica", "APTO", [], ["NOTA_TABLA"]),
    ("nueva_ind_sin_rc", "Nueva indicación sin resumen clínico", 2, "Clínica", "APTO", [], ["SIN_RC"]),
    ("nueva_ind_con_rc", "Nueva indicación con resumen clínico 2.5 en español", 2, "Clínica", "APTO", [], ["RC_RECIBIDO"]),
    ("calidad_pura", "Trámite de calidad puro (vida útil o conservación) que impacta textos", 3, "Calidad", "APTO", [], []),
    ("solo_rotulos_calidad", "Solo rótulos: cambio de composición cuantitativa (dato característico)", 2, "Calidad", "APTO", [], []),
    ("mixto", "Mixto: cambios clínicos + cambio de dato de calidad declarados", 3, "Ambas", "APTO", [], []),
    ("excipiente_efecto_conocido", "Leyenda de excipientes con efecto conocido sin cambio de cantidades", 2, "Clínica", "APTO", [], []),
    ("elaborador_por_disposicion", "Pie con elaborador actualizado según disposición ya aprobada", 2, "Clínica", "APTO", [], []),
    ("archivos_mal_nombrados", "Nombres de archivo que no coinciden con el rol real (proyecto/CC/aprobado)", 2, "Clínica", "APTO", [], ["ROL_NOMBRE"]),
    ("falta_cc", "Un texto declarado como modificado no trae versión con control de cambios", 3, "Clínica", "OBJETAR", ["FALTA_CC"], []),
    ("falta_proyecto", "Un texto declarado no trae proyecto limpio (falta o el 'proyecto' tiene marcas de CC)", 4, "Clínica", "OBJETAR", ["FALTA_P"], []),
    ("no_declarado", "Cambio clínico detectable en los textos que no figura en la tabla", 4, "Clínica", "OBJETAR", ["NO_DECLARADO"], []),
    ("calidad_no_declarado", "Tabla clínica, pero el proyecto cambia un dato de calidad no declarado", 2, "Ambas", "OBJETAR", ["NO_DECLARADO"], []),
    ("falta_certificado", "No se presenta el certificado REM", 3, "Clínica", "OBJETAR", ["FALTA_CERT"], []),
    ("incongruencia", "Dato identificatorio distinto del certificado (nombre, IFA, concentración, forma, titular o N° de certificado)", 6, "Clínica", "OBJETAR", ["INCONGRUENCIA"], []),
    ("documento_ingles", "Documento propio en inglés que no es referencia de agencia", 3, "Clínica", "OBJETAR", ["IDIOMA"], []),
    ("combinado", "Varias fallas a la vez (falta CC + documento en inglés)", 2, "Clínica", "OBJETAR", ["FALTA_CC", "IDIOMA"], []),
]
CONT = {"inc": -1}
DEV_POR_ESC = {"completo_clinico": 2, "incongruencia": 2, "combinado": 0}


def nombre_archivo(r, doc, rol, ver):
    base = {"prospecto": r.choice(["PROSPECTO", "prospecto", "Prospectos", "prosp"]),
            "ip": r.choice(["INFORMACION PARA EL PACIENTE", "info paciente", "INF PACIENTE", "Informacion para el paciente"]),
            "rotulo": r.choice(["ROTULOS", "rotulos", "ROTULO 2rio"])}[doc]
    rot = {"aprobado": r.choice(["aprobado", "APROBADO", ""]), "cc": r.choice(["CTROL CAMBIOS", "ctrol cambios", "CONTROL CAMBIOS"]),
           "proyecto": r.choice(["PROYECTO", "proyecto", ""])}[rol]
    v = r.choice([f"V0{ver}", f"ver0{ver}", f"V 0{ver}"])
    return (" ".join(x for x in [base, v, rot] if x) + ".pdf")


def generar_caso(cid, esc, r, out):
    _, desc, _, asig, dict_esp, obj_esp, obs_esp = esc
    codigo = esc[0]
    p = dict(r.choice(PRODS)); lab, dom = r.choice(LABS)
    excip = r.sample(EXCIPIENTES, 4)
    y = 2026; m = r.randint(1, 10)
    d = dict(p, lab=lab, dom=dom, excip=excip, elab=r.choice(ELABS), vida=r.choice([24, 30, 36]), tmin=2, tmax=8, vm=r.randint(12, 26),
             cert=f"{r.randint(55, 61)}.{r.randint(100, 999)}", dispo=f"DI-{r.randint(2019, 2023)}-{r.randint(1000, 9999)}-APN-ANMAT#MS",
             exp_aut=f"1-0047-2000-{r.randint(1000, 9999)}-{r.randint(18, 23)}-{r.randint(1, 9)}",
             expediente=f"EX-{y}-{r.randint(10000000, 99999999)}-APN-DERM#ANMAT",
             fecha=f"{r.randint(1, 28)} de {MESES[m - 1]} de {y}", rev_a=f"{r.choice(MESES)} {r.randint(2022, 2025)}", rev_p=f"{MESES[m - 1]} {y}",
             indic2_en="locally advanced or metastatic disease after prior therapy")
    for k in ["prospecto", "ip", "rotulo", "cert"]:
        d["if_" + k] = f"IF-{r.randint(2021, 2025)}-{r.randint(10000000, 99999999)}-APN-DECBR#ANMAT"
    for k in ["nombre", "ifa", "conc", "forma", "cert", "lab"]:
        d[k + "_nota"] = d[k] if k != "ifa" else d["ifa"].upper()
        d[k + "_form"] = d[k] if k != "ifa" else d["ifa"].upper()
    formato = r.choice(["F2", "F3", "F4", "F6"])
    estilo = "B" if codigo == "completo_estilo_b" else r.choice(["A", "A", "B"])
    con_aprobado = True if estilo == "B" else r.random() < 0.75
    rot_mod = r.random() < 0.35

    # ── qué textos cambian y cómo ──
    docs_mod = ["prospecto", "ip"] + (["rotulo"] if rot_mod else [])
    quality_rows, cambios = [], []
    clin_docs = ["prospecto", "ip"]
    if codigo in ("calidad_pura",):
        t = r.choice(["vida_util", "conservacion"]); docs_mod = ["prospecto", "ip", "rotulo"]
        cq, qrow = cambios_calidad(p, d, r, docs_mod, t); cambios += cq; quality_rows.append(qrow); clin_docs = []
    elif codigo == "solo_rotulos_calidad":
        docs_mod = ["rotulo"]; cq, qrow = cambios_calidad(p, d, r, docs_mod, "excipiente"); cambios += cq; quality_rows.append(qrow); clin_docs = []
    else:
        cambios += cambios_clinicos(p, d, r, clin_docs, extra_indic=codigo.startswith("nueva_ind"))
        if codigo == "mixto":
            t = r.choice(["vida_util", "elaborador"]); qd = ["prospecto", "rotulo"] if t == "elaborador" else ["prospecto", "ip", "rotulo"]
            docs_mod = sorted(set(docs_mod + qd), key=["prospecto", "ip", "rotulo"].index)
            cq, qrow = cambios_calidad(p, d, r, qd, t); cambios += cq; quality_rows.append(qrow)
        if codigo == "calidad_no_declarado":
            t = r.choice(["vida_util", "excipiente"]); qd = ["prospecto"]
            cq, _ = cambios_calidad(p, d, r, qd, t)
            for c in cq: c["no_declarar"] = True
            cambios += cq
        if codigo == "excipiente_efecto_conocido":
            cambios.append(dict(doc="prospecto", sec="COMPOSICION", tipo="agrega", clin=True,
                                nuevo=f"Este medicamento contiene {d['excip'][0][0].lower()}, excipiente con efecto conocido; puede provocar reacciones alérgicas.",
                                resumen="Se incorpora leyenda de excipientes con efecto conocido (sin cambio cuali-cuantitativo)."))
        if codigo == "elaborador_por_disposicion":
            nuevo = r.choice([e for e in ELABS if e != d["elab"]]); nd = f"DI-2025-{r.randint(1000, 9999)}-APN-ANMAT#MS"
            cambios.append(dict(doc="prospecto", sec="ELABORADOR", tipo="reemplaza", clin=False, viejo=d["elab"], nuevo=nuevo,
                                resumen=f"Se actualiza el elaborador según Disposición {nd}, ya aprobada (no constituye un cambio nuevo)."))
        if rot_mod and codigo not in ("mixto",):
            cambios.append(dict(doc="rotulo", sec="PRESENTACION", tipo="agrega", clin=False, admin=True,
                                nuevo="Mantener fuera del alcance de los niños.", resumen="Se agrega leyenda de seguridad en el estuche."))
    if codigo == "no_declarado":
        cand = [c for c in cambios if c.get("clin") and c["doc"] in ("prospecto", "ip")]
        r.choice(cand)["no_declarar"] = True
    docs_mod = sorted({c["doc"] for c in cambios}, key=["prospecto", "ip", "rotulo"].index)

    textos = base_textos(p, d)
    P, CCu = aplicar(textos, cambios)
    for t in P.values():
        t["pie"] = [l if not l.startswith("Fecha de última revisión") else f"Fecha de última revisión: {d['rev_p']}." for l in t["pie"]]

    # ── tabla de modificaciones ──
    filas = []
    for c in cambios:
        if c.get("no_declarar"): continue
        st = (NOMBRE_SEC_IP if c["doc"] == "ip" else NOMBRE_SEC)[c["sec"]]
        if any(f["doc"] == c["doc"] and f["sec"] == c["sec"] for f in filas):
            f = next(f for f in filas if f["doc"] == c["doc"] and f["sec"] == c["sec"]); f["resumen"] += " " + c["resumen"]; continue
        filas.append(dict(doc=c["doc"], sec=c["sec"], sec_txt=st, doc_txt=NOMBRE_DOC[c["doc"]], resumen=c["resumen"], pag=r.randint(2, 6)))
    docs_tabla = sorted({f["doc"] for f in filas}, key=["prospecto", "ip", "rotulo"].index)
    hay_clin = any(c.get("clin") for c in cambios)
    casillas = [("a. Modificación administrativa", any(c.get("admin") for c in cambios)), ("b. Información de seguridad", hay_clin),
                ("c. Información de eficacia", codigo.startswith("nueva_ind")), ("d. Otras (datos característicos / calidad)", bool(quality_rows))]

    motivo = {"calidad_pura": f"Actualización de los textos por modificación de un dato característico: {quality_rows[0][0].lower() if quality_rows else ''}.",
              "solo_rotulos_calidad": "Corrección de la composición cuantitativa declarada en los rótulos.",
              }.get(codigo, "Actualización de la información de seguridad según la información de la casa matriz." if not codigo.startswith("nueva_ind")
                    else f"Solicitud de modificación de prospecto — nueva indicación: {p['indic2']}.")
    if codigo == "mixto":
        motivo += f" Se modifica además un dato característico: {quality_rows[0][0].lower()}."
    docs_nota = list(docs_tabla)
    if codigo == "nota_distinta_tabla":
        quitar = "rotulo" if "rotulo" in docs_nota else "ip"
        docs_nota.remove(quitar)

    # ── incongruencias ──
    var = ""
    if codigo == "incongruencia":
        CONT["inc"] += 1; var = ["concentracion", "nombre", "certificado", "titular", "ifa", "forma"][CONT["inc"] % 6]
        donde = r.choice(["nota", "form", "texto"]) if var in ("concentracion", "nombre", "certificado") else r.choice(["nota", "form"])
        alt = {"concentracion": p["conc"].replace(p["conc"].split()[0], str(int(float(p["conc"].split()[0].replace(",", "."))) * 2)),
               "nombre": r.choice(OTROS_NOMBRES), "certificado": f"{r.randint(55, 61)}.{r.randint(100, 999)}",
               "titular": r.choice([l for l, _ in LABS if l != lab]), "ifa": r.choice(["velaxumab", "toralizumab", "denosivir"]).upper(),
               "forma": r.choice([f for f in ["Polvo liofilizado para solución inyectable", "Comprimidos recubiertos", "Solución inyectable en vial multidosis"] if f != p["forma"]])}[var]
        clave = {"concentracion": "conc", "nombre": "nombre", "certificado": "cert", "titular": "lab", "ifa": "ifa", "forma": "forma"}[var]
        if donde == "texto":
            t = P["prospecto"]
            if var == "concentracion": t["enc"][1] = f"{p['ifa'].upper()} {alt}"
            elif var == "nombre": t["enc"][0] = f"{alt}®"
            else: t["pie"][0] = f"Especialidad medicinal autorizada por el Ministerio de Salud. Certificado N° {alt}."
        else:
            d[f"{clave}_{donde}"] = alt
        var = f"{var}@{donde}"

    # ── archivos ──
    cdir = os.path.join(out, cid); os.makedirs(cdir)
    arch = []  # (nombre, tipo_real, rol_real)
    def add(nombre, tipo, rol=""):
        while any(a[0] == nombre for a in arch): nombre = nombre.replace(".pdf", "_.pdf")
        arch.append((nombre, tipo, rol)); return os.path.join(cdir, nombre)

    nota(add(r.choice(["NOTA PRES.pdf", "nota pres.pdf", "NOTA DE PRESENTACION.pdf", "NOTA PRES V 01.pdf"]), "nota"), d, docs_nota, motivo)
    formulario(add(r.choice(["FORM SOLI.pdf", "form soli.pdf", "FORMULARIO DE SOLICITUD.pdf", "Formulario de solicitud.pdf"]), "formulario"),
               d, formato, filas, docs_tabla, quality_rows, casillas, clinico=hay_clin)
    if formato == "F6":
        ddjj_cambios(add(r.choice(["DDJJ unicos cambios.pdf", "PROSPECTOS V04.pdf", "declaracion jurada cambios.pdf"]), "ddjj_cambios"), d, filas)
    if codigo != "falta_certificado":
        certificado(add(r.choice(["CERTI PRODUCTO.pdf", "certi producto.pdf", "DATOS DEL PRODUCTO.pdf", "certi pro.pdf"]), "certificado"), d)
    for x in ["prospecto", "ip", "rotulo"]:
        if x not in docs_mod:
            ddjj_no_impactada(add(f"{nombre_archivo(r, x, 'aprobado', 1).split(' ')[0]} {r.choice(['ddjj sin cambios', 'sin cambios', 'V01'])}.pdf", "ddjj_no_impactada"), d, x)

    # textos con cambios: aprobado (opcional), control de cambios, proyecto
    falta = {}
    if codigo in ("falta_cc", "combinado"): falta[r.choice(docs_mod)] = "cc"
    if codigo == "falta_proyecto": falta[r.choice(docs_mod)] = r.choice(["p", "p_no_limpio"])
    mal = codigo == "archivos_mal_nombrados"
    for x in docs_mod:
        vers = [1, 2, 3]; r.shuffle(vers)
        n_a = nombre_archivo(r, x, "aprobado", 1); n_cc = nombre_archivo(r, x, "cc", 3); n_p = nombre_archivo(r, x, "proyecto", 2)
        if mal and x == "prospecto":   # nombres engañosos: el rol real sale del contenido
            b = n_a.split(" ")[0]
            n_a, n_cc, n_p = f"{b} V01 PROYECTO.pdf", f"{b} V03 PROYECTO FINAL.pdf", f"{b} V02 CTROL CAMBIOS.pdf"
        if con_aprobado:
            render_texto(add(n_a, x, "aprobado"), textos[x], x, "aprobado", d)
        if falta.get(x) != "cc":
            if estilo == "A":
                coment = {c["sec"]: f"Comentado [{r.choice(['AB', 'RM', 'JL', 'XX'])}{i + 1}]: Actualización según CCDS v14."
                          for i, c in enumerate([c for c in cambios if c["doc"] == x][:2])}
                render_texto(add(n_cc, x, "control_cambios"), CCu[x] | {"pie": P[x]["pie"]}, x, "cc_a", d, comentarios=coment,
                             fecha_dup=f"Fecha de última revisión: {d['rev_a']}{d['rev_p']}.")
            else:
                render_texto(add(n_cc, x, "control_cambios"), P[x], x, "cc_b", d)
        if falta.get(x) == "p":
            continue
        if falta.get(x) == "p_no_limpio":
            render_texto(add(n_p, x, "control_cambios"), P[x], x, "cc_a", d, comentarios={[c for c in cambios if c["doc"] == x][0]["sec"]: "Commented [SV1]: Updated per CCDS"},
                         fecha_dup=f"Fecha de última revisión: {d['rev_a']} {d['rev_p']}.")
            continue
        render_texto(add(n_p, x, "proyecto"), P[x], x, "proyecto", d)

    # extras
    if codigo == "referencia_agencia":
        ag = r.choice(["FDA", "EMA"])
        referencia(add(r.choice(["761234s012lbl.pdf", "label FDA.pdf"]) if ag == "FDA" else r.choice(["EPAR.pdf", "producto-epar-product-information_es.pdf"]),
                       "referencia_" + ag.lower()), d, ag)
    if codigo == "nueva_ind_con_rc":
        resumen_clinico(add(r.choice(["Aspectos clinicos generales.pdf", "ASP CLINICOS GENERALES.pdf", "resu info clinica.pdf"]), "resumen_clinico"), d)
    if codigo in ("documento_ingles", "combinado"):
        if r.random() < 0.5:
            resumen_clinico(add(r.choice(["PROSPECTOS V05.pdf", "resumen clinico.pdf"]), "resumen_clinico_en"), d, ingles=True)
        else:
            referencia(add(r.choice(["CCDS v14.pdf", "soporte casa matriz.pdf"]), "ccds_en"), d, "CCDS")
    if quality_rows:
        soporte_calidad(add(r.choice(["3.2.P.8 estabilidad.pdf", "DOCUMENTO DECLARADO MODULO 3.pdf"]), "soporte_calidad"), d, quality_rows[0][0])

    motivos = list(obj_esp)
    return dict(caso=cid, escenario=codigo, descripcion=desc, variante=var, asignacion_esperada=asig, dictamen_esperado=dict_esp,
                objeciones_esperadas=";".join(motivos), observaciones_esperadas=";".join(obs_esp),
                producto=d["nombre"], ifa=d["ifa"], concentracion=d["conc"], forma=d["forma"], titular=d["lab"], certificado=d["cert"],
                formato_tabla=formato, estilo_cc=estilo, aprobado_presente=con_aprobado, rotulos_modificados="rotulo" in docs_mod,
                archivos="; ".join(f"{a[0]}={a[1]}{('/' + a[2]) if a[2] else ''}" for a in arch))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=2510); ap.add_argument("--out", default="casos")
    a = ap.parse_args(); r = random.Random(a.seed)
    if os.path.exists(a.out): shutil.rmtree(a.out)
    lista = []
    for e in ESC:
        ndev = DEV_POR_ESC.get(e[0], 1)
        lista += [(e, "DEV")] * ndev + [(e, "TEST")] * (e[2] - ndev)
    r.shuffle(lista)
    filas = []; ndev = ntest = 0
    for e, part in lista:
        if part == "DEV": ndev += 1; cid = f"CLIN-D{ndev:02d}"
        else: ntest += 1; cid = f"CLIN-T{ntest:02d}"
        fila = generar_caso(cid, e, r, os.path.join(a.out, part)); fila["particion"] = part; filas.append(fila)
    filas.sort(key=lambda f: (f["particion"], f["caso"]))
    campos = ["caso", "particion", "escenario", "descripcion", "variante", "asignacion_esperada", "dictamen_esperado", "objeciones_esperadas",
              "observaciones_esperadas", "producto", "ifa", "concentracion", "forma", "titular", "certificado", "formato_tabla", "estilo_cc",
              "aprobado_presente", "rotulos_modificados", "archivos"]
    gt = os.path.join(a.out, "ground_truth.csv")
    with open(gt, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=campos); w.writeheader(); w.writerows(filas)
    h = hashlib.sha256(open(gt, "rb").read()).hexdigest()
    man = dict(seed=a.seed, n=len(filas), dev=ndev, test=ntest, ground_truth_sha256=h,
               generador_sha256=hashlib.sha256(open(__file__, "rb").read()).hexdigest(),
               escenarios={e[0]: f"{e[1]} -> {e[3]} / {e[4]} {('[' + ','.join(e[5] + e[6]) + ']') if e[5] or e[6] else ''}" for e in ESC},
               codigos={"FALTA_CERT": "objeción: falta certificado REM", "FALTA_CC": "objeción: texto declarado sin versión con control de cambios",
                        "FALTA_P": "objeción: texto declarado sin proyecto limpio", "NO_DECLARADO": "objeción: cambio en los textos no declarado en la tabla",
                        "INCONGRUENCIA": "objeción: dato identificatorio distinto del certificado", "IDIOMA": "objeción: documento propio no en español",
                        "NOTA_TABLA": "observación: la nota no coincide con la tabla", "SIN_RC": "observación: nueva indicación sin resumen clínico",
                        "ROL_NOMBRE": "observación: nombre de archivo no coincide con el rol por contenido",
                        "RC_RECIBIDO": "información: resumen clínico recibido", "REF_AGENCIA": "información: referencia de agencia recibida"})
    json.dump(man, open(os.path.join(a.out, "manifest.json"), "w"), ensure_ascii=False, indent=1)
    print(json.dumps({k: man[k] for k in ("seed", "n", "dev", "test", "ground_truth_sha256")}))


if __name__ == "__main__":
    main()
