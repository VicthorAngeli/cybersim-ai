from html import escape


def render_report_markdown(report: dict) -> str:
    def items(title: str, values: list[str]) -> str:
        lines = [f"## {title}"]
        lines.extend(f"- {value}" for value in values)
        return "\n".join(lines)

    action_lines = [
        f"- **{action.get('priority', 'Sem prioridade')}** — {action.get('description', '')} "
        f"(responsável sugerido: {action.get('responsible_role', 'não definido')}; "
        f"status: {action.get('status', 'pendente')})"
        for action in report.get("action_plan", [])
    ]
    sections = [
        "# Relatório de lições aprendidas — CyberSim AI",
        "> Exercício fictício de treinamento. Não constitui auditoria, certificação ou parecer jurídico.",
        "## Identificação",
        f"- Exercício: {report.get('exercise_id') or 'Não informado'}",
        f"- Empresa fictícia: {report.get('company_name') or 'Não informada'}",
        f"- Cenário: {report.get('scenario_name') or 'Não informado'}",
        f"- Data/hora de início: {report.get('exercise_date') or 'Não informada'}",
        f"- Escopo: {report.get('scope') or 'Treinamento tabletop fictício.'}",
        items("Objetivos", report.get("objectives", [])),
        items("Participantes registrados por função/área", report.get("participants", [])),
        "## Resumo executivo",
        report.get("executive_summary", "Não disponível."),
        items("Linha do tempo", report.get("timeline", [])),
        items("Decisões registradas", report.get("decisions", [])),
        items("Pontos fortes", report.get("strengths", [])),
        items("Pontos de melhoria", report.get("improvement_areas", [])),
        items("Lacunas de comunicação", report.get("communication_gaps", [])),
        items("Lacunas de responsabilidade", report.get("responsibility_gaps", [])),
        items("Achados", report.get("findings", [])),
        items("Recomendações", report.get("recommendations", [])),
        "## Plano de ação",
        *(action_lines or ["Nenhuma ação consolidada foi registrada."]),
        items("Objetivos alcançados", report.get("objectives_achieved", [])),
        items("Objetivos não avaliados", report.get("objectives_not_assessed", [])),
        items("Referências metodológicas", report.get("nist_mapping", [])),
        items("Registros de evidência", report.get("evidence_ids", [])),
    ]
    return "\n\n".join(sections) + "\n"


def render_report_html(report: dict) -> str:
    markdown_text = render_report_markdown(report)
    paragraphs = "\n".join(
        f"<p>{escape(line)}</p>" if line and not line.startswith("#") and not line.startswith("- ")
        else f"<h2>{escape(line.lstrip('# '))}</h2>" if line.startswith("## ")
        else f"<h1>{escape(line.lstrip('# '))}</h1>" if line.startswith("# ")
        else f"<p class=\"list-item\">{escape(line[2:])}</p>" if line.startswith("- ")
        else ""
        for line in markdown_text.splitlines()
    )
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><title>Relatório CyberSim AI</title>
<style>
body{{font:16px/1.6 Arial,sans-serif;color:#17233a;max-width:920px;margin:40px auto;padding:0 24px}}
h1,h2{{color:#101B2D}}h1{{border-bottom:3px solid #2463EB;padding-bottom:12px}}
.list-item{{padding-left:16px}}@media print{{body{{margin:0;max-width:none}}}}
</style></head><body>{paragraphs}<button onclick="window.print()">Imprimir / Salvar em PDF</button></body></html>"""
