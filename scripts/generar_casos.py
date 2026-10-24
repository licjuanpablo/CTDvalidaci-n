#!/usr/bin/env python3
"""
Generador de expedientes FICTICIOS para validar el asistente de validación formal CTD.
Plantillas calcadas de los ejemplos del TP (carpeta "Archivos ejemplo"):
  01 Nota de presentación (Módulo 1.0)
  02 Formulario de solicitud de modificación post-registro (Módulo 1.2)
  03 Documento declarado por el regulado (CTD 3.2.S.4.3, validación del método analítico)
Todo es inventado. La referencia (ground_truth.csv) se fija ANTES de correr el sistema.
Semilla fija -> reproducible. DEV para ajustar, TEST congelado para el artículo.

Uso: python3 generar_casos.py [--n 60] [--dev 20] [--seed 2026] [--out casos]
"""
import argparse, csv, json, os, random, shutil, subprocess, hashlib
from datetime import date, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from PIL import Image, ImageFilter, ImageEnhance
import numpy as np

LABS = [("Laboratorios Farmacéuticos del Sur S.A.", "Av. Corrientes 1234, CABA", "30-71234567-8"),
        ("Biofarma Austral S.A.", "Av. Belgrano 845, CABA", "30-70981234-5"),
        ("Inmunogen Pampa S.A.", "Ruta 8 km 61, Pilar, Buenos Aires", "30-71555210-3"),
        ("Bioterapias del Plata S.R.L.", "Calle 50 N° 1120, La Plata", "30-71003456-9"),
        ("Andes Biologics S.A.", "Av. San Martín 2300, Mendoza", "30-70876543-1"),
        ("Proteica Rioplatense S.A.", "Av. Mitre 3400, Avellaneda", "30-71456789-2"),
        ("Vacunas Patagónicas S.A.", "Parque Industrial, Neuquén", "30-71234098-7"),
        ("Celltech Litoral S.R.L.", "Bv. Oroño 1550, Rosario", "30-70777888-4")]
PRODUCTOS = [("BIOPROTEX 100 mg/mL", "Adalimumab", "anticuerpo monoclonal humano anti-TNF-alfa", "Solución inyectable", "Jeringa prellenada 1 mL", "Subcutánea"),
             ("TRASTUFIC 150 mg", "Trastuzumab", "anticuerpo monoclonal humanizado anti-HER2", "Polvo liofilizado para solución", "Vial 150 mg", "Intravenosa"),
             ("ERITROPLAT 4000 UI", "Epoetina alfa", "eritropoyetina humana recombinante", "Solución inyectable", "Jeringa prellenada 0,4 mL", "Subcutánea/Intravenosa"),
             ("RITUXAN-AR 500 mg", "Rituximab", "anticuerpo monoclonal quimérico anti-CD20", "Concentrado para solución", "Vial 50 mL", "Intravenosa"),
             ("FILGRAPAMP 300 mcg", "Filgrastim", "factor estimulante de colonias de granulocitos", "Solución inyectable", "Vial 1 mL", "Subcutánea"),
             ("GLARGIFIC 100 UI/mL", "Insulina glargina", "análogo de insulina humana recombinante", "Solución inyectable", "Cartucho 3 mL", "Subcutánea"),
             ("BEVASUR 100 mg/4 mL", "Bevacizumab", "anticuerpo monoclonal humanizado anti-VEGF", "Concentrado para solución", "Vial 4 mL", "Intravenosa"),
             ("SOMATRAL 5 mg", "Somatropina", "hormona de crecimiento humana recombinante", "Polvo liofilizado", "Cartucho 5 mg", "Subcutánea")]
