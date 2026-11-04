from __future__ import annotations

import csv
import hashlib
import json
import re
import uuid
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
POWERBI = ROOT / "powerbi"
EXPORTS = POWERBI / "exports"
PBIP_NAME = "CyberSim AI"
REPORT_DIR = POWERBI / f"{PBIP_NAME}.Report"
MODEL_DIR = POWERBI / f"{PBIP_NAME}.SemanticModel"
REPORT_DEFINITION = REPORT_DIR / "definition"
MODEL_DEFINITION = MODEL_DIR / "definition"
NAMESPACE = uuid.UUID("61bb90c7-5271-4ad2-af7b-bf492ba235bb")

SCHEMAS = {
    "pbip": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
    "report_properties": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
    "report": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/3.3.0/schema.json",
    "pages": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json",
    "version": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json",
    "page": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json",
    "visual": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.13.0/schema.json",
    "model_properties": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
}
DATA_COLORS = ["#1687C9", "#087F7A", "#A07800", "#D9364F", "#4C5662", "#7655A3"]

TABLE_ORDER = [
    "dim_empresa",
    "dim_exercicio",
    "dim_cenario",
    "dim_agente",
    "dim_participante",
    "dim_objetivo",
    "dim_data",
    "fato_exercicios",
    "fato_injects",
    "fato_decisoes",
    "fato_execucoes_agente",
    "fato_achados",
    "fato_acoes_melhoria",
    "fato_comunicacoes",
    "fato_avaliacao_objetivos",
]

DIMENSION_KEYS = {
    "dim_empresa": "company_key",
    "dim_exercicio": "exercise_key",
    "dim_cenario": "scenario_key",
    "dim_agente": "agent_key",
    "dim_participante": "participant_key",
    "dim_objetivo": "objective_key",
    "dim_data": "date_key",
}

INTEGER_COLUMNS = {
    "agent_key",
    "company_key",
    "exercise_key",
    "scenario_key",
    "participant_key",
    "objective_key",
    "date_key",
    "sequence",
    "decision_count",
    "tempo_resposta_min",
    "latency_ms",
    "tokens_used",
    "validated",
    "attempts",
    "unknowns_count",
    "recommendations_count",
    "possible_anpd_communication",
    "legal_review_pending",
    "has_decision",
    "evidence_count",
    "score",
    "informacoes_pendentes",
    "duracao_planejada",
    "duracao_real",
    "participantes",
    "quantidade_funcionarios",
    "ano",
    "semestre",
    "trimestre",
    "mes",
    "dia",
    "dia_semana",
}

DATE_COLUMNS = {"data", "data_prazo"}
DATETIME_COLUMNS = {"data_inicio", "data_fim"}
BOOLEAN_COLUMNS = {"dados_simulados"}

