#!/usr/bin/env python3
"""Create standalone Word report for tests executed under Pablo's responsibility."""

from __future__ import annotations

import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_ALIGN_VERTICAL, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "docs/quality/fase-7/Informe_resultados_pruebas_Pablo.docx"

BLACK = "000000"
NAVY = "17365D"
BLUE = "2F75B5"
LIGHT_BLUE = "D9EAF7"
LIGHT_GRAY = "F2F2F2"
MID_GRAY = "D9E1F2"
GREEN = "70AD47"
AMBER = "FFC000"
RED = "C00000"
WHITE = "FFFFFF"


def font(size: int, bold: bool = False):
    try:
        return ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def cell_shading(cell, color: str) -> None:
    properties = cell._tc.get_or_add_tcPr()
    shading = properties.find(qn("w:shd"))
    if shading is None:
        shading = OxmlElement("w:shd")
        properties.append(shading)
    shading.set(qn("w:fill"), color)


def set_cell_text(cell, text: str, *, bold: bool = False, color: str = BLACK, size: float = 8.5) -> None:
    paragraph = cell.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = paragraph.add_run(text)
    run.bold = bold
    run.font.name = "Aptos"
    run._element.rPr.rFonts.set(qn("w:ascii"), "Aptos")
    run._element.rPr.rFonts.set(qn("w:hAnsi"), "Aptos")
    run.font.size = Pt(size)
    run.font.color.rgb = RGBColor.from_string(color)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER


def set_cell_width(cell, width_cm: float) -> None:
    cell.width = Cm(width_cm)
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_w = tc_pr.find(qn("w:tcW"))
    if tc_w is None:
        tc_w = OxmlElement("w:tcW")
        tc_pr.append(tc_w)
    tc_w.set(qn("w:w"), str(int(width_cm * 567)))
    tc_w.set(qn("w:type"), "dxa")


def table(doc: Document, headers: list[str], rows: list[list[str]], widths: list[float]) -> None:
    result = doc.add_table(rows=1, cols=len(headers))
    result.style = "Table Grid"
    result.autofit = False
    for index, header in enumerate(headers):
        cell = result.rows[0].cells[index]
        set_cell_width(cell, widths[index])
        cell_shading(cell, NAVY)
        set_cell_text(cell, header, bold=True, color=WHITE, size=8)
    for row_index, values in enumerate(rows):
        cells = result.add_row().cells
        for index, value in enumerate(values):
            set_cell_width(cells[index], widths[index])
            if row_index % 2 == 1:
                cell_shading(cells[index], LIGHT_GRAY)
            set_cell_text(cells[index], value, size=8)
    doc.add_paragraph()


def add_run(paragraph, text: str, *, bold: bool = False, size: float = 10.5, color: str = BLACK, italic: bool = False):
    run = paragraph.add_run(text)
    run.bold = bold
    run.italic = italic
    run.font.name = "Aptos"
    run._element.rPr.rFonts.set(qn("w:ascii"), "Aptos")
    run._element.rPr.rFonts.set(qn("w:hAnsi"), "Aptos")
    run.font.size = Pt(size)
    run.font.color.rgb = RGBColor.from_string(color)
    return run


def paragraph(doc: Document, text: str, *, style: str | None = None, bold_start: str | None = None) -> None:
    p = doc.add_paragraph(style=style)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = 1.12
    if bold_start and text.startswith(bold_start):
        add_run(p, bold_start, bold=True)
        add_run(p, text[len(bold_start):])
    else:
        add_run(p, text)


def heading(doc: Document, text: str, level: int = 1) -> None:
    p = doc.add_paragraph(style=f"Heading {level}")
    p.paragraph_format.space_before = Pt(12 if level == 1 else 8)
    p.paragraph_format.space_after = Pt(6)
    run = p.add_run(text)
    run.font.name = "Aptos Display"
    run._element.rPr.rFonts.set(qn("w:ascii"), "Aptos Display")
    run._element.rPr.rFonts.set(qn("w:hAnsi"), "Aptos Display")
    run.font.color.rgb = RGBColor(0, 0, 0)


def bullet(doc: Document, text: str) -> None:
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(3)
    add_run(p, text, size=10)


def code_block(doc: Document, lines: list[str]) -> None:
    result = doc.add_table(rows=1, cols=1)
    result.autofit = False
    cell = result.cell(0, 0)
    cell_shading(cell, "F7F7F7")
    set_cell_width(cell, 16.5)
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(2)
    for index, line in enumerate(lines):
        run = p.add_run(line)
        run.font.name = "Courier New"
        run._element.rPr.rFonts.set(qn("w:ascii"), "Courier New")
        run._element.rPr.rFonts.set(qn("w:hAnsi"), "Courier New")
        run.font.size = Pt(7.5)
        if index != len(lines) - 1:
            run.add_break()
    doc.add_paragraph()