CAMBIOS = [("Cambio en el método analítico para la determinación de potencia biológica del IFA {ifa}, pasando del bioensayo celular al método de citometría de flujo validado según ICH Q2(R1).",
            "Notificación de cambio en método analítico", "citometría de flujo", "potencia biológica"),
           ("Cambio en el método analítico para la determinación de pureza del IFA {ifa}, reemplazando la electroforesis SDS-PAGE por cromatografía de exclusión molecular (SEC-HPLC).",
            "Notificación de cambio en método analítico", "SEC-HPLC", "pureza"),
           ("Cambio en el método analítico de identidad del IFA {ifa}, incorporando mapeo peptídico por LC-MS en reemplazo del isoelectroenfoque.",
            "Notificación de cambio en método analítico", "mapeo peptídico por LC-MS", "identidad"),
           ("Cambio en el método analítico para la determinación de proteínas de célula huésped en el IFA {ifa}, pasando de ELISA comercial a ELISA específico de proceso.",
            "Notificación de cambio en método analítico", "ELISA específico de proceso", "proteínas de célula huésped")]
FIRMAS = [("Dr. Roberto Méndez", "M.N. 45.231"), ("Farm. Laura Giménez", "M.N. 51.876"), ("Dra. Silvia Ferraro", "M.N. 38.402"),
          ("Farm. Martín Acosta", "M.N. 60.115"), ("Bioq. Daniela Ríos", "M.N. 47.990")]
CALIDAD = ["Farm. Ana González", "Lic. Pablo Herrera", "Bioq. Carla Suárez", "Farm. Tomás Ledesma"]
# Textos sin relación regulatoria (inventados para este set, sin derechos de terceros)
AJENOS = [["Bajo la luna de octubre canta el río su canción,", "y el viento lleva en las hojas", "los secretos de mi corazón."],
          ["Estribillo: Baila, baila hasta el amanecer,", "que la noche es corta y no vuelve a volver,", "baila, baila, no dejes de creer."],
          ["Receta de la abuela: tres huevos, una taza de harina,", "media de azúcar y ralladura de limón.", "Hornear cuarenta minutos a fuego moderado."],
          ["El sueldo de los profesionales que trabajan en la ANMAT es altísimo."]]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

ESCENARIOS = [  # (codigo, descripcion, peso, veredicto)
    ("completo_pdf",          "Completo, los 3 documentos en PDF", 7, "VALIDAR"),
    ("completo_escaneado",    "Completo, escaneado (JPG/PNG/TIFF)", 4, "VALIDAR"),
    ("completo_ruidoso",      "Completo, escaneo de baja calidad (rotado/ruido)", 2, "VALIDAR"),
    ("completo_sin_nro_exp",  "Completo, el formulario no consigna N° de expediente", 2, "VALIDAR"),
    ("falta_nota",            "Falta la nota de presentación", 2, "OBJETAR"),
    ("falta_formulario",      "Falta el formulario de solicitud", 2, "OBJETAR"),
    ("falta_declaracion",     "Falta el documento declarado por el regulado", 2, "OBJETAR"),
    ("falta_varios",          "Solo llega un documento", 1, "OBJETAR"),
    ("nota_texto_ajeno",      "Nota con poema/canción en lugar del motivo", 2, "OBJETAR"),
    ("formulario_texto_ajeno","Formulario con texto ajeno en la descripción del cambio", 1, "OBJETAR"),
    ("declaracion_texto_ajeno","Documento del regulado con texto ajeno en el alcance", 1, "OBJETAR"),
    ("documento_ajeno",       "Un documento entero sin relación (poema/receta) en lugar de uno obligatorio", 1, "OBJETAR"),
    ("producto_inconsistente","El producto no coincide entre documentos", 2, "OBJETAR"),
    ("empresa_inconsistente", "La empresa no coincide entre documentos", 2, "OBJETAR"),
    ("formato_no_soportado",  "Un documento obligatorio en .docx", 1, "OBJETAR"),
]


