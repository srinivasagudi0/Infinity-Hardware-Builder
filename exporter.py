import json
import os
from pathlib import Path
from textwrap import wrap

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from agent import turn_project_into_markdown_text


EXPORT_DIR = Path(os.getenv("EXPORT_DIR", "exports"))


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


def export_project_in_every_format(project):
    return {
        "json": export_project_as_json_file(project),
        "markdown": export_project_as_markdown_file(project),
        "pdf": export_project_as_pdf_file(project),
    }
