"""End-to-end API flow tests."""

import io
from zipfile import ZipFile


def _login(client, email="admin@test.cybersim.local", password="TestOnly!Passphrase2026"):
    response = client.post("/api/v1/auth/token", json={"email": email, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_complete_mock_exercise_api_flow_and_powerbi_export(client):
    headers = _login(client)
    assert client.get("/health").json()["status"] == "ok"

    company_response = client.post("/api/v1/companies", headers=headers, json={
        "name": "Horizonte Digital de teste",
        "segment": "Comércio eletrônico",
        "size": "Médio",
        "employee_count": 120,
        "critical_systems": ["CRM", "ERP"],
        "data_categories": ["dados cadastrais"],
        "essential_processes": ["pedidos"],
        "security_maturity": "Inicial",
    })
    assert company_response.status_code == 201, company_response.text
    company_id = company_response.json()["id"]

    created = client.post("/api/v1/exercises", headers=headers, json={
        "company_id": company_id,
        "title": "Exercício de validação de ponta a ponta",
        "incident_type": "exposicao_acidental",
        "difficulty": "Intermediário",
        "planned_duration": 60,
        "participant_count": 4,
        "objectives": ["Praticar escalonamento", "Registrar decisões"],
        "areas": ["TI", "Privacidade"],
        "affected_systems": ["CRM"],
        "data_categories": ["dados cadastrais"],
    })
    assert created.status_code == 201, created.text
    exercise_id = created.json()["id"]

    generated = client.post(
        f"/api/v1/exercises/{exercise_id}/scenario/generate",
        headers=headers,
        json={"incident_type": "indisponibilidade_sistema"},
    )
    assert generated.status_code == 200, generated.text
    assert generated.json()["scenario"]["incident_type"] == "indisponibilidade_sistema"

    generated = client.post(
        f"/api/v1/exercises/{exercise_id}/scenario/generate",
        headers=headers,
        json={"incident_type": "exposicao_acidental"},
    )
    assert generated.status_code == 200, generated.text
    assert generated.json()["status"] == "planejado"
    assert generated.json()["scenario"]["inject_count"] == 5

    start = client.post(
        f"/api/v1/exercises/{exercise_id}/start",
        headers=headers,
        json={},
    )
    assert start.status_code == 200, start.text
    assert start.json()["scenario"]["inject_count"] == 5

    all_decision_ids = []
    for sequence in range(1, 6):
        released = client.post(
            f"/api/v1/exercises/{exercise_id}/injects/release-next",
            headers=headers,
            json={},
        )
        assert released.status_code == 200, released.text
        assert released.json()["inject"]["sequence"] == sequence
        decision = client.post(
            f"/api/v1/exercises/{exercise_id}/decisions",
            headers=headers,
            json={
                "inject_event_id": released.json()["inject"]["id"],
                "description": f"Decisão fictícia registrada para o inject {sequence}.",
                "rationale": "Registro de teste com evidência do exercício.",
                "responsible_role": "Facilitador",
            },
        )
        assert decision.status_code == 201, decision.text
        all_decision_ids.append(decision.json()["id"])

    agent_runs = client.get(f"/api/v1/exercises/{exercise_id}/agents", headers=headers).json()
    assert {row["agent_name"] for row in agent_runs} >= {
        "narrator", "soc", "legal", "communications",
    }

    detail = client.get(f"/api/v1/exercises/{exercise_id}", headers=headers).json()
    assert len(detail["released_injects"]) == 5
    assert len(detail["decisions"]) == 5
    assert len(detail["objectives"]) >= 10
    assessment = client.post(
        f"/api/v1/exercises/{exercise_id}/objectives/assessments",
        headers=headers,
        json={"objective_id": detail["objectives"][0]["id"], "score": 3,
              "evidence_ids": [all_decision_ids[0]]},
    )
    assert assessment.status_code == 200, assessment.text
    invalid_assessment = client.post(
        f"/api/v1/exercises/{exercise_id}/objectives/assessments",
        headers=headers,
        json={"objective_id": detail["objectives"][1]["id"], "score": 4, "evidence_ids": []},
    )
    assert invalid_assessment.status_code == 422

    insights = client.get(f"/api/v1/exercises/{exercise_id}/insights", headers=headers).json()
    assert insights["communications"]
    draft = insights["communications"][0]
    approval = client.patch(
        f"/api/v1/exercises/{exercise_id}/communications/{draft['id']}",
        headers=headers,
        json={"status": "aprovado", "rationale": "Revisado no teste; sem envio externo."},
    )
    assert approval.status_code == 200
    assert "nenhum envio" in approval.json()["message"].casefold()

    completed = client.post(f"/api/v1/exercises/{exercise_id}/complete", headers=headers)
    assert completed.status_code == 200, completed.text
    assert completed.json()["company_name"] == "Horizonte Digital de teste"
    report_json = client.get(f"/api/v1/exercises/{exercise_id}/report", headers=headers)
    report_md = client.get(f"/api/v1/exercises/{exercise_id}/report?format=markdown", headers=headers)
    report_html = client.get(f"/api/v1/exercises/{exercise_id}/report?format=html", headers=headers)
    assert report_json.status_code == 200
    assert report_json.json()["action_plan"]
    action = client.get(f"/api/v1/exercises/{exercise_id}/insights", headers=headers).json()["actions"][0]
    assert action["status"] == "pendente"
    assert "# Relatório" in report_md.text
    assert "window.print()" in report_html.text

    exported = client.get("/api/v1/analytics/export", headers=headers)
    assert exported.status_code == 200
    assert exported.headers["content-type"] == "application/zip"
    assert int(exported.headers["x-export-record-count"]) >= 15
    with ZipFile(io.BytesIO(exported.content)) as archive:
        csv_names = archive.namelist()
        assert len(csv_names) == 15
        company_csv = archive.read("dim_empresa.csv")
        assert company_csv.startswith(b"\xef\xbb\xbf")
        assert "Horizonte Digital de teste".encode("utf-8") in company_csv
        inject_csv = archive.read("fato_injects.csv").decode("utf-8-sig")
        assert inject_csv.count("\n") == 6


def test_authentication_tenant_isolation_and_facilitator_notes(client):
    headers = _login(client)
    company_a = client.post("/api/v1/companies", headers=headers, json={
        "name": "Tenant A", "segment": "Treinamento", "size": "Pequeno", "employee_count": 10,
    }).json()
    company_b = client.post("/api/v1/companies", headers=headers, json={
        "name": "Tenant B", "segment": "Treinamento", "size": "Pequeno", "employee_count": 12,
    }).json()
    exercise = client.post("/api/v1/exercises", headers=headers, json={
        "company_id": company_a["id"], "title": "Exercício isolado",
    }).json()
    started = client.post(
        f"/api/v1/exercises/{exercise['id']}/start", headers=headers,
        json={"incident_type": "exposicao_acidental"},
    )
    assert started.status_code == 200

    unauthorized = client.get("/api/v1/companies")
    assert unauthorized.status_code == 401
    assert client.post("/api/v1/auth/token", json={"email": "admin@test.cybersim.local", "password": "incorreta"}).status_code == 401

    for role, email in [("facilitator", "faci@tenant-b.local"), ("participant", "part@tenant-a.local")]:
        created_user = client.post("/api/v1/admin/users", headers=headers, json={
            "email": email, "password": "TenantTest!Password2026", "role": role,
            "company_id": company_b["id"] if role == "facilitator" else company_a["id"],
        })
        assert created_user.status_code == 201, created_user.text

    facilitator = _login(client, "faci@tenant-b.local", "TenantTest!Password2026")
    company_list = client.get("/api/v1/companies", headers=facilitator).json()
    assert [row["id"] for row in company_list] == [company_b["id"]]
    assert client.get(f"/api/v1/exercises/{exercise['id']}", headers=facilitator).status_code == 404
    scoped_export = client.get("/api/v1/analytics/export", headers=facilitator)
    assert scoped_export.status_code == 200
    with ZipFile(io.BytesIO(scoped_export.content)) as archive:
        company_csv = archive.read("dim_empresa.csv").decode("utf-8-sig")
        assert company_b["id"] in company_csv
        assert company_a["id"] not in company_csv

    participant = _login(client, "part@tenant-a.local", "TenantTest!Password2026")
    assert client.post(
        f"/api/v1/exercises/{exercise['id']}/start", headers=participant, json={}
    ).status_code == 403
    participant_detail = client.get(f"/api/v1/exercises/{exercise['id']}", headers=participant).json()
    assert participant_detail["scenario"]["facilitator_notes"] is None
    narrator_result = next(
        row["result"] for row in client.get(
            f"/api/v1/exercises/{exercise['id']}/agents", headers=participant
        ).json() if row["agent_name"] == "narrator"
    )
    assert "facilitator_notes" not in narrator_result
    assert all("facilitator_notes" not in inject for inject in narrator_result["injects"])
    assert client.post(
        f"/api/v1/exercises/{exercise['id']}/injects/release-next",
        headers=participant, json={},
    ).status_code == 403
