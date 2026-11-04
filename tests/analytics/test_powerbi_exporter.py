"""Power BI export validation tests."""

import csv

from app.analytics.powerbi_exporter import export_powerbi
from app.db.models import Company, Exercise, ExerciseObjective, InjectEvent, Scenario


def test_exporter_writes_all_tables_with_bom_and_consistent_keys(db_session, tmp_path):
    company = Company(name="Empresa fictícia", segment="Treinamento", size="Pequeno", employee_count=4)
    db_session.add(company)
    db_session.flush()
    scenario = Scenario(
        company_id=company.id, name="Cenário demonstrativo", incident_type="simulado",
        difficulty="Inicial", description="Fictício", executive_summary="Treinamento",
    )
    db_session.add(scenario)
    db_session.flush()
    exercise = Exercise(
        company_id=company.id, scenario_id=scenario.id, title="Exercício teste",
        status="em_andamento", planned_duration=60,
    )
    db_session.add(exercise)
    db_session.flush()
    objective = ExerciseObjective(
        company_id=company.id, exercise_id=exercise.id, objective_name="Avaliação",
    )
    db_session.add(objective)
    inject = InjectEvent(
        company_id=company.id, exercise_id=exercise.id, scenario_inject_id="referência-fictícia",
        sequence=1, title="Inject", description="Fictício",
    )
    # Keep referential integrity by using a real scenario inject row.
    from app.db.models import ScenarioInject
    scenario_inject = ScenarioInject(
        scenario_id=scenario.id, sequence=1, title="Inject", description="Fictício",
    )
    db_session.add(scenario_inject)
    db_session.flush()
    inject.scenario_inject_id = scenario_inject.id
    db_session.add(inject)
    db_session.commit()

    result = export_powerbi(db_session, tmp_path)
    assert result["total_rows"] >= 12
    assert len(list(tmp_path.glob("*.csv"))) == 15
    with (tmp_path / "dim_empresa.csv").open(encoding="utf-8-sig", newline="") as file:
        companies = list(csv.DictReader(file))
    with (tmp_path / "fato_exercicios.csv").open(encoding="utf-8-sig", newline="") as file:
        facts = list(csv.DictReader(file))
    assert len(companies) == 1
    assert len(facts) == 1
    assert facts[0]["company_key"] == companies[0]["company_key"]
    assert facts[0]["scenario_key"] == "1"