class Doc:
    def __init__(self, path):
        self.c = canvas.Canvas(path, pagesize=A4); self.w, self.h = A4; self.y = self.h - 2.2 * cm
    def nl(self, d=0.55):
        self.y -= d * cm
        if self.y < 2.5 * cm:
            self.c.showPage(); self.y = self.h - 2.2 * cm
    def centro(self, t, size=11, bold=True):
        self.c.setFont("Helvetica-Bold" if bold else "Helvetica", size); self.c.drawCentredString(self.w / 2, self.y, t); self.nl(0.5)
    def derecha(self, t):
        self.c.setFont("Helvetica", 10); self.c.drawRightString(self.w - 2.5 * cm, self.y, t); self.nl()
    def txt(self, t, bold=False, size=10):
        self.c.setFont("Helvetica-Bold" if bold else "Helvetica", size); self.c.drawString(2.5 * cm, self.y, t); self.nl()
    def parrafo(self, t, ancho=95):
        palabras, linea = t.split(), ""
        for p in palabras:
            if len(linea) + len(p) + 1 > ancho:
                self.txt(linea); linea = p
            else:
                linea = (linea + " " + p).strip()
        if linea: self.txt(linea)
    def campo(self, k, v):
        self.c.setFont("Helvetica", 10); self.c.drawString(2.5 * cm, self.y, k); self.c.drawString(9.5 * cm, self.y, v); self.nl(0.7)
    def fin(self):
        self.c.save()


def nota(path, d):
    D = Doc(path)
    D.centro("ADMINISTRACIÓN NACIONAL DE MEDICAMENTOS,"); D.centro("ALIMENTOS Y TECNOLOGÍA MÉDICA — ANMAT"); D.centro("INSTITUTO NACIONAL DE MEDICAMENTOS — INAME"); D.nl()
    D.derecha(f"Buenos Aires, {d['fecha'].day} de {MESES[d['fecha'].month - 1]} de {d['fecha'].year}"); D.nl()
    D.centro("NOTA DE PRESENTACIÓN", 12); D.nl()
    D.txt("Señores"); D.txt("Instituto Nacional de Medicamentos (INAME)"); D.txt("Administración Nacional de Medicamentos, Alimentos y Tecnología Médica (ANMAT)"); D.nl()
    D.parrafo(f"Por medio de la presente, {d['empresa_nota']}, con domicilio legal en {d['domicilio']}, en su carácter de titular del "
              "Registro Sanitario del producto que se detalla a continuación, viene a presentar solicitud de modificación post-registro ante el INAME."); D.nl()
    D.txt("DATOS DEL PRODUCTO:", bold=True)
    D.campo("Nombre Comercial:", d["producto_nota"]); D.campo("IFA (Ingrediente Farmacéutico Activo):", d["ifa"])
    D.campo("Forma Farmacéutica:", d["forma"]); D.campo("Presentación:", d["presentacion"])
    D.campo("Número de Registro Sanitario:", d["registro"]); D.campo("Titular del Registro:", d["empresa_nota"]); D.nl()
    D.txt("MOTIVO DE LA MODIFICACIÓN SOLICITADA:", bold=True)
    if d["ajeno_en"] == "nota":
        for l in d["ajeno"]: D.txt(l)
    else:
        D.parrafo(d["motivo"])
    D.nl()
    D.parrafo("Se adjunta la documentación técnica requerida según normativa vigente, incluyendo el Módulo 3 del CTD con las secciones correspondientes al cambio solicitado.")
    D.nl(); D.txt("Sin otro particular, saluda atentamente."); D.nl(1.2)
    D.txt("_______________________________"); D.txt(d["dt"]); D.txt("Director Técnico"); D.txt(d["empresa_nota"]); D.txt(d["mat"])
    D.fin()


