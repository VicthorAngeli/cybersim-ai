from __future__ import annotations

import csv
import json
import re
import sys
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from jsonschema import Draft7Validator
from referencing import Registry, Resource


ROOT = Path(__file__).resolve().parents[2]
POWERBI = ROOT / "powerbi"
EXPORTS = POWERBI / "exports"
PBIP_NAME = "CyberSim AI"
REPORT_DIR = POWERBI / f"{PBIP_NAME}.Report"
MODEL_DIR = POWERBI / f"{PBIP_NAME}.SemanticModel"
MODEL_DEFINITION = MODEL_DIR / "definition"
REPORT_DEFINITION = REPORT_DIR / "definition"
SCHEMA_CACHE: dict[str, dict[str, Any]] = {}
VALIDATOR_CACHE: dict[str, Draft7Validator] = {}

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


def schema_url_to_raw(url: str) -> str:
    parsed = urlparse(url)
    prefix = "/json-schemas/"
    if parsed.netloc == "developer.microsoft.com" and parsed.path.startswith(prefix):
        relative = parsed.path[len(prefix) :]
        relative = relative.replace("/schema.embedded.json", "/schema-embedded.json")
        return f"https://raw.githubusercontent.com/microsoft/json-schemas/main/{relative}"
    return url


def fetch_schema(url: str) -> dict[str, Any]:
    if url in SCHEMA_CACHE:
        return SCHEMA_CACHE[url]
    request = urllib.request.Request(
        schema_url_to_raw(url),
        headers={"User-Agent": "CyberSimAI-PBIP-Validator"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            SCHEMA_CACHE[url] = json.load(response)
    except Exception as exc:
        raise RuntimeError(f"não foi possível carregar o schema {url}: {exc}") from exc
    return SCHEMA_CACHE[url]


def validator_for(schema_url: str) -> Draft7Validator:
    if schema_url in VALIDATOR_CACHE:
        return VALIDATOR_CACHE[schema_url]
    schema = fetch_schema(schema_url)

    def retrieve(uri: str) -> Resource:
        return Resource.from_contents(fetch_schema(uri))

    validator = Draft7Validator(schema, registry=Registry(retrieve=retrieve))
    VALIDATOR_CACHE[schema_url] = validator
    return validator


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def validate_json_schema(path: Path, schema_url: str, errors: list[str]) -> None:
    try:
        instance = load_json(path)
        validator = validator_for(schema_url)
        for error in validator.iter_errors(instance):
            location = ".".join(str(item) for item in error.absolute_path) or "<root>"
            errors.append(f"{path.relative_to(POWERBI)}:{location}: {error.message}")
    except Exception as exc:
        errors.append(f"{path.relative_to(POWERBI)}: validação de schema falhou: {exc}")


def parse_tmdl_model() -> tuple[dict[str, set[str]], dict[str, set[str]], list[tuple[str, str]]]:
    columns: dict[str, set[str]] = defaultdict(set)
    measures: dict[str, set[str]] = defaultdict(set)
    guid_lines: list[tuple[str, str]] = []
    table_dir = MODEL_DEFINITION / "tables"
    for path in sorted(table_dir.glob("*.tmdl")):
        text = path.read_text(encoding="utf-8")
        table_match = re.search(r"^table\s+(.+)$", text, re.MULTILINE)
        if not table_match:
            continue
        table = table_match.group(1).strip().strip("'")
        columns[table].update(
            match.group(1).strip().strip("'")
            for match in re.finditer(r"^    column\s+(.+)$", text, re.MULTILINE)
        )
        measures[table].update(
            match.group(1).replace("''", "'")
            for match in re.finditer(r"^    measure\s+'((?:[^']|'')+)'\s*=", text, re.MULTILINE)
        )
        for line in text.splitlines():
            if "lineageTag:" in line:
                guid_lines.append((str(path.relative_to(POWERBI)), line.split(":", 1)[1].strip()))
    return columns, measures, guid_lines


def validate_embedded_partitions(errors: list[str]) -> None:
    for path in sorted((MODEL_DEFINITION / "tables").glob("*.tmdl")):
        if path.stem == "Medidas":
            continue
        text = path.read_text(encoding="utf-8")
        if "Source = #table(" not in text:
            errors.append(f"Partição sem dados incorporados: {path.relative_to(POWERBI)}")
        if "File.Contents(" in text:
            errors.append(f"Partição ainda depende de arquivo local: {path.relative_to(POWERBI)}")


def parse_relationships(errors: list[str]) -> list[tuple[str, str, str, str]]:
    path = MODEL_DEFINITION / "relationships.tmdl"
    text = path.read_text(encoding="utf-8")
    relations = re.findall(
        r"^relationship\s+([0-9a-fA-F-]+)\s*\n"
        r"\s+fromCardinality:\s+many\s*\n"
        r"\s+fromColumn:\s+([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)\s*\n"
        r"\s+toCardinality:\s+one\s*\n"
        r"\s+toColumn:\s+([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)",
        text,
        re.MULTILINE,
    )
    seen_ids: set[str] = set()
    result: list[tuple[str, str, str, str]] = []
    pairs: set[tuple[str, str, str, str]] = set()
    for relation_id, many_table, many_column, one_table, one_column in relations:
        if relation_id in seen_ids:
            errors.append(f"GUID de relacionamento duplicado: {relation_id}")
        seen_ids.add(relation_id)
        pair = (one_table.strip(), one_column, many_table.strip(), many_column)
        if pair in pairs:
            errors.append(f"Relacionamento duplicado: {pair}")
        pairs.add(pair)
        result.append(pair)
    if not relations:
        errors.append("Nenhum relacionamento TMDL foi reconhecido.")
    return result


def validate_relationships(
    relationships: list[tuple[str, str, str, str]],
    columns: dict[str, set[str]],
    errors: list[str],
) -> None:
    graph: dict[str, list[str]] = defaultdict(list)
    key_values: dict[tuple[str, str], set[str]] = {}

    def values_for(table: str, column: str) -> set[str]:
        key = (table, column)
        if key not in key_values:
            path = EXPORTS / f"{table}.csv"
            try:
                with path.open(encoding="utf-8-sig", newline="") as stream:
                    key_values[key] = {
                        row[column]
                        for row in csv.DictReader(stream)
                        if row.get(column) not in (None, "")
                    }
            except (OSError, KeyError) as exc:
                errors.append(f"Não foi possível verificar {table}[{column}]: {exc}")
                key_values[key] = set()
        return key_values[key]

    for source_table, source_column, target_table, target_column in relationships:
        if source_column not in columns.get(source_table, set()):
            errors.append(f"Coluna de relacionamento inexistente: {source_table}[{source_column}]")
        if target_column not in columns.get(target_table, set()):
            errors.append(f"Coluna de relacionamento inexistente: {target_table}[{target_column}]")
        source_values = values_for(source_table, source_column)
        target_values = values_for(target_table, target_column)
        orphan_values = target_values - source_values
        if orphan_values:
            examples = ", ".join(sorted(orphan_values)[:3])
            errors.append(
                f"Chaves sem correspondência em {source_table}[{source_column}] "
                f"para {target_table}[{target_column}]: {examples}"
            )
        graph[source_table].append(target_table)

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(table: str) -> None:
        if table in visiting:
            errors.append(f"Ciclo em relacionamentos ativos detectado envolvendo {table}.")
            return
        if table in visited:
            return
        visiting.add(table)
        for neighbor in graph.get(table, []):
            visit(neighbor)
        visiting.remove(table)
        visited.add(table)

    for table in graph:
        visit(table)

    for source in graph:
        path_counts: Counter[str] = Counter()

        def count_paths(table: str, path: frozenset[str]) -> None:
            for neighbor in graph.get(table, []):
                if neighbor in path:
                    continue
                path_counts[neighbor] += 1
                count_paths(neighbor, path | {neighbor})

        count_paths(source, frozenset({source}))
        ambiguous = sorted(table for table, count in path_counts.items() if count > 1)
        if ambiguous:
            errors.append(
                f"Caminhos ativos ambíguos a partir de {source}: {', '.join(ambiguous)}"
            )


def collect_field_references(value: Any) -> list[tuple[str, str, str]]:
    found: list[tuple[str, str, str]] = []
    if isinstance(value, dict):
        for kind in ("Column", "Measure"):
            field = value.get(kind)
            if isinstance(field, dict):
                expression = field.get("Expression", {})
                source_ref = expression.get("SourceRef", {}) if isinstance(expression, dict) else {}
                entity = source_ref.get("Entity")
                prop = field.get("Property")
                if isinstance(entity, str) and isinstance(prop, str):
                    found.append((kind, entity, prop))
        for child in value.values():
            found.extend(collect_field_references(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(collect_field_references(child))
    return found


def validate_visual_fields(
    columns: dict[str, set[str]],
    measures: dict[str, set[str]],
    errors: list[str],
) -> None:
    for path in REPORT_DEFINITION.glob("pages/*/visuals/*/visual.json"):
        try:
            visual = load_json(path)
        except Exception as exc:
            errors.append(f"{path.relative_to(POWERBI)}: JSON inválido: {exc}")
            continue
        for kind, table, prop in collect_field_references(visual):
            available = columns if kind == "Column" else measures
            if prop not in available.get(table, set()):
                errors.append(
                    f"{path.relative_to(POWERBI)}: {kind} inexistente {table}[{prop}]"
                )


def validate_page_design(errors: list[str]) -> None:
    page_paths = sorted((REPORT_DEFINITION / "pages").glob("*/page.json"))
    if len(page_paths) != 6:
        errors.append(f"Esperadas 6 páginas do relatório; encontradas {len(page_paths)}.")

    for page_path in page_paths:
        page = load_json(page_path)
        if page.get("width") != 1280 or page.get("height") != 720:
            errors.append(f"Página fora do layout 16:9: {page_path.relative_to(POWERBI)}")
        if not page.get("objects", {}).get("background"):
            errors.append(f"Página sem fundo de tema: {page_path.relative_to(POWERBI)}")

        visual_paths = sorted((page_path.parent / "visuals").glob("*/visual.json"))
        slicer_groups: set[str] = set()
        for visual_path in visual_paths:
            visual = load_json(visual_path)
            visual_config = visual.get("visual", {})
            formatting = visual_config.get("visualContainerObjects", {})
            if not formatting.get("background") or not formatting.get("border"):
                errors.append(
                    f"Visual sem painel estilizado: {visual_path.relative_to(POWERBI)}"
                )
            group = visual_config.get("syncGroup", {}).get("groupName")
            if group:
                slicer_groups.add(group)
                projections = (
                    visual_config.get("query", {})
                    .get("queryState", {})
                    .get("Values", {})
                    .get("projections", [])
                )
                if not projections:
                    errors.append(
                        f"Segmentador sem campo: {visual_path.relative_to(POWERBI)}"
                    )
        if len(slicer_groups) != 5:
            errors.append(
                f"Esperados 5 filtros sincronizados em {page_path.parent.name}; "
                f"encontrados {len(slicer_groups)}."
            )


def validate_duplicate_names(
    columns: dict[str, set[str]],
    measures: dict[str, set[str]],
    errors: list[str],
) -> None:
    for table, names in measures.items():
        duplicates = names & columns.get(table, set())
        for name in sorted(duplicates):
            errors.append(f"Medida e coluna com o mesmo nome em {table}: {name}")


def validate_guids(
    guid_lines: list[tuple[str, str]],
    errors: list[str],
) -> None:
    identifiers = list(guid_lines)
    relationship_path = MODEL_DEFINITION / "relationships.tmdl"
    if relationship_path.is_file():
        relationship_text = relationship_path.read_text(encoding="utf-8")
        identifiers.extend(
            (str(relationship_path.relative_to(POWERBI)), match.group(1))
            for match in re.finditer(
                r"^relationship\s+([0-9a-fA-F-]+)",
                relationship_text,
                re.MULTILINE,
            )
        )
    visual_ids: list[tuple[str, str]] = []
    for path in REPORT_DEFINITION.glob("pages/*/visuals/*/visual.json"):
        try:
            visual = load_json(path)
            visual_ids.append((str(path.relative_to(POWERBI)), visual.get("name", "")))
        except Exception:
            continue
    seen: dict[str, str] = {}
    for path, identifier in identifiers:
        normalized = str(identifier).replace("-", "").lower()
        if not re.fullmatch(r"[0-9a-f]{32}", normalized):
            errors.append(f"Identificador GUID inválido em {path}: {identifier}")
        elif normalized in seen:
            errors.append(f"GUID duplicado {identifier} em {path} e {seen[normalized]}")
        else:
            seen[normalized] = path
    seen_visuals: dict[str, str] = {}
    for path, identifier in visual_ids:
        if not re.fullmatch(r"[0-9a-f]{20}", identifier):
            errors.append(f"Identificador visual inválido em {path}: {identifier}")
        elif identifier in seen_visuals:
            errors.append(
                f"ID visual duplicado {identifier} em {path} e {seen_visuals[identifier]}"
            )
        else:
            seen_visuals[identifier] = path


def validate_dimension_keys(errors: list[str]) -> None:
    dimensions = {
        "dim_empresa": "company_key",
        "dim_exercicio": "exercise_key",
        "dim_cenario": "scenario_key",
        "dim_agente": "agent_key",
        "dim_participante": "participant_key",
        "dim_objetivo": "objective_key",
        "dim_data": "date_key",
    }
    for table, key in dimensions.items():
        path = EXPORTS / f"{table}.csv"
        try:
            with path.open(encoding="utf-8-sig", newline="") as stream:
                values = [row[key] for row in csv.DictReader(stream)]
        except (OSError, KeyError) as exc:
            errors.append(f"Não foi possível verificar {table}[{key}]: {exc}")
            continue
        if len(values) != len(set(values)):
            errors.append(f"Chave duplicada em {table}[{key}].")


def main() -> int:
    errors: list[str] = []
    schema_paths = [
        (POWERBI / f"{PBIP_NAME}.pbip", SCHEMAS["pbip"]),
        (REPORT_DIR / "definition.pbir", SCHEMAS["report_properties"]),
        (REPORT_DEFINITION / "report.json", SCHEMAS["report"]),
        (REPORT_DEFINITION / "pages" / "pages.json", SCHEMAS["pages"]),
        (REPORT_DEFINITION / "version.json", SCHEMAS["version"]),
        (MODEL_DIR / "definition.pbism", SCHEMAS["model_properties"]),
    ]
    for path, schema_url in schema_paths:
        validate_json_schema(path, schema_url, errors)

    for path in REPORT_DEFINITION.glob("pages/*/page.json"):
        validate_json_schema(path, SCHEMAS["page"], errors)
    for path in REPORT_DEFINITION.glob("pages/*/visuals/*/visual.json"):
        validate_json_schema(path, SCHEMAS["visual"], errors)

    columns, measures, guid_lines = parse_tmdl_model()
    validate_embedded_partitions(errors)
    relationships_list = parse_relationships(errors)
    validate_relationships(relationships_list, columns, errors)
    validate_visual_fields(columns, measures, errors)
    validate_page_design(errors)
    validate_duplicate_names(columns, measures, errors)
    validate_guids(guid_lines, errors)
    validate_dimension_keys(errors)

    if errors:
        print(f"Validação PBIP: {len(errors)} erro(s)")
        for error in errors:
            print(f"- {error}")
        return 1

    visual_count = len(list(REPORT_DEFINITION.glob("pages/*/visuals/*/visual.json")))
    print(
        "Validação PBIP concluída: JSONs aprovados pelos schemas oficiais; "
        f"{len(columns)} tabelas, {sum(map(len, measures.values()))} medidas, "
        f"{len(relationships_list)} relações e {visual_count} visuais; "
        "seis páginas em layout uniforme; campos, chaves e GUIDs consistentes; "
        "sem ciclos ou caminhos ambíguos."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
