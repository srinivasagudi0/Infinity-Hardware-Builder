import csv
import json
import os
import io
from pathlib import Path
from textwrap import wrap

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from agent import parse_component_entries, turn_project_into_markdown_text


EXPORT_DIR = Path(os.getenv("EXPORT_DIR", "exports"))
BOM_CSV_FIELDNAMES = ["name", "quantity", "unit_cost_estimate", "total_cost_estimate", "purchase_link", "source_note"]


def check_name_before_using_it_for_a_file(name):
    cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in name).strip("_")
    return cleaned or "project"


def make_sure_export_folder_exists():
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    return EXPORT_DIR


def export_project_as_json_file(project):
    export_dir = make_sure_export_folder_exists()
    file_path = export_dir / f"{check_name_before_using_it_for_a_file(project['project_name'])}.json"
    with open(file_path, "w", encoding="utf-8") as file_handle:
        json.dump(project, file_handle, indent=2, ensure_ascii=True)
    return file_path


def export_project_as_markdown_file(project):
    export_dir = make_sure_export_folder_exists()
    file_path = export_dir / f"{check_name_before_using_it_for_a_file(project['project_name'])}.md"
    with open(file_path, "w", encoding="utf-8") as file_handle:
        file_handle.write(turn_project_into_markdown_text(project))
    return file_path


def export_project_as_pdf_file(project):
    export_dir = make_sure_export_folder_exists()
    file_path = export_dir / f"{check_name_before_using_it_for_a_file(project['project_name'])}.pdf"
    pdf = canvas.Canvas(str(file_path), pagesize=letter)
    width, height = letter
    y = height - 40
    pdf.setFont("Helvetica", 10)

    for raw_line in turn_project_into_markdown_text(project).splitlines():
        wrapped_lines = wrap(raw_line, width=100) or [""]
        for line in wrapped_lines:
            pdf.drawString(40, y, line)
            y -= 14
            if y < 40:
                pdf.showPage()
                pdf.setFont("Helvetica", 10)
                y = height - 40
    pdf.save()
    return file_path


def _normalize_bom_row_for_csv(item):
    if isinstance(item, dict):
        return {field: item.get(field, "") for field in BOM_CSV_FIELDNAMES}
    return {
        "name": str(item),
        "quantity": "",
        "unit_cost_estimate": "",
        "total_cost_estimate": "",
        "purchase_link": "",
        "source_note": "",
    }


def _fallback_bom_rows_from_components(project):
    components_text = (project.get("inputs_json") or {}).get("components", "")
    component_names = parse_component_entries(components_text, use_defaults=False)
    if len(component_names) <= 1:
        return []
    return [
        {
            "name": component_name,
            "quantity": 1,
            "unit_cost_estimate": "",
            "total_cost_estimate": "",
            "purchase_link": "",
            "source_note": "Parsed from components input.",
        }
        for component_name in component_names
    ]


def make_bom_csv_text(project):
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=BOM_CSV_FIELDNAMES)
    writer.writeheader()

    artifacts = project.get("artifacts_json") or {}
    bom_rows = artifacts.get("bom") or []
    if not isinstance(bom_rows, list):
        bom_rows = []
    normalized_rows = [_normalize_bom_row_for_csv(item) for item in bom_rows if isinstance(item, (dict, str))]

    components_text = (project.get("inputs_json") or {}).get("components", "")
    if len(normalized_rows) <= 1 and any(separator in components_text for separator in ("\n", "\r", ";", "|")):
        fallback_rows = _fallback_bom_rows_from_components(project)
        if fallback_rows:
            normalized_rows = fallback_rows

    for row in normalized_rows:
        writer.writerow(row)
    return output.getvalue()


def export_project_in_every_format(project):
    return {
        "json": export_project_as_json_file(project),
        "markdown": export_project_as_markdown_file(project),
        "pdf": export_project_as_pdf_file(project),
    }