def formulario(path, d):
    D = Doc(path)
    D.centro("INSTITUTO NACIONAL DE MEDICAMENTOS — INAME"); D.centro("FORMULARIO DE SOLICITUD DE MODIFICACIÓN POST-REGISTRO"); D.centro("Productos Biológicos", 10, False); D.nl()
    D.txt("SECCIÓN 1 — DATOS DEL EXPEDIENTE", bold=True)
    if d["exp_en_form"]:
        D.campo("Número de Expediente ANMAT:", d["expediente"])
    D.campo("Fecha de Presentación:", d["fecha"].strftime("%d/%m/%Y")); D.campo("Tipo de Trámite:", "Modificación Post-Registro"); D.campo("Modalidad:", d["modalidad"])
    D.txt("SECCIÓN 2 — DATOS DEL TITULAR", bold=True)
    D.campo("Razón Social:", d["empresa_form"]); D.campo("CUIT:", d["cuit"]); D.campo("Domicilio Legal:", d["domicilio"]); D.campo("Director Técnico:", f"{d['dt']} — {d['mat']}")
    D.txt("SECCIÓN 3 — DATOS DEL PRODUCTO", bold=True)
    D.campo("Nombre Comercial:", d["producto_form"]); D.campo("IFA:", d["ifa"]); D.campo("Forma Farmacéutica:", d["forma"])
    D.campo("Presentación:", d["presentacion"]); D.campo("Vía de Administración:", d["via"]); D.campo("Número de Registro ANMAT:", d["registro"])
    D.txt("SECCIÓN 4 — DESCRIPCIÓN DEL CAMBIO SOLICITADO", bold=True)
    if d["ajeno_en"] == "formulario":
        for l in d["ajeno"]: D.txt(l)
    else:
        D.parrafo(d["motivo"] + " Normativa aplicable: ICH Q2(R1).")
    D.txt("SECCIÓN 5 — DOCUMENTACIÓN ADJUNTA (CTD)", bold=True)
    for l in ["• Módulo 1.0 — Nota de Presentación", "• Módulo 1.2 — Formulario de Solicitud (presente documento)",
              "• Módulo 3.2.S.4.2 — Procedimientos analíticos (método propuesto)", "• Módulo 3.2.S.4.3 — Validación de procedimientos analíticos"]:
        D.txt(l)
    D.txt("Declaro bajo juramento que la información consignada es verdadera."); D.nl(1.2)
    D.txt("_______________________________"); D.txt("Firma y sello del Director Técnico"); D.txt(f"{d['dt']} — {d['mat']}")
    D.fin()


def declaracion(path, d, r):
    D = Doc(path)
    D.centro(d["empresa_decl"].upper()); D.centro("DOCUMENTO DECLARADO POR EL REGULADO"); D.centro("CTD Módulo 3 — Sección 3.2.S.4.3", 10, False)
    D.centro(f"Validación del Método Analítico — {d['atributo'].capitalize()} {d['ifa']}", 10, False); D.nl()
    D.txt("1. ALCANCE", bold=True)
    if d["ajeno_en"] == "declaracion":
        for l in d["ajeno"]: D.txt(l)
    else:
        D.parrafo(f"El presente informe describe la validación del método analítico por {d['metodo']} para la determinación de {d['atributo']} "
                  f"del IFA {d['ifa']} ({d['ifa_desc']}) presente en {d['producto_decl']}, de acuerdo con ICH Q2(R1) y la Farmacopea Argentina.")
    D.nl(); D.txt("2. PARÁMETROS DE VALIDACIÓN", bold=True)
    for k, crit, res in [("Especificidad", "Sin interferencias", "Sin interferencias"), ("Linealidad (R²)", "≥ 0.990", f"0.99{r.randint(3, 9)}"),
                         ("Exactitud (recuperación)", "85 – 115%", f"{r.uniform(94, 104):.1f}%"), ("Precisión (CV%)", "≤ 15%", f"{r.uniform(2, 9):.1f}%"),
                         ("Robustez (CV%)", "≤ 20%", f"{r.uniform(4, 14):.1f}%")]:
        D.c.setFont("Helvetica", 10); D.c.drawString(2.5 * cm, D.y, k); D.c.drawString(8 * cm, D.y, crit); D.c.drawString(12.5 * cm, D.y, res); D.c.drawString(16 * cm, D.y, "SÍ"); D.nl(0.65)
    D.nl(); D.txt("3. CONCLUSIÓN", bold=True)
    D.parrafo(f"El método analítico por {d['metodo']} cumple con todos los parámetros de validación establecidos por ICH Q2(R1) y es apto "
              f"para su implementación en el control de calidad de rutina del producto {d['producto_decl']}.")
    D.nl(); D.campo("Elaborado por:", d["qc"] + " — Jefe/a de Control de Calidad"); D.campo("Revisado por:", d["dt"] + " — Director Técnico")
    D.campo("Fecha:", (d["fecha"] - timedelta(days=3)).strftime("%d/%m/%Y"))
    D.fin()