MEASURES: list[tuple[str, str, str, str]] = [
    ("Total de Exercícios", "DISTINCTCOUNT(fato_exercicios[exercise_id])", "#,0", "01 • Exercícios"),
    ("Exercícios Concluídos", 'CALCULATE([Total de Exercícios], fato_exercicios[status] = "concluido")', "#,0", "01 • Exercícios"),
    ("Exercícios em Andamento", 'CALCULATE([Total de Exercícios], fato_exercicios[status] = "em_andamento")', "#,0", "01 • Exercícios"),
    ("Total de Injects", "COUNTROWS(fato_injects)", "#,0", "02 • Decisões"),
    ("Total de Decisões", "COUNTROWS(fato_decisoes)", "#,0", "02 • Decisões"),
    ("Tempo Médio para Decisão", "AVERAGE(fato_decisoes[tempo_resposta_min])", "0.0", "02 • Decisões"),
    ("Percentual de Injects com Decisão", "DIVIDE(SUM(fato_injects[has_decision]), [Total de Injects], 0)", "0.0%", "02 • Decisões"),
    ("Injects sem Decisão", "CALCULATE([Total de Injects], fato_injects[has_decision] = 0)", "#,0", "02 • Decisões"),
    ("Total de Achados", "COUNTROWS(fato_achados)", "#,0", "03 • Melhorias"),
    ("Total de Ações de Melhoria", "COUNTROWS(fato_acoes_melhoria)", "#,0", "03 • Melhorias"),
    ("Ações Pendentes", 'CALCULATE([Total de Ações de Melhoria], fato_acoes_melhoria[status] = "pendente")', "#,0", "03 • Melhorias"),
    (
        "Ações Atrasadas",
        'CALCULATE(COUNTROWS(fato_acoes_melhoria), FILTER(fato_acoes_melhoria, NOT ISBLANK(fato_acoes_melhoria[data_prazo]) && fato_acoes_melhoria[data_prazo] < TODAY() && fato_acoes_melhoria[status] <> "concluida" && fato_acoes_melhoria[status] <> "cancelada"))',
        "#,0",
        "03 • Melhorias",
    ),
    ("Ações Concluídas", 'CALCULATE([Total de Ações de Melhoria], fato_acoes_melhoria[status] = "concluida")', "#,0", "03 • Melhorias"),
    ("Média de Cobertura dos Objetivos", "DIVIDE(AVERAGE(fato_avaliacao_objetivos[score]), 4, 0)", "0.0%", "04 • Objetivos"),
    (
        "Percentual de Objetivos Avaliados",
        "VAR ObjetivosAvaliados = DISTINCTCOUNT(fato_avaliacao_objetivos[objective_key]) VAR ExerciciosNoContexto = VALUES(fato_exercicios[exercise_key]) VAR TotalObjetivos = CALCULATE(DISTINCTCOUNT(dim_objetivo[objective_key]), TREATAS(ExerciciosNoContexto, dim_objetivo[exercise_key])) RETURN DIVIDE(ObjetivosAvaliados, TotalObjetivos, 0)",
        "0.0%",
        "04 • Objetivos",
    ),
    ("Tempo Médio de Execução dos Agentes", "DIVIDE(AVERAGE(fato_execucoes_agente[latency_ms]), 1000, 0)", "0.0", "05 • Agentes"),
    ("Total de Execuções dos Agentes", "COUNTROWS(fato_execucoes_agente)", "#,0", "05 • Agentes"),
    ("Taxa de Execuções Validadas", "DIVIDE(SUM(fato_execucoes_agente[validated]), [Total de Execuções dos Agentes], 0)", "0.0%", "05 • Agentes"),
    ("Total de Tokens", "SUM(fato_execucoes_agente[tokens_used])", "#,0", "05 • Agentes"),
    ("Total de Comunicações", "COUNTROWS(fato_comunicacoes)", "#,0", "06 • Privacidade"),
    ("Unknowns Identificados", "SUM(fato_execucoes_agente[unknowns_count])", "#,0", "05 • Agentes"),
    ("Recomendações Geradas", "SUM(fato_execucoes_agente[recommendations_count])", "#,0", "05 • Agentes"),
    ("Revisões Jurídicas Pendentes", "SUM(fato_execucoes_agente[legal_review_pending])", "#,0", "06 • Privacidade"),
    ("Comunicações ANPD Possíveis (Simulação)", "SUM(fato_execucoes_agente[possible_anpd_communication])", "#,0", "06 • Privacidade"),
    (
        "Comunicações Aguardando Aprovação",
        'CALCULATE(COUNTROWS(fato_comunicacoes), FILTER(fato_comunicacoes, fato_comunicacoes[status_aprovacao] <> "aprovado" && fato_comunicacoes[status_aprovacao] <> "rejeitado"))',
        "#,0",
        "06 • Privacidade",
    ),
    (
        "Título Executivo",
        '"CyberSim AI  |  " & SELECTEDVALUE(dim_cenario[nome_cenario], "Todos os cenários") & "  •  " & FORMAT([Total de Exercícios], "0") & " exercício(s)"',
        "",
        "00 • Contexto",
    ),
]

SLICERS = [
    ("Empresa", "dim_empresa", "nome_empresa", "slicer_empresa"),
    ("Período", "dim_data", "data", "slicer_periodo"),
    ("Cenário", "dim_cenario", "nome_cenario", "slicer_cenario"),
    ("Dificuldade", "dim_exercicio", "dificuldade", "slicer_dificuldade"),
    ("Status", "dim_exercicio", "status", "slicer_status"),
]


def stable_guid(value: str) -> str:
    return str(uuid.uuid5(NAMESPACE, value))


def read_table_data(table: str) -> tuple[list[str], list[list[str]]]:
    path = EXPORTS / f"{table}.csv"
    if not path.is_file():
        raise FileNotFoundError(f"CSV obrigatório não encontrado: {path}")
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        try:
            columns = next(reader)
        except StopIteration as exc:
            raise ValueError(f"CSV sem cabeçalho: {path}") from exc
        rows = []
        for line_number, row in enumerate(reader, start=2):
            if len(row) != len(columns):
                raise ValueError(
                    f"Linha {line_number} de {path} tem {len(row)} campos; "
                    f"eram esperados {len(columns)}."
                )
            rows.append(row)
    return columns, rows