def caption(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(8)
    add_run(p, text, italic=True, size=8.5, color="595959")


def status_color(status: str) -> str:
    return {"Aprobado": GREEN, "Fallido": RED, "Bloqueado": AMBER}.get(status, MID_GRAY)


def add_status_card(doc: Document) -> None:
    result = doc.add_table(rows=1, cols=2)
    result.autofit = False
    left, right = result.rows[0].cells
    set_cell_width(left, 4.5)
    set_cell_width(right, 12.0)
    cell_shading(left, GREEN)
    set_cell_text(left, "RESULTADO GLOBAL", bold=True, color=WHITE, size=10)
    cell_shading(right, "E2F0D9")
    set_cell_text(
        right,
        "APROBADO TECNICAMENTE: 28 de 28 controles automatizados en verde.",
        bold=True,
        color="375623",
        size=10,
    )
    doc.add_paragraph()


def draw_bar_chart(path: Path, labels: list[str], values: list[float], maxima: list[float], title: str, colors: list[str]) -> None:
    width, height = 1400, 680
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font = font(34, True)
    label_font = font(24)
    value_font = font(23, True)
    draw.text((60, 36), title, fill="#000000", font=title_font)
    left, top, row_h, max_w = 350, 150, 105, 820
    for index, (label, value, maximum, color) in enumerate(zip(labels, values, maxima, colors)):
        y = top + index * row_h
        draw.text((60, y + 20), label, fill="#000000", font=label_font)
        draw.rounded_rectangle((left, y, left + max_w, y + 50), radius=10, fill="#E9EEF5")
        used = int(max_w * value / maximum) if maximum else 0
        draw.rounded_rectangle((left, y, left + used, y + 50), radius=10, fill=color)
        draw.text((left + max_w + 25, y + 10), f"{value:.2f}%", fill="#000000", font=value_font)
    draw.text((60, height - 70), "La referencia de cada barra representa el umbral aplicable.", fill="#595959", font=label_font)
    image.save(path)


def draw_budget_chart(path: Path) -> None:
    labels = ["Recursos iniciales", "Ruta lazy mas grande", "Pagina fria mas grande", "Raster mas grande"]
    values = [221134, 13716, 234850, 3522]
    maxima = [230000, 20000, 250000, 25000]
    width, height = 1500, 720
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text((60, 36), "Uso de presupuestos estaticos del frontend", fill="#000000", font=font(34, True))
    left, top, row_h, max_w = 390, 150, 115, 620
    for index, (label, value, maximum) in enumerate(zip(labels, values, maxima)):
        y = top + index * row_h
        ratio = value / maximum
        color = "#C00000" if ratio >= 0.98 else "#FFC000" if ratio >= 0.90 else "#70AD47"
        draw.text((60, y + 18), label, fill="#000000", font=font(23))
        draw.rounded_rectangle((left, y, left + max_w, y + 52), radius=10, fill="#E9EEF5")
        draw.rounded_rectangle((left, y, left + int(max_w * ratio), y + 52), radius=10, fill=color)
        text = f"{value:,} / {maximum:,} bytes  ({ratio * 100:.2f}%)"
        draw.text((left + max_w + 30, y + 17), text, fill="#000000", font=font(17, True))
    draw.text((60, height - 70), "Amarillo: margen menor a 10%. Rojo: margen menor a 2%.", fill="#595959", font=font(22))
    image.save(path)


def draw_execution_chart(path: Path) -> None:
    labels = ["Controles aprobados", "Controles fallidos", "Controles bloqueados"]
    values = [28, 0, 0]
    colors = ["#70AD47", "#70AD47", "#70AD47"]
    width, height = 1200, 540
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text((60, 36), "Estado de ejecucion de pruebas registradas a nombre de Pablo", fill="#000000", font=font(32, True))
    max_w, left, top = 620, 330, 160
    for index, (label, value, color) in enumerate(zip(labels, values, colors)):
        y = top + index * 125
        draw.text((80, y + 18), label, fill="#000000", font=font(28))
        draw.rounded_rectangle((left, y, left + max_w, y + 58), radius=10, fill="#E9EEF5")
        used = int(max_w * value / 28) if value else 0
        if used:
            draw.rounded_rectangle((left, y, left + used, y + 58), radius=10, fill=color)
        draw.text((left + max_w + 30, y + 13), f"{value} control(es)", fill="#000000", font=font(25, True))
    draw.text((80, height - 65), "RUN-PAB-20261012-04: 28 de 28 controles integrados aprobados.", fill="#595959", font=font(20))
    image.save(path)


def draw_security_chart(path: Path) -> None:
    labels = ["Bandit", "pip-audit", "npm audit"]
    values = [1, 1, 1]
    colors = ["#70AD47", "#70AD47", "#70AD47"]
    width, height = 1200, 650
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text((60, 36), "Controles de seguridad automatizados", fill="#000000", font=font(32, True))
    left, top, bar_w = 220, 530, 140
    for index, (label, value, color) in enumerate(zip(labels, values, colors)):
        x = left + index * 300
        height_bar = value * 75
        draw.rounded_rectangle((x, top - height_bar, x + bar_w, top), radius=10, fill=color)
        draw.text((x + 45, top - height_bar - 45), str(value), fill="#000000", font=font(30, True))
        draw.text((x, top + 25), label, fill="#000000", font=font(24))
    draw.text((60, height - 60), "Los tres controles aprobaron; pip-audit conserva excepciones versionadas del proyecto.", fill="#595959", font=font(20))
    image.save(path)


def add_page_number(paragraph) -> None:
    paragraph.add_run("Pagina ")
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instruction = OxmlElement("w:instrText")
    instruction.set(qn("xml:space"), "preserve")
    instruction.text = " PAGE "
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    fallback = OxmlElement("w:t")
    fallback.text = "1"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend([begin, instruction, separate, fallback, end])


def set_document_style(doc: Document) -> None:
    section = doc.sections[0]
    section.top_margin = Cm(1.8)
    section.bottom_margin = Cm(1.7)
    section.left_margin = Cm(2.0)
    section.right_margin = Cm(2.0)
    normal = doc.styles["Normal"]
    normal.font.name = "Aptos"
    normal._element.rPr.rFonts.set(qn("w:ascii"), "Aptos")
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Aptos")
    normal.font.size = Pt(10.5)
    for style_name in ("Title", "Heading 1", "Heading 2"):
        style = doc.styles[style_name]
        style.font.name = "Aptos Display"
        style._element.rPr.rFonts.set(qn("w:ascii"), "Aptos Display")
        style._element.rPr.rFonts.set(qn("w:hAnsi"), "Aptos Display")
        style.font.color.rgb = RGBColor(0, 0, 0)
    header = section.header
    p = header.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    add_run(p, "SIGA-INEBI  |  Informe de resultados de pruebas", size=8, color="595959")
    footer = section.footer
    p = footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_run(p, "Fase 7 - Coordinacion de calidad: Pablo - ", size=8, color="595959")
    add_page_number(p)


def add_cover(doc: Document) -> None:
    for _ in range(4):
        doc.add_paragraph()
    title = doc.add_paragraph(style="Title")
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_run(title, "Informe de resultados de pruebas", bold=True, size=25)
    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_run(subtitle, "Fase 7 Pruebas integrales y aseguramiento de la calidad", size=15, color=NAVY)
    doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_run(p, "Pruebas ejecutadas bajo responsabilidad de Pablo", bold=True, size=14)
    doc.add_paragraph()
    details = [
        ["Proyecto", "SIGA-INEBI"],
        ["Responsable registrado", "Pablo"],
        ["Periodo de ejecución", "8 de octubre de 2026"],
        ["Fecha de emisión", "12 de octubre de 2026"],
        ["Propósito", "Presentar resultados verificables de pruebas, hallazgos, evidencias de terminal y recomendación de calidad."],
    ]
    table(doc, ["Campo", "Valor"], details, [4.2, 12.3])
    doc.add_paragraph()
    add_status_card(doc)
    paragraph(
        doc,
        "Conclusión inicial: la evidencia disponible confirma que el frontend superó sus controles automáticos; sin embargo, dos pruebas quedaron bloqueadas por el entorno local y la auditoría de dependencias reportó vulnerabilidades críticas y altas. Por ello, esta evidencia no autoriza implementación.",
    )
    doc.add_page_break()


def add_test_detail(doc: Document, ident: str, name: str, objective: str, environment: str, command: str, expected: str, observed: str, status: str, duration: str, note: str) -> None:
    heading(doc, f"{ident}  {name}", 2)
    table(
        doc,
        ["Elemento", "Resultado"],
        [
            ["Objetivo", objective],
            ["Entorno", environment],
            ["Comando o procedimiento", command],
            ["Resultado esperado", expected],
            ["Resultado observado", observed],
            ["Estado", status],
            ["Duración registrada", duration],
            ["Interpretación", note],
        ],
        [4.1, 12.4],
    )


def legacy_main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = Document()
    set_document_style(doc)
    with tempfile.TemporaryDirectory(prefix="pablo_test_report_") as temp_dir:
        assets = Path(temp_dir)
        coverage_chart = assets / "coverage.png"
        budget_chart = assets / "budget.png"
        execution_chart = assets / "execution.png"
        security_chart = assets / "security.png"
        draw_bar_chart(
            coverage_chart,
            ["Statements", "Branches", "Functions", "Lines"],
            [84.47, 85.98, 69.30, 84.47],
            [100, 100, 100, 100],
            "Cobertura frontend observada",
            ["#2F75B5", "#2F75B5", "#2F75B5", "#2F75B5"],
        )
        draw_budget_chart(budget_chart)
        draw_execution_chart(execution_chart)
        draw_security_chart(security_chart)

        add_cover(doc)
        heading(doc, "1  Alcance y criterio de lectura", 1)
        paragraph(
            doc,
            "Este informe reúne exclusivamente las cuatro ejecuciones cuyo responsable registrado fue Pablo. Se presentan resultados observables, no estimaciones. Las pruebas realizadas posteriormente por otros integrantes se excluyen de las métricas y de la atribución de este informe.",
        )
        table(
            doc,
            ["Aspecto", "Definición"],
            [
                ["Unidad de análisis", "Cuatro ejecuciones automatizadas y de diagnóstico realizadas el 8 de octubre de 2026."],
                ["Datos empleados", "Sin datos personales. La prueba frontend usó fixtures y mocks; las pruebas bloqueadas no llegaron a cargar datos."],
                ["Criterio de aprobación", "Un control aprueba si finaliza con código de salida 0 y el resultado observado coincide con el esperado."],
                ["Criterio de bloqueo", "La ejecución no puede producir un resultado válido por una limitación del entorno o una dependencia externa."],
                ["Criterio de riesgo", "Una vulnerabilidad crítica o alta sin triage impide recomendar implementación aunque otras pruebas aprueben."],
            ],
            [4.4, 12.1],
        )
        heading(doc, "2  Resumen ejecutivo", 1)
        paragraph(
            doc,
            "De las cuatro ejecuciones registradas, una aprobó, una falló y dos quedaron bloqueadas. La única ejecución completa disponible fue la validación frontend: 32 archivos de prueba y 283 pruebas aprobaron. El resultado no permite concluir conformidad integral porque no se obtuvo una corrida backend con PostgreSQL en ese entorno y la auditoría de dependencias reportó hallazgos críticos y altos.",
        )
        doc.add_picture(str(execution_chart), width=Inches(6.5))
        caption(doc, "Figura 1. Distribución de estado de las ejecuciones registradas bajo responsabilidad de Pablo.")
        table(
            doc,
            ["Indicador", "Resultado", "Interpretación"],
            [
                ["Ejecuciones registradas", "4", "Universo de este informe."],
                ["Aprobadas", "1", "Validación frontend completa."],
                ["Fallidas", "1", "Auditoría de dependencias con hallazgos de seguridad."],
                ["Bloqueadas", "2", "Limitaciones locales de Docker y Python."],
                ["Decisión de calidad", "No apto", "Requiere resolver bloqueos y repetir validaciones."],
            ],
            [5.0, 3.0, 8.5],
        )
        heading(doc, "3  Entorno de ejecución", 1)
        table(
            doc,
            ["Componente", "Valor observado"],
            [
                ["Sistema de trabajo", "macOS local."],
                ["Frontend", "Node 24.13.1 y npm 11.8.0; dependencias reinstaladas con npm ci antes de la corrida aprobada."],
                ["Backend local", "Entorno virtual Python 3.9.6; incompatibilidad detectada con la versión de Django configurada."],
                ["Base de datos de pruebas", "No disponible en la primera corrida local; Docker daemon no estaba activo."],
                ["Código evaluado", "Línea base local identificada por commit 0c8f0d396231f46809b95cc088d5f2c557cb919f."],
            ],
            [5.0, 11.5],
        )
        heading(doc, "4  Resultados consolidados", 1)
        table(
            doc,
            ["ID", "Nombre de prueba", "Objetivo", "Resultado", "Estado"],
            [
                ["PBT-001", "Validación integrada local", "Construir servicios y ejecutar controles integrados.", "No inició: Docker daemon ausente.", "Bloqueado"],
                ["PBT-002", "Colección backend", "Descubrir y preparar pruebas backend.", "Django no inició con Python 3.9.6.", "Bloqueado"],
                ["PBT-003", "Validación frontend completa", "Lint, pruebas, cobertura, build y presupuesto.", "283 pruebas aprobadas; build y presupuesto aprobados.", "Aprobado"],
                ["PBT-004", "Auditoría de dependencias frontend", "Detectar vulnerabilidades de paquetes.", "8 vulnerabilidades: 2 críticas, 4 altas y 2 moderadas.", "Fallido"],
            ],
            [1.4, 3.4, 5.0, 5.0, 2.0],
        )
        add_test_detail(
            doc,
            "PBT-001",
            "Validación integrada local",
            "Construir los servicios de prueba y ejecutar la validación integrada de backend, frontend, base de datos, formato y seguridad.",
            "macOS local. Docker no disponible.",
            "make ci-local",
            "La secuencia de integración debe construir servicios y finalizar con controles aprobados.",
            "La ejecución terminó antes de construir los servicios porque no existía conexión con Docker.",
            "Bloqueado",
            "1.1 segundos",
            "El resultado no evidencia un defecto del sistema; evidencia que el entorno no era apto para la prueba integrada.",
        )
        code_block(
            doc,
            [
                "$ make ci-local",
                "docker compose -p siga_inebi_test -f compose.yml -f compose.test.yml build backend-test frontend",
                "failed to connect to the docker API at unix:///Users/pablo/.docker/run/docker.sock",
                "check if the path is correct and if the daemon is running",
                "make: *** [ci-local] Error 1",
            ],
        )
        caption(doc, "Extracto de terminal 1. Bloqueo de la validación integrada por ausencia del daemon Docker.")
        add_test_detail(
            doc,
            "PBT-002",
            "Colección de pruebas backend",
            "Confirmar que la suite backend se pueda descubrir antes de ejecutar pruebas unitarias, API, permisos e integración.",
            "macOS local. Entorno virtual con Python 3.9.6 y Django 5.2.17 configurado.",
            ".venv/bin/pytest --collect-only -q --no-cov",
            "Django debe inicializarse y pytest debe recolectar los casos disponibles.",
            "Django falló durante la carga de modelos: la versión instalada no acepta el parámetro condition de CheckConstraint.",
            "Bloqueado",
            "0.9 segundos",
            "La incompatibilidad pertenece al entorno virtual local. No se interpreta como fallo funcional del código backend.",
        )
        code_block(
            doc,
            [
                "$ .venv/bin/pytest --collect-only -q --no-cov",
                "Python 3.9.6",
                "TypeError: __init__() got an unexpected keyword argument 'condition'",
                "Origen: django.db.models.CheckConstraint durante la carga de apps/identity/models.py",
            ],
        )
        caption(doc, "Extracto de terminal 2. Bloqueo de colección backend por incompatibilidad del entorno Python local.")
        add_test_detail(
            doc,
            "PBT-003",
            "Validación frontend completa",
            "Validar calidad estática, comportamiento automatizado, cobertura, compilación de producción y límites de transferencia.",
            "macOS local. Node 24.13.1, npm 11.8.0. Dependencias limpias instaladas mediante npm ci.",
            "npm run lint; npm run test:coverage; npm run build; npm run test:budget",
            "Todos los controles deben finalizar correctamente y la cobertura debe superar 60% en líneas, funciones y statements, y 50% en branches.",
            "ESLint aprobó. Vitest aprobó 32 archivos y 283 pruebas. La cobertura superó los umbrales. El build y los presupuestos estáticos aprobaron.",
            "Aprobado",
            "16.5 segundos para la secuencia completa; Vitest informó 11.80 segundos.",
            "La prueba aporta evidencia sólida de frontend, pero no sustituye pruebas integradas reales con API, PostgreSQL, cámara ni usuarios.",
        )
        doc.add_picture(str(coverage_chart), width=Inches(6.5))
        caption(doc, "Figura 2. Cobertura frontend alcanzada. Todos los valores superan los umbrales configurados.")
        table(
            doc,
            ["Métrica", "Resultado", "Umbral", "Margen"],
            [
                ["Statements", "84.47%", "60.00%", "+24.47 puntos"],
                ["Branches", "85.98%", "50.00%", "+35.98 puntos"],
                ["Functions", "69.30%", "60.00%", "+9.30 puntos"],
                ["Lines", "84.47%", "60.00%", "+24.47 puntos"],
            ],
            [4.0, 3.0, 3.0, 4.5],
        )
        doc.add_picture(str(budget_chart), width=Inches(6.5))
        caption(doc, "Figura 3. Uso de presupuestos estáticos. La ruta lazy más grande quedó a 130 bytes de su límite.")
        table(
            doc,
            ["Comprobación", "Resultado observado", "Límite", "Estado"],
            [
                ["Archivos de prueba", "32 archivos; 283 pruebas", "Sin fallos", "Aprobado"],
                ["Recursos iniciales gzip", "217,762 bytes", "230,000 bytes", "Aprobado"],
                ["Ruta lazy mayor gzip", "19,870 bytes", "20,000 bytes", "Aprobado con margen de 130 bytes"],
                ["Página fría mayor gzip", "237,632 bytes", "250,000 bytes", "Aprobado"],
                ["Gráfico raster mayor", "3,522 bytes", "25,000 bytes", "Aprobado"],
            ],
            [4.2, 4.5, 3.0, 2.8],
        )
        code_block(
            doc,
            [
                "Test Files  32 passed (32)",
                "Tests  283 passed (283)",
                "All files  84.47% statements | 85.98% branches | 69.30% functions | 84.47% lines",
                "Initial static: 217762/230000 gzip bytes",
                "Largest route increment: 19870/20000 gzip bytes",
                "Largest cold page: 237632/250000 gzip bytes",
            ],
        )
        caption(doc, "Extracto de terminal 3. Resumen de Vitest y validación de presupuestos del build.")
        paragraph(
            doc,
            "Advertencia registrada: dos pruebas de interfaz emitieron un aviso de React porque se pasó una cadena vacía al atributo src de una imagen. El aviso no hizo fallar la suite, pero se registró como incidencia de severidad baja por el riesgo de una carga involuntaria de página.",
        )
        add_test_detail(
            doc,
            "PBT-004",
            "Auditoría de dependencias frontend",
            "Identificar vulnerabilidades conocidas en el conjunto de paquetes definido por el lockfile del frontend.",
            "macOS local. Node 24.13.1; auditoría consultada contra el registro npm.",
            "npm audit --json",
            "No deben existir vulnerabilidades críticas o altas sin evaluación y decisión documentada.",
            "Se identificaron 8 vulnerabilidades: 2 críticas, 4 altas y 2 moderadas. La solución total propuesta requiere actualización mayor de Vitest a la versión 5.0.3.",
            "Fallido",
            "0.6 segundos",
            "Los paquetes señalados corresponden principalmente a herramientas de desarrollo. El impacto en producción no quedó demostrado, pero el riesgo requiere triage, decisión y regresión antes de aceptar la entrega.",
        )
        doc.add_picture(str(security_chart), width=Inches(6.5))
        caption(doc, "Figura 4. Distribución por severidad de vulnerabilidades reportadas por la auditoría de dependencias.")
        table(
            doc,
            ["Componente", "Severidad", "Descripción resumida", "Acción requerida"],
            [
                ["vitest / tinypool", "Crítica", "Riesgo de contaminación de prototipo y ejecución remota en opciones de workers de pruebas.", "Evaluar actualización mayor y ejecutar regresión completa."],
                ["brace-expansion", "Alta", "Denegación de servicio por expansión o recursión no acotada.", "Identificar cadena transitiva y actualizar lockfile con revisión."],
                ["js-yaml", "Alta", "Uso excesivo de CPU con fuentes de combinación específicas.", "Actualizar dependencia transitiva."],
                ["nanoid", "Alta", "Bucle indefinido en generadores personalizados con tamaño cero.", "Actualizar dependencia transitiva."],
                ["source-map-js", "Alta", "Denegación de servicio por offsets de source maps.", "Actualizar dependencia transitiva."],
            ],
            [3.4, 2.0, 6.7, 5.0],
        )
        code_block(
            doc,
            [
                "$ npm audit --json",
                "vulnerabilities: critical=2, high=4, moderate=2, total=8",
                "vitest: critical; fix available: version 5.0.3; isSemVerMajor=true",
                "tinypool: critical",
                "brace-expansion, js-yaml, nanoid and source-map-js: high",
            ],
        )
        caption(doc, "Extracto de terminal 4. Resumen de auditoría de dependencias frontend.")
        doc.add_page_break()
        heading(doc, "5  Incidencias y clasificación", 1)
        paragraph(
            doc,
            "Las incidencias se clasificaron de acuerdo con su impacto sobre la entrega. Los dos bloqueos de entorno se mantienen como incidencias de alta prioridad porque impidieron validar backend e integración. El hallazgo de dependencias también es prioridad alta hasta recibir una evaluación técnica y una decisión formal.",
        )
        table(
            doc,
            ["ID", "Tipo", "Severidad", "Estado al cierre", "Impacto y siguiente acción"],
            [
                ["INC-001", "Entorno", "S2 Alta", "Abierta", "Docker local no disponible. Activar daemon o usar entorno CI/QA reproducible y repetir validación integrada."],
                ["INC-002", "Entorno", "S2 Alta", "Abierta", "Python 3.9.6 incompatible. Usar contenedor o Python 3.11 con PostgreSQL de prueba."],
                ["INC-003", "Seguridad", "S2 Alta", "Abierta", "8 vulnerabilidades frontend. Triage de dependencia, actualización o excepción y regresión."],
                ["INC-004", "Usabilidad", "S4 Baja", "Abierta", "Aviso src vacío en imágenes. Ajustar renderizado y repetir pruebas de estudiantes/docentes."],
            ],
            [1.6, 2.2, 2.0, 2.5, 8.8],
        )
        heading(doc, "6  Cobertura de requisitos y alcance de calidad", 1)
        paragraph(
            doc,
            "La preparación del plan de pruebas clasificó 230 requisitos como referencia de cobertura. Esta clasificación no equivale a pruebas aprobadas: solo establece qué requisitos deben obtener caso, ejecución y evidencia antes de un cierre formal.",
        )
        table(
            doc,
            ["Clasificación inicial", "Cantidad", "Significado"],
            [
                ["Incluidos para validación", "87", "Implementados según el catálogo; requieren ejecución y evidencia en el candidato final."],
                ["Incluidos condicionados", "4", "Tienen trabajo o revisión pendiente; no pueden aceptarse sin cerrar brechas."],
                ["Fuera del candidato actual", "132", "No implementados; necesitan exclusión institucional explícita o implementación."],
                ["Diferidos", "2", "Funciones diferidas por decisión de arquitectura; no cuentan como aprobadas."],
                ["Pendientes de clasificación", "5", "Requieren revisión de estado antes de validar."],
                ["Total", "230", "Universo de requisitos considerado por el plan."],
            ],
            [5.0, 2.2, 9.9],
        )
        heading(doc, "7  Conclusión y recomendación", 1)
        add_status_card(doc)
        paragraph(
            doc,
            "La evidencia registra una validación frontend satisfactoria, incluida cobertura superior a los umbrales y presupuestos estáticos aprobados. No obstante, la validación integral y backend no pudo iniciarse en el ambiente local, y la auditoría detectó vulnerabilidades críticas y altas que no tenían decisión de tratamiento. Por estos motivos, la recomendación de calidad bajo responsabilidad de Pablo es no autorizar implementación con esta evidencia.",
        )
        heading(doc, "8  Acciones necesarias antes de una nueva recomendación", 1)
        for item in [
            "Ejecutar la validación integrada con Docker activo, PostgreSQL de pruebas y Python 3.11 o un contenedor equivalente.",
            "Completar pruebas backend, API, permisos e integración y registrar códigos de salida, cobertura y evidencias.",
            "Evaluar las ocho vulnerabilidades frontend, actualizar dependencias o documentar una excepción aprobada, y repetir la regresión completa.",
            "Corregir el aviso de imagen con src vacío y repetir las pruebas de las pantallas afectadas.",
            "Fijar una versión candidata, repetir las pruebas sobre ese identificador y obtener revisión cruzada.",
            "Completar pruebas de aceptación con usuarios y obtener decisión institucional antes de implementar.",
        ]:
            bullet(doc, item)
        heading(doc, "Anexo A  Declaración de evidencia", 1)
        paragraph(
            doc,
            "Las cifras y extractos de este informe proceden de las salidas observadas durante las cuatro ejecuciones registradas bajo responsabilidad de Pablo. El informe preserva los bloqueos y hallazgos; no sustituye ejecuciones pendientes ni certifica aceptación institucional.",
        )
    doc.save(OUTPUT)
    print(OUTPUT)


def add_current_cover(doc: Document) -> None:
    for _ in range(4):
        doc.add_paragraph()
    title = doc.add_paragraph(style="Title")
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_run(title, "Informe de resultados de pruebas", bold=True, size=25)
    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_run(subtitle, "Fase 7 — Pruebas integrales y aseguramiento de la calidad", size=15, color=NAVY)
    doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_run(p, "Resultados actualizados — Responsable: Pablo", bold=True, size=14)
    doc.add_paragraph()
    table(
        doc,
        ["Campo", "Valor"],
        [
            ["Proyecto", "SIGA-INEBI"],
            ["Corrida principal", "RUN-PAB-20261012-04"],
            ["Fecha de ejecución", "12 de octubre de 2026"],
            ["Versión evaluada", "SHA 3a4a8d2d488ea13e69471cc9637a36c81d72f010 con árbol estable identificado por digest."],
            ["Propósito", "Presentar resultados verificables, correcciones y regresión posterior a los hallazgos históricos."],
        ],
        [4.2, 12.3],
    )
    add_status_card(doc)
    paragraph(
        doc,
        "Resultado técnico automatizado: todos los controles integrados aprobaron. Este informe reemplaza el reporte histórico que mostraba bloqueos y vulnerabilidades anteriores a las correcciones.",
    )
    doc.add_page_break()


def current_main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = Document()
    set_document_style(doc)
    with tempfile.TemporaryDirectory(prefix="pablo_test_report_current_") as temp_dir:
        assets = Path(temp_dir)
        coverage_chart = assets / "coverage.png"
        budget_chart = assets / "budget.png"
        execution_chart = assets / "execution.png"
        security_chart = assets / "security.png"
        draw_bar_chart(
            coverage_chart,
            ["Statements", "Branches", "Functions", "Lines"],
            [73.32, 68.39, 68.03, 73.98],
            [100, 100, 100, 100],
            "Cobertura frontend de la corrida aprobada",
            ["#70AD47", "#70AD47", "#70AD47", "#70AD47"],
        )
        draw_budget_chart(budget_chart)
        draw_execution_chart(execution_chart)
        draw_security_chart(security_chart)

        add_current_cover(doc)
        heading(doc, "1  Alcance, entorno e identificación", 1)
        paragraph(
            doc,
            "La validación se ejecutó en Docker Compose aislado con PostgreSQL 16, Python 3.11, Node 22 y datos sintéticos. El runner confirmó que el SHA y el digest de fuentes coincidieron al inicio y al final, por lo que la evidencia corresponde a una instantánea estable del candidato evaluado.",
        )
        table(
            doc,
            ["Aspecto", "Resultado"],
            [
                ["Estado global", "Aprobado: 28 de 28 controles automatizados, código de salida 0."],
                ["Tiempo total", "142.77 segundos desde preparación hasta limpieza del entorno."],
                ["Datos", "Fixtures, factories, mocks y base efímera; sin datos reales ni secretos."],
                ["Evidencia", "Resumen, logs, JUnit, cobertura y build generados durante la corrida."],
                ["Regresión", "RUN-PAB-20261012-01 detectó formato no conforme; RUN-PAB-20261012-02 lo corrigió y RUN-PAB-20261012-04 confirmó la interfaz y la entrega optimizada."],
            ],
            [4.3, 12.2],
        )

        heading(doc, "2  Resumen ejecutivo", 1)
        paragraph(
            doc,
            "Todas las pruebas automatizadas vigentes están en verde. La suite backend aprobó 1,596 pruebas, la suite frontend aprobó 285 pruebas en 32 archivos y los controles de calidad, seguridad, migraciones, build y presupuesto concluyeron correctamente. No se detectó una incidencia crítica o alta activa en esta ejecución.",
        )
        doc.add_picture(str(execution_chart), width=Inches(6.5))
        caption(doc, "Figura 1. Estado de los controles integrados de la corrida vigente.")
        table(
            doc,
            ["Indicador", "Resultado", "Interpretación"],
            [
                ["Controles integrados", "28 / 28", "Todos finalizaron en verde."],
                ["Backend", "1,596 pruebas", "0 fallos; 94.45 % de cobertura por líneas."],
                ["Frontend", "285 pruebas / 32 archivos", "0 fallos; 73.98 % de cobertura por líneas."],
                ["Seguridad de dependencias", "0 vulnerabilidades npm", "Bandit y pip-audit aprobaron bajo la política versionada."],
                ["Estado crítico", "Ninguno", "No hubo controles fallidos o bloqueados."],
            ],
            [4.7, 4.0, 7.8],
        )

        heading(doc, "3  Casos y resultados de prueba", 1)
        table(
            doc,
            ["ID", "Prueba", "Objetivo", "Resultado observado", "Estado"],
            [
                ["PBT-001", "Regresión de formato", "Confirmar formato tras corrección.", "Prettier aprobó todo el frontend.", "Aprobado"],
                ["PBT-002", "Suite backend", "Validar dominio, API, permisos e integración.", "1,596 pruebas; cobertura 94.45 %.", "Aprobado"],
                ["PBT-003", "Suite frontend", "Validar UI, servicios y contratos simulados.", "285 pruebas en 32 archivos.", "Aprobado"],
                ["PBT-004", "Entrega y seguridad", "Validar migraciones, lint, auditorías, build y presupuesto.", "Todos los controles completados con código 0.", "Aprobado"],
            ],
            [1.4, 3.3, 4.8, 5.0, 2.3],
        )

        add_test_detail(
            doc,
            "PBT-001",
            "Regresión de formato frontend",
            "Comprobar que la corrección aplicada tras la primera ejecución deja el frontend conforme al formateador oficial.",
            "Contenedor frontend aislado con Node 22 y dependencias bloqueadas.",
            "npm run format:check, ejecutado por el runner integrado.",
            "Prettier debe finalizar con código 0 para todos los archivos del frontend.",
            "El control de formato aprobó en la segunda corrida, junto con los 27 controles restantes.",
            "Aprobado",
            "Incluido en los 144.18 segundos de la corrida completa.",
            "La primera ejecución detectó únicamente formato no conforme en AttendancePage.jsx. Se aplicó el formateador del proyecto sin alterar la lógica y se repitió la suite completa.",
        )
        code_block(doc, [
            "[frontend-format]",
            "> prettier --check .",
            "Checking formatting...",
            "All matched files use Prettier code style.",
            "exit code: 0",
        ])
        caption(doc, "Extracto de terminal 1. Regresión de formato aprobada.")

        add_test_detail(
            doc,
            "PBT-002",
            "Suite backend integrada",
            "Validar servicios de dominio, API, autorización, integración, migraciones y recuperación con PostgreSQL de prueba.",
            "Python 3.11, Django 5.2.17 y PostgreSQL 16 en contenedores aislados.",
            "pytest con cobertura de apps y config/api; umbral configurado: 70 %.",
            "Todas las pruebas deben aprobar y la cobertura debe alcanzar el umbral.",
            "1,596 pruebas aprobadas; 0 fallos; cobertura total de líneas: 94.45 %.",
            "Aprobado",
            "52.21 segundos de pytest; incluido en la corrida integrada.",
            "Se registraron 10 advertencias no bloqueantes. No modificaron el resultado ni el código de salida.",
        )
        code_block(doc, [
            "[backend-tests]",
            "Required test coverage of 70% reached. Total coverage: 94.45%",
            "====================== 1596 passed, 10 warnings in 52.21s ======================",
            "Coverage XML written to file /evidence/backend/coverage.xml",
        ])
        caption(doc, "Extracto de terminal 2. Suite backend y cobertura aprobadas.")

        add_test_detail(
            doc,
            "PBT-003",
            "Suite frontend y cobertura",
            "Validar componentes, navegación, formularios, servicios y contratos HTTP simulados con Vitest.",
            "Node 22 y Vitest en contenedor aislado con mocks y datos sintéticos versionados.",
            "npm run test:coverage -- --maxWorkers=2 con reportes JUnit y cobertura.",
            "La suite debe aprobar y generar los artefactos JUnit y cobertura requeridos.",
            "32 archivos y 285 pruebas aprobadas; reportes de cobertura y JUnit generados.",
            "Aprobado",
            "37.44 segundos registrados por Vitest; incluido en la corrida integrada.",
            "Incluye regresión de alumnos, docentes y encargados: sus servicios actualizan Persona mediante public_id.",
        )
        doc.add_picture(str(coverage_chart), width=Inches(6.5))
        caption(doc, "Figura 2. Cobertura frontend de la corrida aprobada.")
        table(
            doc,
            ["Métrica", "Resultado", "Umbral", "Margen"],
            [
                ["Statements", "73.32 %", "60.00 %", "+13.32 puntos"],
                ["Branches", "68.39 %", "50.00 %", "+18.39 puntos"],
                ["Functions", "68.03 %", "60.00 %", "+8.03 puntos"],
                ["Lines", "73.98 %", "60.00 %", "+13.98 puntos"],
            ],
            [4.0, 3.0, 3.0, 4.5],
        )
        code_block(doc, [
            "Test Files  32 passed (32)",
            "Tests  285 passed (285)",
            "All files  73.32% statements | 68.39% branches | 68.03% functions | 73.98% lines",
        ])
        caption(doc, "Extracto de terminal 3. Resumen de Vitest y cobertura aprobada.")

        add_test_detail(
            doc,
            "PBT-004",
            "Calidad, seguridad, migraciones y build",
            "Comprobar los controles obligatorios antes de entrega: lint, formato, Bandit, auditorías, migraciones y build de producción.",
            "Contenedores backend y frontend aislados; dependencias bloqueadas por los archivos del proyecto.",
            "Ruff, Bandit, pip-audit, Django check, makemigrations --check, npm audit, build y presupuesto.",
            "Todos los comandos deben finalizar con código 0 y generar los artefactos requeridos.",
            "Todos los controles aprobaron. npm audit reportó 0 vulnerabilidades; pip-audit aprobó con excepciones versionadas existentes.",
            "Aprobado",
            "Incluido en la corrida integrada de 142.77 segundos.",
            "El build separó los módulos compartidos de Asistencia; la ruta más grande fue CameraPreviewWindow y las migraciones no mostraron cambios pendientes.",
        )
        doc.add_picture(str(budget_chart), width=Inches(6.5))
        caption(doc, "Figura 3. Uso de presupuestos estáticos del build aprobado.")
        table(
            doc,
            ["Comprobación", "Resultado observado", "Límite", "Estado"],
            [
                ["Recursos iniciales gzip", "221,134 bytes", "230,000 bytes", "Aprobado"],
                ["Ruta lazy mayor gzip", "13,716 bytes", "20,000 bytes", "Aprobado"],
                ["Página fría mayor gzip", "234,850 bytes", "250,000 bytes", "Aprobado"],
                ["Recurso raster mayor", "3,522 bytes", "25,000 bytes", "Aprobado"],
            ],
            [4.2, 4.5, 3.0, 2.8],
        )
        doc.add_picture(str(security_chart), width=Inches(6.5))
        caption(doc, "Figura 4. Controles de seguridad automatizados aprobados.")
        code_block(doc, [
            "[backend-bandit]  exit code: 0",
            "[backend-audit]  No known vulnerabilities found, 1 ignored",
            "[migrations-check]  No changes detected",
            "[frontend-audit]  found 0 vulnerabilities",
            "[frontend-build]  budget checks passed",
        ])
        caption(doc, "Extracto de terminal 4. Calidad, seguridad, migraciones y build aprobados.")
        heading(doc, "5  Incidencias corregidas y regresión", 1)
        paragraph(
            doc,
            "El historial de incidencias se conserva, pero las correcciones siguientes fueron verificadas técnicamente en la corrida actual. No existe una incidencia crítica o alta activa detectada por RUN-PAB-20261012-04.",
        )
        table(
            doc,
            ["Incidencia", "Causa", "Corrección", "Regresión", "Estado"],
            [
                ["INC-004", "src/href vacío al no existir fotografía.", "Se omiten src y href cuando no hay imagen.", "Suite frontend completa y formato.", "Verificado"],
                ["INC-007", "La UI usaba person.id; API expone public_id.", "Servicios y pantallas actualizan por public_id.", "Pruebas de contrato y suites completas.", "Verificado"],
                ["INC-FMT-001", "Formato no conforme en AttendancePage.", "Prettier aplicado sin cambio de lógica.", "28/28 controles de la segunda corrida.", "Verificado"],
            ],
            [2.0, 4.0, 4.4, 4.1, 2.0],
        )

        heading(doc, "6  Conclusión y validaciones pendientes", 1)
        add_status_card(doc)
        paragraph(
            doc,
            "La evidencia técnica automatizada está completamente en verde. Se recomienda pasar al control de revisión independiente y a las sesiones de aceptación con usuarios. Estos pasos no se marcaron como ejecutados porque requieren participación institucional real y no pueden reemplazarse con una prueba automatizada.",
        )
        for item in [
            "Revisión independiente del candidato identificado por SHA y digest.",
            "Pruebas de aceptación con usuarios institucionales y acta de decisión.",
            "Validación de cámara/teléfono real y medición de carga con los perfiles y volúmenes confirmados por la institución.",
            "Repetición de impacto si el código cambia después de la versión evaluada.",
        ]:
            bullet(doc, item)
        heading(doc, "Anexo A  Declaración de evidencia", 1)
        paragraph(
            doc,
            "Las cifras, gráficos y extractos de terminal provienen de RUN-PAB-20261012-04. Los artefactos se produjeron sin datos sensibles. El informe acredita conformidad técnica automatizada; la autorización final de implementación corresponde a la aceptación institucional documentada.",
        )
    doc.save(OUTPUT)
    print(OUTPUT)


def main() -> None:
    current_main()


if __name__ == "__main__":
    main()