def ajeno_doc(path, d):
    D = Doc(path); D.nl(2)
    for l in d["ajeno"]: D.txt(l, size=12)
    D.fin()


def a_imagen(pdf_path, base, fmt, ruido, r):
    subprocess.run(["pdftoppm", "-r", "150", "-singlefile", "-png", pdf_path, base + "_tmp"], check=True)
    img = Image.open(base + "_tmp.png").convert("L"); os.remove(base + "_tmp.png")
    if ruido:
        img = img.rotate(r.uniform(-2.5, 2.5), expand=True, fillcolor=255)
        arr = np.array(img).astype(np.int16)
        arr += np.random.default_rng(r.randint(0, 1 << 30)).normal(0, 22, arr.shape).astype(np.int16)
        img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))
        img = ImageEnhance.Contrast(img).enhance(0.75)
    ext = {"JPEG": ".jpg", "PNG": ".png", "TIFF": ".tif"}[fmt]
    img.save(base + ext, fmt, **({"quality": 70} if fmt == "JPEG" else {}))
    os.remove(pdf_path)
    return base + ext


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=60); ap.add_argument("--dev", type=int, default=20)
    ap.add_argument("--seed", type=int, default=2026); ap.add_argument("--out", default="casos")
    a = ap.parse_args(); r = random.Random(a.seed)
    if os.path.exists(a.out): shutil.rmtree(a.out)
    os.makedirs(a.out)
    total = sum(e[2] for e in ESCENARIOS); lista = []
    for cod, _, p, _v in ESCENARIOS: lista += [cod] * round(a.n * p / total)
    while len(lista) < a.n: lista.append("completo_pdf")
    lista = lista[:a.n]; r.shuffle(lista)
    veredicto = {e[0]: e[3] for e in ESCENARIOS}
    particion, por_esc = {}, {}
    for i, cod in enumerate(lista): por_esc.setdefault(cod, []).append(i)
    for cod, idxs in por_esc.items():
        k = max(1, round(len(idxs) * a.dev / a.n)) if len(idxs) > 1 else 0
        for j, i in enumerate(idxs): particion[i] = "DEV" if j < k else "TEST"

    rows = []
    for i, esc in enumerate(lista):
        cid = f"CASO-{i + 1:03d}"; carpeta = os.path.join(a.out, particion[i], cid); os.makedirs(carpeta)
        emp, dom, cuit = r.choice(LABS); prod, ifa, ifa_desc, forma, pres, via = r.choice(PRODUCTOS)
        motivo, modalidad, metodo, atributo = r.choice(CAMBIOS); dt, mat = r.choice(FIRMAS)
        d = dict(domicilio=dom, cuit=cuit, ifa=ifa, ifa_desc=ifa_desc, forma=forma, presentacion=pres, via=via,
                 motivo=motivo.format(ifa=ifa), modalidad=modalidad, metodo=metodo, atributo=atributo, dt=dt, mat=mat, qc=r.choice(CALIDAD),
                 registro=f"1-47-{r.randint(1995, 2024)}-{r.randint(1000, 999999):06d}-{r.randint(20, 26)}-{r.randint(1, 9)}",
                 fecha=date(2026, 3, 1) + timedelta(days=r.randint(0, 200)), exp_en_form=True, ajeno_en="", ajeno=r.choice(AJENOS))
        d["expediente"] = f"1-0047-2002-{r.randint(100, 999999):06d}-{r.randint(24, 26)}-{r.randint(1, 9)}"
        for k in ("nota", "form", "decl"): d["empresa_" + k] = emp; d["producto_" + k] = prod
        if esc == "producto_inconsistente":
            d["producto_" + r.choice(["nota", "form", "decl"])] = r.choice([p[0] for p in PRODUCTOS if p[0] != prod])
        if esc == "empresa_inconsistente":
            d["empresa_" + r.choice(["nota", "form", "decl"])] = r.choice([l[0] for l in LABS if l[0] != emp])
        if esc == "completo_sin_nro_exp": d["exp_en_form"] = False
        if esc.endswith("_texto_ajeno"): d["ajeno_en"] = esc.split("_")[0]

        incluir = ["nota", "formulario", "declaracion"]
        faltan = {"falta_nota": ["nota"], "falta_formulario": ["formulario"], "falta_declaracion": ["declaracion"]}.get(esc, [])
        if esc == "falta_varios": faltan = r.sample(incluir, 2)
        if esc == "documento_ajeno": faltan = [r.choice(incluir)]
        incluir = [x for x in incluir if x not in faltan]
        if esc == "documento_ajeno": incluir.append("ajeno")
        r.shuffle(incluir)
        no_soportado = r.choice(incluir) if esc == "formato_no_soportado" else None
        archivos = []
        for nd, tipo in enumerate(incluir, 1):
            base = os.path.join(carpeta, f"{cid}_doc{nd:02d}"); p = base + ".pdf"
            {"nota": lambda: nota(p, d), "formulario": lambda: formulario(p, d),
             "declaracion": lambda: declaracion(p, d, r), "ajeno": lambda: ajeno_doc(p, d)}[tipo]()
            dest = p
            if esc in ("completo_escaneado", "completo_ruidoso"):
                dest = a_imagen(p, base, r.choice(["JPEG", "PNG", "TIFF"]), esc == "completo_ruidoso", r)
            if tipo == no_soportado:
                os.rename(p, base + ".docx"); dest = base + ".docx"
            archivos.append(f"{os.path.basename(dest)}={tipo}")
        nombres = {"nota": "Nota de presentación", "formulario": "Formulario de solicitud", "declaracion": "Documento declarado por el regulado"}
        falt = [nombres[x] for x in faltan] + ([nombres[no_soportado] + " (formato no admitido)"] if no_soportado else [])
        exp_ok = d["exp_en_form"] and "formulario" in incluir and no_soportado != "formulario"
        rows.append({"caso": cid, "particion": particion[i], "escenario": esc, "veredicto_esperado": veredicto[esc],
                     "faltantes_esperados": "; ".join(falt),
                     "problema_esperado": {"producto_inconsistente": "producto no coincide", "empresa_inconsistente": "empresa no coincide",
                                           "nota_texto_ajeno": "motivo sin datos", "formulario_texto_ajeno": "descripción sin datos",
                                           "declaracion_texto_ajeno": "alcance sin datos", "documento_ajeno": "documento no reconocido"}.get(esc, ""),
                     "expediente_esperado": d["expediente"] if exp_ok else "NO IDENTIFICADO",
                     "producto_esperado": prod, "empresa_esperada": emp, "ifa_esperado": ifa, "archivos": "; ".join(archivos)})

    with open(os.path.join(a.out, "ground_truth.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    h = hashlib.sha256(open(os.path.join(a.out, "ground_truth.csv"), "rb").read()).hexdigest()
    json.dump({"seed": a.seed, "n": a.n, "dev": sum(x["particion"] == "DEV" for x in rows), "test": sum(x["particion"] == "TEST" for x in rows),
               "ground_truth_sha256": h, "escenarios": {e[0]: f"{e[1]} -> {e[3]}" for e in ESCENARIOS}},
              open(os.path.join(a.out, "manifest.json"), "w"), ensure_ascii=False, indent=2)
    print(f"{len(rows)} casos. sha256 referencia: {h}")


if __name__ == "__main__":
    main()