def m_text(value: str) -> str:
    escaped = (
        value.replace("#", "#(#)")
        .replace('"', '""')
        .replace("\r", "#(cr)")
        .replace("\n", "#(lf)")
        .replace("\t", "#(tab)")
    )
    return f'"{escaped}"'


def column_type(column: str) -> str:
    if column in BOOLEAN_COLUMNS:
        return "boolean"
    if column in DATE_COLUMNS:
        return "date"
    if column in DATETIME_COLUMNS:
        return "datetime"
    if column in INTEGER_COLUMNS or column.endswith("_key"):
        return "int64"
    return "string"


def m_type(data_type: str) -> str:
    return {
        "boolean": "type logical",
        "date": "type date",
        "datetime": "type datetime",
        "int64": "Int64.Type",
        "string": "type text",
    }[data_type]


def tmdl_data_type(data_type: str) -> str:
    return {
        "boolean": "boolean",
        "date": "dateTime",
        "datetime": "dateTime",
        "int64": "int64",
        "string": "string",
    }[data_type]


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_table_tmdl(table: str, columns: list[str], rows: list[list[str]]) -> str:
    lines = [f"table {table}", f"    lineageTag: {stable_guid(f'table:{table}')}", ""]
    sort_by = {"mes_nome": "mes", "ano_mes": "date_key"}
    for column in columns:
        data_type = column_type(column)
        lines.extend(
            [
                f"    column {column}",
                f"        dataType: {tmdl_data_type(data_type)}",
            ]
        )
        if column == DIMENSION_KEYS.get(table):
            lines.append("        isKey")
        if column.endswith("_key") or column.endswith("_id"):
            lines.append("        isHidden")
        if data_type in {"int64", "boolean"}:
            lines.append("        summarizeBy: none")
        if data_type in {"date", "datetime"}:
            lines.append('        formatString: Short Date')
        elif data_type == "int64":
            lines.append("        formatString: #,0")
        if column in sort_by:
            lines.append(f"        sortByColumn: {sort_by[column]}")
        lines.append(f"        sourceColumn: {column}")
        lines.append("")

    column_names = ", ".join(m_text(column) for column in columns)
    type_items = ", ".join(
        f"{{{m_text(column)}, {m_type(column_type(column))}}}" for column in columns
    )
    lines.extend(
        [
            f"    partition {table} = m",
            "        mode: import",
            "        source =",
            "            let",
            f"                Source = #table({{{column_names}}},",
            "                    {",
            *[
                "                        {"
                + ", ".join(m_text(value) if value else "null" for value in row)
                + "}"
                + ("," if index < len(rows) - 1 else "")
                for index, row in enumerate(rows)
            ],
            "                    }),",
            f'                ChangedType = Table.TransformColumnTypes(Source, {{{type_items}}}, "pt-BR")',
            "            in",
            "                ChangedType",
            "",
        ]
    )
    return "\n".join(lines)


def write_measures_tmdl() -> str:
    lines = [
        "table Medidas",
        f"    lineageTag: {stable_guid('table:Medidas')}",
        "",
        "    column Placeholder",
        "        dataType: string",
        "        isHidden",
        "        summarizeBy: none",
        "        sourceColumn: Placeholder",
        "",
        "    partition Medidas = m",
        "        mode: import",
        "        source = #table(type table [Placeholder = text], {})",
        "",
    ]
    for name, expression, format_string, folder in MEASURES:
        escaped_name = name.replace("'", "''")
        lines.extend(
            [
                f"    measure '{escaped_name}' = {expression}",
                f"        lineageTag: {stable_guid(f'measure:{name}')}",
            ]
        )
        if format_string:
            lines.append(f"        formatString: {format_string}")
        lines.append(f"        displayFolder: {folder}")
        lines.append("")
    return "\n".join(lines)


def relationships() -> list[tuple[str, str, str, str]]:
    facts = [
        "fato_exercicios",
        "fato_injects",
        "fato_decisoes",
        "fato_execucoes_agente",
        "fato_achados",
        "fato_acoes_melhoria",
        "fato_comunicacoes",
        "fato_avaliacao_objetivos",
    ]
    result: list[tuple[str, str, str, str]] = []
    for fact in facts:
        for dimension, key in (
            ("dim_empresa", "company_key"),
            ("dim_exercicio", "exercise_key"),
            ("dim_cenario", "scenario_key"),
            ("dim_data", "date_key"),
        ):
            result.append((dimension, key, fact, key))
    result.extend(
        [
            ("dim_agente", "agent_key", "fato_execucoes_agente", "agent_key"),
            ("dim_objetivo", "objective_key", "fato_avaliacao_objetivos", "objective_key"),
            ("dim_exercicio", "exercise_key", "dim_participante", "exercise_key"),
        ]
    )
    return result


def write_relationships_tmdl() -> str:
    lines: list[str] = []
    for source_table, source_column, target_table, target_column in relationships():
        relation_key = f"{source_table}.{source_column}->{target_table}.{target_column}"
        lines.extend(
            [
                f"relationship {stable_guid(f'relationship:{relation_key}')}",
                "    fromCardinality: many",
                f"    fromColumn: {target_table}.{target_column}",
                "    toCardinality: one",
                f"    toColumn: {source_table}.{source_column}",
                "    isActive",
                "    crossFilteringBehavior: oneDirection",
                "",
            ]
        )
    return "\n".join(lines)


def model_files(
    tables: dict[str, list[str]],
    table_rows: dict[str, list[list[str]]],
) -> None:
    definition = MODEL_DEFINITION
    (definition / "tables").mkdir(parents=True, exist_ok=True)
    (definition / "model.tmdl").write_text(
        "\n".join(
            [
                "model CyberSim_AI",
                "    culture: pt-BR",
                "    defaultPowerBIDataSourceVersion: powerBI_V3",
                "    sourceQueryCulture: pt-BR",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (definition / "relationships.tmdl").write_text(
        write_relationships_tmdl(),
        encoding="utf-8",
    )
    for table, columns in tables.items():
        (definition / "tables" / f"{table}.tmdl").write_text(
            write_table_tmdl(table, columns, table_rows[table]),
            encoding="utf-8",
        )
    (definition / "tables" / "Medidas.tmdl").write_text(
        write_measures_tmdl(),
        encoding="utf-8",
    )
    write_json(
        MODEL_DIR / "definition.pbism",
        {
            "$schema": SCHEMAS["model_properties"],
            "version": "4.0",
            "settings": {"qnaEnabled": False},
        },
    )


def field_ref(table: str, column: str, kind: str = "Column") -> dict[str, Any]:
    return {
        kind: {
            "Expression": {"SourceRef": {"Entity": table}},
            "Property": column,
        }
    }


def projection(table: str, column: str, kind: str = "Column") -> dict[str, Any]:
    return {
        "field": field_ref(table, column, kind),
        "queryRef": f"{table}.{column}",
        "nativeQueryRef": column,
    }


def measure_projection(name: str) -> dict[str, Any]:
    return projection("Medidas", name, "Measure")


def visual_query(
    visual_type: str,
    *,
    values: list[dict[str, Any]] | None = None,
    category: list[dict[str, Any]] | None = None,
    measures: list[dict[str, Any]] | None = None,
    legend: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    state: dict[str, Any] = {}
    if visual_type in {"tableEx", "multiRowCard", "slicer"}:
        state["Values"] = {"projections": values or []}
    else:
        if category:
            state["Category"] = {"projections": category}
        if measures:
            state["Y"] = {"projections": measures}
        if legend:
            state["Legend"] = {"projections": legend}
    return {
        "visualType": visual_type,
        "query": {"queryState": state},
        "drillFilterOtherVisuals": True,
    }


def literal(value: str) -> dict[str, Any]:
    return {"expr": {"Literal": {"Value": value}}}


def solid_color(value: str) -> dict[str, Any]:
    return {"solid": {"color": literal(f"'{value}'")}}


def container_style(
    title: str,
    *,
    background: str = "#FFFFFF",
    border: str = "#FFFFFF",
    radius: int = 14,
    show_title: bool = True,
) -> dict[str, Any]:
    return {
        "background": [
            {
                "properties": {
                    "show": literal("true"),
                    "color": solid_color(background),
                    "transparency": literal("0D"),
                }
            }
        ],
        "border": [
            {
                "properties": {
                    "show": literal("true"),
                    "color": solid_color(border),
                    "radius": literal(f"{radius}D"),
                    "width": literal("1D"),
                }
            }
        ],
        "dropShadow": [
            {
                "properties": {
                    "show": literal("true"),
                    "preset": literal("'Custom'"),
                    "color": solid_color("#19314F"),
                    "transparency": literal("88D"),
                    "shadowBlur": literal("6D"),
                    "shadowDistance": literal("2D"),
                    "angle": literal("45D"),
                    "shadowSpread": literal("0D"),
                }
            }
        ],
        "title": (
            [
                {
                    "properties": {
                        "show": literal("true"),
                        "text": literal(f"'{title.replace(chr(39), chr(39) * 2)}'"),
                        "fontColor": solid_color("#20385F"),
                        "fontFamily": literal("'Segoe UI Semibold'"),
                        "fontSize": literal("11D"),
                        "bold": literal("true"),
                        "alignment": literal("'left'"),
                    }
                }
            ]
            if show_title
            else [{"properties": {"show": literal("false")}}]
        ),
    }


class PageBuilder:
    def __init__(self, page_name: str, page_folder: Path) -> None:
        self.page_name = page_name
        self.page_folder = page_folder
        self.visuals: list[dict[str, Any]] = []
        self.tab_order = 0
        self.card_count = 0

    def add(
        self,
        visual_name: str,
        visual: dict[str, Any],
        x: int,
        y: int,
        width: int,
        height: int,
        *,
        sync_group: str | None = None,
        style: dict[str, Any] | None = None,
    ) -> None:
        self.tab_order += 1
        if sync_group:
            visual["syncGroup"] = {
                "groupName": sync_group,
                "fieldChanges": True,
                "filterChanges": True,
            }
        if style is not None:
            visual["visualContainerObjects"] = style
        elif visual["visualType"] != "multiRowCard" or visual_name != "Título Executivo":
            visual["visualContainerObjects"] = container_style(visual_name)
        if visual_name == "Título Executivo":
            visual["objects"] = {
                "dataLabels": [
                    {
                        "properties": {
                            "color": solid_color("#FFFFFF"),
                            "fontSize": literal("18D"),
                            "fontFamily": literal("'Segoe UI Semibold'"),
                            "bold": literal("true"),
                        }
                    }
                ],
                "categoryLabels": [{"properties": {"show": literal("false")}}],
            }
        visual_id = hashlib.sha256(
            f"{self.page_name}:{visual_name}".encode("utf-8")
        ).hexdigest()[:20]
        self.visuals.append(
            {
                "$schema": SCHEMAS["visual"],
                "name": visual_id,
                "position": {
                    "x": x,
                    "y": y,
                    "z": self.tab_order,
                    "height": height,
                    "width": width,
                    "tabOrder": self.tab_order,
                },
                "visual": visual,
            }
        )

    def add_slicers(self) -> None:
        x_positions = [32, 272, 512, 752, 992]
        for (label, table, column, group), x in zip(SLICERS, x_positions, strict=True):
            slicer = visual_query(
                "slicer",
                values=[projection(table, column)],
            )
            self.add(
                f"Filtro {label}",
                slicer,
                x,
                52,
                224,
                52,
                sync_group=group,
                style=container_style(label, background="#FFFFFF", border="#D5DFEA", radius=10),
            )

    def add_header(self) -> None:
        self.add(
            "Título Executivo",
            visual_query("multiRowCard", values=[measure_projection("Título Executivo")]),
            24,
            8,
            1232,
            36,
            style=container_style(
                "CyberSim AI",
                background="#20385F",
                border="#20385F",
                radius=10,
                show_title=False,
            ),
        )

    def add_card(
        self, name: str, measure: str, x: int, y: int, width: int, height: int
    ) -> None:
        card = visual_query("multiRowCard", values=[measure_projection(measure)])
        card_color = ["#D9364F", "#A07800", "#D9364F", "#4C5662", "#087F7A"][
            self.card_count % 5
        ]
        self.card_count += 1
        card["objects"] = {
            "dataLabels": [
                {
                    "properties": {
                        "color": solid_color(card_color),
                        "fontSize": literal("22D"),
                        "fontFamily": literal("'Segoe UI Semibold'"),
                        "bold": literal("true"),
                    }
                }
            ],
            "categoryLabels": [
                {
                    "properties": {
                        "color": solid_color("#26384B"),
                        "fontSize": literal("10D"),
                        "fontFamily": literal("'Segoe UI'"),
                    }
                }
            ],
        }
        self.add(
            name,
            card,
            x,
            y,
            width,
            height,
            style=container_style(
                name,
                background="#FFFFFF",
                border="#D6DEE8",
                radius=14,
                show_title=False,
            ),
        )

    def add_chart(
        self,
        name: str,
        visual_type: str,
        table: str,
        category: str,
        measure: str,
        x: int,
        y: int,
        width: int,
        height: int,
        *,
        legend: tuple[str, str] | None = None,
    ) -> None:
        self.add(
            name,
            visual_query(
                visual_type,
                category=[projection(table, category)],
                measures=[measure_projection(measure)],
                legend=[projection(*legend)] if legend else None,
            ),
            x,
            y,
            width,
            height,
            style=container_style(name),
        )

    def add_table(
        self,
        name: str,
        columns: list[tuple[str, str]],
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> None:
        self.add(
            name,
            visual_query(
                "tableEx",
                values=[projection(table, column) for table, column in columns],
            ),
            x,
            y,
            width,
            height,
            style=container_style(name),
        )

    def write(self, display_name: str) -> None:
        write_json(
            self.page_folder / "page.json",
            {
                "$schema": SCHEMAS["page"],
                "name": self.page_name,
                "displayName": display_name,
                "displayOption": "FitToPage",
                "height": 720,
                "width": 1280,
                "objects": {
                    "background": [
                        {
                            "properties": {
                                "color": solid_color("#DCE3EA"),
                                "transparency": literal("0D"),
                            }
                        }
                    ]
                },
            },
        )
        for visual in self.visuals:
            visual_folder = self.page_folder / "visuals" / visual["name"]
            write_json(visual_folder / "visual.json", visual)


def add_common_start(builder: PageBuilder) -> None:
    builder.add_header()
    builder.add_slicers()


def remove_legacy_visuals(page_folder: Path) -> None:
    visuals_folder = page_folder / "visuals"
    if not visuals_folder.is_dir():
        return
    for visual_folder in visuals_folder.iterdir():
        if not visual_folder.is_dir() or not re.fullmatch(r"[0-9a-f]{64}", visual_folder.name):
            continue
        contents = list(visual_folder.iterdir())
        if len(contents) == 1 and contents[0].name == "visual.json" and contents[0].is_file():
            contents[0].unlink()
            visual_folder.rmdir()


def build_pages() -> list[str]:
    pages_root = REPORT_DEFINITION / "pages"
    pages_root.mkdir(parents=True, exist_ok=True)
    page_names: list[str] = []

    def new_page(name: str, display: str) -> PageBuilder:
        page_names.append(name)
        page_folder = pages_root / name
        remove_legacy_visuals(page_folder)
        builder = PageBuilder(name, page_folder)
        add_common_start(builder)
        return builder

    page = new_page("executiva", "Executiva")
    kpis = [
        ("Exercícios", "Total de Exercícios"),
        ("Decisões", "Total de Decisões"),
        ("Injects com decisão", "Percentual de Injects com Decisão"),
        ("Ações pendentes", "Ações Pendentes"),
        ("Cobertura dos objetivos", "Média de Cobertura dos Objetivos"),
    ]
    for index, (label, measure) in enumerate(kpis):
        page.add_card(label, measure, 24 + index * 248, 124, 232, 88)
    page.add_chart(
        "Exercícios por mês",
        "lineChart",
        "dim_data",
        "ano_mes",
        "Total de Exercícios",
        24,
        232,
        608,
        200,
    )
    page.add_chart(
        "Exercícios por tipo de incidente",
        "clusteredBarChart",
        "dim_cenario",
        "tipo_incidente",
        "Total de Exercícios",
        648,
        232,
        608,
        200,
    )
    page.add_chart(
        "Ações por prioridade",
        "clusteredBarChart",
        "fato_acoes_melhoria",
        "prioridade",
        "Total de Ações de Melhoria",
        24,
        448,
        608,
        244,
    )
    page.add_table(
        "Plano de melhoria prioritário",
        [
            ("fato_acoes_melhoria", "descricao"),
            ("fato_acoes_melhoria", "prioridade"),
            ("fato_acoes_melhoria", "responsavel_funcao"),
            ("fato_acoes_melhoria", "status"),
        ],
        648,
        448,
        608,
        244,
    )
    page.write("Executiva")

    page = new_page("linha_tempo", "Linha do tempo")
    for index, (label, measure) in enumerate(
        [
            ("Injects liberados", "Total de Injects"),
            ("Decisões registradas", "Total de Decisões"),
            ("Tempo médio (min)", "Tempo Médio para Decisão"),
            ("Injects com decisão", "Percentual de Injects com Decisão"),
        ]
    ):
        page.add_card(label, measure, 24 + index * 310, 124, 294, 88)
    page.add_chart(
        "Injects por sequência",
        "clusteredColumnChart",
        "fato_injects",
        "sequence",
        "Total de Injects",
        24,
        232,
        600,
        200,
    )
    page.add_chart(
        "Injects por severidade",
        "clusteredBarChart",
        "fato_injects",
        "severidade",
        "Total de Injects",
        640,
        232,
        616,
        200,
    )
    page.add_table(
        "Cronologia dos injects",
        [
            ("fato_injects", "sequence"),
            ("fato_injects", "titulo"),
            ("fato_injects", "severidade"),
            ("fato_injects", "has_decision"),
        ],
        24,
        448,
        600,
        244,
    )
    page.add_table(
        "Decisões dos participantes",
        [
            ("fato_decisoes", "responsible_role"),
            ("fato_decisoes", "tempo_resposta_min"),
            ("fato_decisoes", "date_key"),
        ],
        640,
        448,
        616,
        244,
    )
    page.write("Linha do tempo")

    page = new_page("operacao_soc", "Operação SOC")
    for index, (label, measure) in enumerate(
        [
            ("Execuções de agentes", "Total de Execuções dos Agentes"),
            ("Saídas validadas", "Taxa de Execuções Validadas"),
            ("Unknowns registrados", "Unknowns Identificados"),
            ("Recomendações", "Recomendações Geradas"),
        ]
    ):
        page.add_card(label, measure, 24 + index * 310, 124, 294, 88)
    page.add_chart(
        "Execuções por agente",
        "clusteredBarChart",
        "dim_agente",
        "agent_name",
        "Total de Execuções dos Agentes",
        24,
        232,
        600,
        200,
    )
    page.add_chart(
        "Execuções por classificação simulada",
        "clusteredColumnChart",
        "fato_execucoes_agente",
        "incident_classification",
        "Total de Execuções dos Agentes",
        640,
        232,
        616,
        200,
    )
    page.add_table(
        "Registro de execuções simuladas",
        [
            ("dim_agente", "agent_name"),
            ("fato_execucoes_agente", "status"),
            ("fato_execucoes_agente", "severity"),
            ("fato_execucoes_agente", "unknowns_count"),
            ("fato_execucoes_agente", "recommendations_count"),
            ("fato_execucoes_agente", "validated"),
        ],
        24,
        448,
        1232,
        244,
    )
    page.write("Operação SOC")

    page = new_page("lgpd_comunicacao", "LGPD e comunicação")
    for index, (label, measure) in enumerate(
        [
            ("Revisões jurídicas pendentes", "Revisões Jurídicas Pendentes"),
            ("Comunicações ANPD possíveis*", "Comunicações ANPD Possíveis (Simulação)"),
            ("Rascunhos aguardando aprovação", "Comunicações Aguardando Aprovação"),
            ("Total de execuções avaliadas", "Total de Execuções dos Agentes"),
        ]
    ):
        page.add_card(label, measure, 24 + index * 310, 124, 294, 88)
    page.add_chart(
        "Rascunhos por status de aprovação",
        "clusteredBarChart",
        "fato_comunicacoes",
        "status_aprovacao",
        "Total de Comunicações",
        24,
        232,
        600,
        200,
    )
    page.add_chart(
        "Execuções sinalizadas para revisão jurídica",
        "clusteredColumnChart",
        "fato_execucoes_agente",
        "legal_review_pending",
        "Total de Execuções dos Agentes",
        640,
        232,
        616,
        200,
    )
    page.add_table(
        "Dados de privacidade da simulação (sem dados pessoais)",
        [
            ("fato_execucoes_agente", "data_categories"),
            ("fato_execucoes_agente", "possible_anpd_communication"),
            ("fato_execucoes_agente", "legal_review_pending"),
        ],
        24,
        448,
        600,
        244,
    )
    page.add_table(
        "Rascunhos e informações pendentes",
        [
            ("fato_comunicacoes", "publico_alvo"),
            ("fato_comunicacoes", "status_aprovacao"),
            ("fato_comunicacoes", "informacoes_pendentes"),
        ],
        640,
        448,
        616,
        244,
    )
    page.write("LGPD e comunicação")

    page = new_page("licoes_aprendidas", "Lições aprendidas")
    for index, (label, measure) in enumerate(
        [
            ("Achados registrados", "Total de Achados"),
            ("Ações de melhoria", "Total de Ações de Melhoria"),
            ("Ações atrasadas", "Ações Atrasadas"),
            ("Cobertura dos objetivos", "Média de Cobertura dos Objetivos"),
        ]
    ):
        page.add_card(label, measure, 24 + index * 310, 124, 294, 88)
    page.add_chart(
        "Achados por categoria",
        "clusteredBarChart",
        "fato_achados",
        "categoria",
        "Total de Achados",
        24,
        232,
        600,
        200,
    )
    page.add_chart(
        "Ações por prioridade",
        "clusteredColumnChart",
        "fato_acoes_melhoria",
        "prioridade",
        "Total de Ações de Melhoria",
        640,
        232,
        616,
        200,
    )
    page.add_table(
        "Plano de ação e acompanhamento",
        [
            ("fato_acoes_melhoria", "descricao"),
            ("fato_acoes_melhoria", "prioridade"),
            ("fato_acoes_melhoria", "responsavel_funcao"),
            ("fato_acoes_melhoria", "data_prazo"),
            ("fato_acoes_melhoria", "status"),
        ],
        24,
        448,
        1232,
        244,
    )
    page.write("Lições aprendidas")

    page = new_page("inteligencia_artificial", "Inteligência Artificial")
    for index, (label, measure) in enumerate(
        [
            ("Execuções", "Total de Execuções dos Agentes"),
            ("Duração média (s)", "Tempo Médio de Execução dos Agentes"),
            ("Saídas validadas", "Taxa de Execuções Validadas"),
            ("Tokens utilizados", "Total de Tokens"),
        ]
    ):
        page.add_card(label, measure, 24 + index * 310, 124, 294, 88)
    page.add_chart(
        "Execuções por agente",
        "clusteredBarChart",
        "dim_agente",
        "agent_name",
        "Total de Execuções dos Agentes",
        24,
        232,
        600,
        200,
    )
    page.add_chart(
        "Execuções por status",
        "clusteredColumnChart",
        "fato_execucoes_agente",
        "status",
        "Total de Execuções dos Agentes",
        640,
        232,
        616,
        200,
    )
    page.add_table(
        "Telemetria agregada dos agentes",
        [
            ("dim_agente", "agent_name"),
            ("fato_execucoes_agente", "status"),
            ("fato_execucoes_agente", "latency_ms"),
            ("fato_execucoes_agente", "tokens_used"),
            ("fato_execucoes_agente", "attempts"),
            ("fato_execucoes_agente", "validated"),
        ],
        24,
        448,
        1232,
        244,
    )
    page.write("Inteligência Artificial")

    write_json(
        pages_root / "pages.json",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json",
            "pageOrder": page_names,
            "activePageName": "executiva",
        },
    )
    return page_names


def build_report() -> None:
    report_definition = REPORT_DEFINITION
    (report_definition / "pages").mkdir(parents=True, exist_ok=True)
    theme_path = "RegisteredResources/cybersim-theme.json"
    write_json(
        REPORT_DIR / "definition.pbir",
        {
            "$schema": SCHEMAS["report_properties"],
            "version": "4.0",
            "datasetReference": {"byPath": {"path": f"../{PBIP_NAME}.SemanticModel"}},
        },
    )
    write_json(
        report_definition / "report.json",
        {
            "$schema": SCHEMAS["report"],
            "themeCollection": {
                "customTheme": {
                    "name": "CyberSim AI - Painel de Segurança",
                    "reportVersionAtImport": {
                        "visual": "2.13.0",
                        "report": "3.3.0",
                        "page": "2.1.0",
                    },
                    "type": "RegisteredResources",
                }
            },
            "resourcePackages": [
                {
                    "name": "RegisteredResources",
                    "type": "RegisteredResources",
                    "items": [
                        {
                            "name": "cybersim-theme.json",
                            "path": theme_path,
                            "type": "CustomTheme",
                        }
                    ],
                }
            ],
        },
    )
    write_json(
        report_definition / "version.json",
        {
            "$schema": SCHEMAS["version"],
            "version": "2.0.0",
        },
    )
    write_json(
        REPORT_DIR / "StaticResources" / theme_path,
        {
            "name": "CyberSim AI - Executivo",
            "dataColors": DATA_COLORS,
            "background": "#DCE3EA",
            "foreground": "#20385F",
            "tableAccent": "#1687C9",
            "visualStyles": {
                "*": {
                    "*": {
                        "title": [
                            {
                                "show": True,
                                "fontFace": "Segoe UI",
                                "fontSize": 11,
                                "color": {"solid": {"color": "#20385F"}},
                                "bold": True,
                            }
                        ],
                        "background": [
                            {
                                "show": True,
                                "color": {"solid": {"color": "#FFFFFF"}},
                                "transparency": 0,
                            }
                        ]
                    }
                }
            },
        },
    )
    build_pages()


def main() -> None:
    table_data = {table: read_table_data(table) for table in TABLE_ORDER}
    tables = {table: data[0] for table, data in table_data.items()}
    table_rows = {table: data[1] for table, data in table_data.items()}
    (POWERBI / f"{PBIP_NAME}.pbip").write_text(
        json.dumps(
            {
                "$schema": SCHEMAS["pbip"],
                "version": "1.0",
                "artifacts": [{"report": {"path": f"{PBIP_NAME}.Report"}}],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    model_files(tables, table_rows)
    build_report()
    print(f"PBIP criado em: {POWERBI / f'{PBIP_NAME}.pbip'}")
    print(f"Modelo: {MODEL_DIR}")
    print(f"Relatório: {REPORT_DIR}")
    print(f"Tabelas: {len(tables)} | Medidas: {len(MEASURES)} | Relações: {len(relationships())}")


if __name__ == "__main__":
    main()
