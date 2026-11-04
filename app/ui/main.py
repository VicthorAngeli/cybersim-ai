import streamlit as st

from app.ui.api_client import api_request

st.set_page_config(page_title="CyberSim AI", page_icon="🛡️", layout="wide")
st.markdown(
    """
    <style>
    :root {
        --navy: #101B2D;
        --blue: #2463EB;
        --blue-soft: #E8F0FE;
        --green: #16A36A;
        --orange: #E99A28;
        --red: #D64545;
        --ink: #17243A;
        --muted: #667085;
        --line: #E4EAF2;
        --surface: #FFFFFF;
        --canvas: #F4F7FB;
    }
    .stApp { background: var(--canvas); color: var(--ink); }
    [data-testid="stHeader"] { background: rgba(244,247,251,.92); }
    [data-testid="stMainBlockContainer"] { padding-top: 1.5rem; padding-bottom: 3rem; max-width: 1440px; }
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #101B2D 0%, #172943 100%); border-right: 1px solid #263650; }
    [data-testid="stSidebar"] * { color: #F5F8FC; }
    [data-testid="stSidebar"] [role="radiogroup"] label { padding: .55rem .65rem; border-radius: 9px; }
    [data-testid="stSidebar"] [role="radiogroup"] label:hover { background: rgba(255,255,255,.09); }
    .brand { color: var(--blue); font-size: 2rem; font-weight: 800; letter-spacing: -.04em; margin-bottom: .15rem; }
    .subtle { color: var(--muted); }
    .app-topbar {
        display: flex; justify-content: space-between; align-items: center;
        padding: .8rem 1.05rem; margin: 0 0 1.35rem;
        background: var(--surface); border: 1px solid var(--line); border-radius: 14px;
        box-shadow: 0 3px 14px rgba(16,27,45,.04);
    }
    .app-topbar-brand { color: var(--navy); font-size: 1.15rem; font-weight: 800; letter-spacing: -.025em; }
    .app-topbar-label { color: var(--muted); font-size: .82rem; }
    h1, h2, h3 { color: var(--navy); letter-spacing: -.025em; }
    h1 { font-weight: 780; }
    div[data-testid="stMetric"] {
        background: var(--surface); border: 1px solid var(--line); padding: 1.05rem 1.15rem;
        border-radius: 14px; box-shadow: 0 4px 16px rgba(16,27,45,.045);
    }
    div[data-testid="stMetricLabel"] { color: var(--muted); font-weight: 600; }
    div[data-testid="stMetricValue"] { color: var(--navy); font-weight: 780; }
    div[data-testid="stForm"], div[data-testid="stExpander"], div[data-testid="stAlert"] {
        border-radius: 12px;
    }
    div[data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 12px; overflow: hidden; }
    div[data-testid="stTabs"] button[role="tab"] { font-weight: 650; }
    .stButton > button, [data-testid="stFormSubmitButton"] > button {
        border-radius: 9px; font-weight: 650; transition: all .15s ease;
    }
    .stButton > button[kind="primary"], [data-testid="stFormSubmitButton"] > button[kind="primary"] {
        background: var(--blue); border-color: var(--blue);
    }
    .stButton > button:hover { border-color: var(--blue); color: var(--blue); }
    [data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea,
    [data-testid="stSelectbox"] [data-baseweb="select"] > div,
    [data-testid="stNumberInput"] input { border-radius: 9px; }
    .login-shell { max-width: 460px; margin: 9vh auto 0; }
    .login-mark {
        display: inline-flex; align-items: center; justify-content: center;
        width: 52px; height: 52px; border-radius: 15px; color: white;
        background: linear-gradient(135deg, #2463EB, #61A1FF);
        font-size: 1.45rem; box-shadow: 0 8px 24px rgba(36,99,235,.25);
    }
    .login-title { color: var(--navy); font-size: 2.2rem; font-weight: 820; letter-spacing: -.05em; margin: .8rem 0 .2rem; }
    .login-subtitle { color: var(--muted); margin: 0 0 1.2rem; line-height: 1.55; }
    .notice { border-left: 4px solid var(--orange); background: #FFF8E8; padding: 12px; border-radius: 8px; }
    @media (max-width: 760px) {
        [data-testid="stMainBlockContainer"] { padding: 1rem .75rem 2rem; }
        .app-topbar { margin-bottom: .9rem; }
        div[data-testid="stMetric"] { padding: .8rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def _show_error(payload: object) -> None:
    st.error(str(payload))


def _rows(path: str) -> list[dict]:
    ok, data = api_request("GET", path)
    if not ok:
        _show_error(data)
        return []
    return data if isinstance(data, list) else []


def _companies() -> list[dict]:
    return _rows("/api/v1/companies")


def _exercises() -> list[dict]:
    return _rows("/api/v1/exercises")


def _login() -> bool:
    _, center, _ = st.columns([1, 1.25, 1])
    with center:
        st.markdown(
            '<div class="login-shell"><div class="login-mark">✦</div>'
            '<div class="login-title">CyberSim AI</div>'
            '<div class="login-subtitle">Treine a resposta a crises cibernéticas em um ambiente '
            'seguro, fictício e colaborativo.</div></div>',
            unsafe_allow_html=True,
        )
        with st.container(border=True):
            st.subheader("Acessar plataforma")
            with st.form("login"):
                email = st.text_input("E-mail", placeholder="nome@empresa.com")
                password = st.text_input("Senha", type="password")
                submitted = st.form_submit_button("Entrar", type="primary", use_container_width=True)
    if submitted:
        ok, result = api_request("POST", "/api/v1/auth/token", json={"email": email, "password": password})
        if ok and isinstance(result, dict):
            st.session_state.access_token = result["access_token"]
            st.rerun()
        _show_error(result)
    if not st.session_state.get("access_token"):
        st.caption("Simulação exclusivamente para treinamento. Nenhum sistema real é acessado.")
    return False


if not st.session_state.get("access_token"):
    _login()
    st.stop()

ok, profile = api_request("GET", "/api/v1/auth/me")
if not ok:
    st.session_state.pop("access_token", None)
    _show_error(profile)
    st.rerun()

profile = profile if isinstance(profile, dict) else {}
st.sidebar.markdown(
    '<div style="font-size:1.35rem;font-weight:800;letter-spacing:-.04em;padding:.35rem 0">'
    '<span style="color:#76A7FF">✦</span> CyberSim <span style="color:#76A7FF">AI</span></div>',
    unsafe_allow_html=True,
)
st.sidebar.caption(f"{profile.get('email', '')} · {profile.get('role', '')}")
if st.sidebar.button("Sair", use_container_width=True):
    st.session_state.pop("access_token", None)
    st.rerun()

pages = [
    "Visão geral", "Empresas", "Novo exercício", "Cenário", "Sala de simulação",
    "Análises dos agentes", "Lições aprendidas", "Relatório final",
    "Power BI", "Administração",
]
page = st.sidebar.radio("Navegação", pages)
st.markdown(
    '<div class="app-topbar"><span class="app-topbar-brand">CyberSim AI</span>'
    '<span class="app-topbar-label">AMBIENTE DE TREINAMENTO&nbsp;&nbsp;·&nbsp;&nbsp;DADOS FICTÍCIOS</span></div>',
    unsafe_allow_html=True,
)


def show_home() -> None:
    st.title("Visão geral")
    ok, summary = api_request("GET", "/api/v1/analytics/summary")
    if not ok:
        _show_error(summary)
        return
    values = summary if isinstance(summary, dict) else {}
    cols = st.columns(5)
    labels = [
        ("Exercícios", "total_exercises"), ("Concluídos", "completed_exercises"),
        ("Em andamento", "in_progress_exercises"), ("Decisões", "decisions"),
        ("Ações pendentes", "pending_actions"),
    ]
    for column, (label, key) in zip(cols, labels):
        column.metric(label, values.get(key, 0))
    st.subheader("Atividade recente")
    recent = _rows("/api/v1/analytics/recent")
    if recent:
        st.dataframe(recent, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum exercício registrado ainda.")
    st.caption(f"Execuções de agentes: {values.get('agent_runs', 0)} · Comunicações aguardando aprovação: {values.get('pending_communications', 0)}")


def show_companies() -> None:
    st.title("Empresas")
    if profile.get("role") == "admin":
        with st.expander("Cadastrar empresa de treinamento"):
            with st.form("company_create"):
                name = st.text_input("Nome")
                segment = st.text_input("Segmento")
                size = st.selectbox("Porte", ["Micro", "Pequeno", "Médio", "Grande"])
                employee_count = st.number_input("Colaboradores", min_value=1, value=20)
                location = st.text_input("Localização geral")
                systems = st.text_input("Sistemas críticos (separados por vírgula)")
                suppliers = st.text_input("Dependências de fornecedores (separadas por vírgula)")
                categories = st.text_input("Categorias de dados (separadas por vírgula)")
                processes = st.text_input("Processos essenciais (separados por vírgula)")
                maturity = st.selectbox("Maturidade declarada", ["Inicial", "Em desenvolvimento", "Definida", "Avançada"])
                submitted = st.form_submit_button("Salvar empresa")
            if submitted:
                payload = {
                    "name": name, "segment": segment, "size": size,
                    "employee_count": int(employee_count), "location": location or None,
                    "critical_systems": [item.strip() for item in systems.split(",") if item.strip()],
                    "suppliers": [item.strip() for item in suppliers.split(",") if item.strip()],
                    "data_categories": [item.strip() for item in categories.split(",") if item.strip()],
                    "essential_processes": [item.strip() for item in processes.split(",") if item.strip()],
                    "security_maturity": maturity,
                }
                ok, result = api_request("POST", "/api/v1/companies", json=payload)
                st.success("Empresa cadastrada.") if ok else _show_error(result)
    companies = _companies()
    if companies:
        st.dataframe(companies, use_container_width=True, hide_index=True)
    else:
        st.info("Cadastre ou solicite acesso a uma empresa de treinamento.")


def show_new_exercise() -> None:
    st.title("Novo exercício")
    companies = _companies()
    if not companies:
        st.warning("Cadastre uma empresa antes de criar um exercício.")
        return
    with st.form("exercise_create"):
        company = st.selectbox("Empresa", companies, format_func=lambda item: item["name"])
        title = st.text_input("Nome do exercício", "Exercício de resposta a incidente")
        incident_type = st.selectbox("Tipo de incidente", [
            "exposicao_acidental", "comprometimento_conta", "indisponibilidade_sistema",
            "fornecedor_terceirizado", "nuvem_indisponivel",
        ])
        difficulty = st.selectbox("Dificuldade", ["Inicial", "Intermediário", "Avançado"])
        duration = st.slider("Duração planejada (minutos)", 30, 120, 60, step=15)
        participant_count = st.number_input("Quantidade de participantes", 1, 500, 4)
        objectives = st.text_area("Objetivos (um por linha)", "Praticar escalonamento\nRegistrar decisões")
        areas = st.text_input("Áreas envolvidas (separadas por vírgula)", "TI, Segurança, Jurídico")
        systems = st.text_input("Sistemas hipoteticamente afetados (separados por vírgula)", ", ".join(company.get("critical_systems", [])))
        categories = st.text_input("Categorias de dados (separadas por vírgula)", ", ".join(company.get("data_categories", [])))
        submitted = st.form_submit_button("Criar exercício", type="primary")
    if submitted:
        payload = {
            "company_id": company["id"], "title": title, "incident_type": incident_type,
            "difficulty": difficulty, "planned_duration": duration,
            "participant_count": participant_count,
            "objectives": [item.strip() for item in objectives.splitlines() if item.strip()],
            "areas": [item.strip() for item in areas.split(",") if item.strip()],
            "affected_systems": [item.strip() for item in systems.split(",") if item.strip()],
            "data_categories": [item.strip() for item in categories.split(",") if item.strip()],
        }
        ok, result = api_request("POST", "/api/v1/exercises", json=payload)
        if ok and isinstance(result, dict):
            st.session_state.selected_exercise_id = result["id"]
            st.success(f"Exercício criado: {result['id']}")
        else:
            _show_error(result)


def show_scenario() -> None:
    st.title("Geração do cenário")
    exercises = _exercises()
    if not exercises:
        st.info("Crie um exercício para gerar um cenário.")
        return
    exercise = st.selectbox("Exercício", exercises, format_func=lambda item: item["title"], key="scenario_select")
    ok, detail = api_request("GET", f"/api/v1/exercises/{exercise['id']}")
    scenario = None
    if ok and isinstance(detail, dict):
        scenario = detail.get("scenario")
        if scenario:
            st.subheader(scenario["name"])
            st.write(scenario["executive_summary"])
            st.write(f"Dificuldade: **{scenario['difficulty']}** · Injects: **{scenario['inject_count']}**")
            for entry in scenario.get("timeline", []):
                st.write(f"- {entry}")
            st.write("**Objetivos**")
            for objective in scenario["learning_objectives"]:
                st.write(f"- {objective}")
            if scenario.get("facilitator_notes"):
                with st.expander("Notas reservadas ao facilitador"):
                    st.warning(scenario["facilitator_notes"])
        else:
            st.info("O cenário ainda não foi gerado.")
    elif not ok:
        _show_error(detail)
    if exercise["status"] == "planejado":
        generate_label = "Regenerar cenário" if scenario else "Gerar cenário"
        if st.button(generate_label, type="primary"):
            ok, result = api_request(
                "POST", f"/api/v1/exercises/{exercise['id']}/scenario/generate",
                json={"incident_type": exercise["incident_type"]},
            )
            if ok:
                st.success("Cenário validado e salvo. Pode regenerá-lo antes de iniciar.")
                st.rerun()
            _show_error(result)
        if scenario and st.button("Iniciar exercício"):
            ok, result = api_request("POST", f"/api/v1/exercises/{exercise['id']}/start", json={})
            if ok:
                st.success("Exercício iniciado. A liberação de injects permanece manual.")
                st.rerun()
            _show_error(result)


def show_simulation() -> None:
    st.title("Sala de simulação")
    exercises = _exercises()
    if not exercises:
        st.info("Nenhum exercício cadastrado.")
        return
    index = next(
        (i for i, item in enumerate(exercises) if item["id"] == st.session_state.get("selected_exercise_id")),
        0,
    )
    exercise = st.selectbox("Exercício ativo", exercises, index=index,
                            format_func=lambda item: f"{item['title']} — {item['status']}")
    st.session_state.selected_exercise_id = exercise["id"]
    ok, detail = api_request("GET", f"/api/v1/exercises/{exercise['id']}")
    if not ok or not isinstance(detail, dict):
        _show_error(detail)
        return
    st.caption(f"Status: **{detail['status']}** · Duração planejada: {detail['planned_duration']} min")
    if detail.get("status") == "planejado":
        scenario = detail.get("scenario")
        if scenario:
            st.subheader(scenario["name"])
            st.write(scenario["executive_summary"])
            if st.button("Iniciar exercício", type="primary"):
                ok, result = api_request("POST", f"/api/v1/exercises/{exercise['id']}/start", json={})
                if ok:
                    st.success("Exercício iniciado. Libere o primeiro acontecimento quando os participantes estiverem prontos.")
                    st.rerun()
                _show_error(result)
            if st.button("Regenerar cenário"):
                ok, result = api_request(
                    "POST", f"/api/v1/exercises/{exercise['id']}/scenario/generate",
                    json={"incident_type": exercise["incident_type"]},
                )
                if ok:
                    st.success("Cenário regenerado.")
                    st.rerun()
                _show_error(result)
        elif st.button("Gerar cenário", type="primary"):
            ok, result = api_request(
                "POST", f"/api/v1/exercises/{exercise['id']}/scenario/generate",
                json={"incident_type": exercise["incident_type"]},
            )
            if ok:
                st.success("Cenário gerado. Revise-o antes de iniciar.")
                st.rerun()
            _show_error(result)
        return
    if detail.get("scenario", {}).get("facilitator_notes"):
        with st.expander("Notas reservadas ao facilitador"):
            st.warning(detail["scenario"]["facilitator_notes"])
    tabs = st.tabs(["SOC", "LGPD", "Comunicação", "Decisões", "Histórico"])
    current_events = detail.get("released_injects", [])
    next_sequence = len(current_events) + 1
    with tabs[4]:
        for event in current_events:
            st.markdown(f"**{event['sequence']}. {event['title']}** · {event['severity']}")
            st.write(event["description"])
    if detail["status"] == "em_andamento":
        if st.button(f"Liberar próximo acontecimento ({next_sequence})", type="primary",
                     disabled=next_sequence > (detail.get("scenario") or {}).get("inject_count", 5)):
            ok, result = api_request("POST", f"/api/v1/exercises/{exercise['id']}/injects/release-next", json={})
            if ok:
                st.success("Acontecimento liberado e análises concluídas.")
                st.rerun()
            _show_error(result)
        if current_events:
            event = current_events[-1]
            st.subheader(f"Inject {event['sequence']} — {event['title']}")
            st.write(event["description"])
            with st.form("decision_form"):
                decision = st.text_area("Decisão registrada pelos participantes")
                rationale = st.text_area("Justificativa e evidências")
                responsible = st.text_input("Responsável por função")
                submitted = st.form_submit_button("Registrar decisão")
            if submitted:
                ok, result = api_request("POST", f"/api/v1/exercises/{exercise['id']}/decisions", json={
                    "inject_event_id": event["id"], "description": decision,
                    "rationale": rationale, "responsible_role": responsible or None,
                })
                st.success("Decisão registrada.") if ok else _show_error(result)
    with tabs[0]:
        _show_agent_results(exercise["id"], {"soc"})
    with tabs[1]:
        _show_agent_results(exercise["id"], {"legal"})
        st.caption("Triagem indicativa; revisão humana pelo DPO/advogado é obrigatória.")
    with tabs[2]:
        _show_agent_results(exercise["id"], {"communications"})
        st.caption("Todos os textos são rascunhos; nenhum envio externo é realizado.")
    with tabs[3]:
        st.json(detail.get("decisions", []))
    if detail["status"] == "em_andamento" and st.button("Finalizar exercício", type="secondary"):
        ok, result = api_request("POST", f"/api/v1/exercises/{exercise['id']}/complete")
        if ok:
            st.success("Relatório de lições aprendidas consolidado.")
            st.rerun()
        _show_error(result)


def _show_agent_results(exercise_id: str, names: set[str]) -> None:
    runs = _rows(f"/api/v1/exercises/{exercise_id}/agents")
    filtered = [run for run in runs if run["agent_name"] in names]
    if not filtered:
        st.info("Nenhuma análise deste agente foi executada.")
    for run in filtered:
        with st.expander(f"{run['agent_role']} · {run['status']} · {run['latency_ms']} ms", expanded=True):
            st.caption(f"Validada pelo schema: {run['validated']} · {run['started_at']}")
            st.json(run["result"])


def show_agents() -> None:
    st.title("Análises dos agentes")
    exercises = _exercises()
    if not exercises:
        st.info("Nenhum exercício disponível.")
        return
    exercise = st.selectbox("Exercício", exercises, format_func=lambda item: item["title"], key="agent_exercise")
    _show_agent_results(exercise["id"], {"narrator", "soc", "legal", "communications", "consolidator"})


def show_lessons() -> None:
    st.title("Lições aprendidas e plano de melhoria")
    exercises = _exercises()
    if not exercises:
        st.info("Nenhum exercício disponível.")
        return
    exercise = st.selectbox("Exercício", exercises, format_func=lambda item: item["title"], key="lesson_exercise")
    ok_detail, detail = api_request("GET", f"/api/v1/exercises/{exercise['id']}")
    if ok_detail and isinstance(detail, dict) and detail.get("objectives"):
        st.subheader("Avaliação humana dos objetivos (0–4)")
        st.caption("0 Não abordado · 1 Abordado sem decisão · 2 Decisão proposta · 3 Responsável e prazo definidos · 4 Validação documentada. Atribuição humana, baseada em evidências.")
        objectives = detail["objectives"]
        with st.form("objective_assessment"):
            objective = st.selectbox(
                "Objetivo",
                objectives,
                format_func=lambda item: item["name"],
            )
            score = st.select_slider("Nível observado", options=[0, 1, 2, 3, 4], value=0)
            evidence_options = [
                (event["id"], f"Inject {event['sequence']}: {event['title']}")
                for event in detail.get("released_injects", [])
            ] + [
                (decision["id"], f"Decisão: {decision['description'][:80]}")
                for decision in detail.get("decisions", [])
            ]
            selected_evidence = st.multiselect(
                "Evidências deste exercício",
                evidence_options,
                format_func=lambda item: item[1],
            )
            submitted_assessment = st.form_submit_button("Salvar avaliação")
        if submitted_assessment:
            ok, result = api_request(
                "POST", f"/api/v1/exercises/{exercise['id']}/objectives/assessments",
                json={
                    "objective_id": objective["id"],
                    "score": score,
                    "evidence_ids": [item[0] for item in selected_evidence],
                },
            )
            st.success("Avaliação registrada com evidências.") if ok else _show_error(result)
    elif not ok_detail:
        _show_error(detail)
    ok, data = api_request("GET", f"/api/v1/exercises/{exercise['id']}/insights")
    if not ok or not isinstance(data, dict):
        _show_error(data)
        return
    st.subheader("Ações de melhoria")
    actions = data.get("actions", [])
    if not actions:
        st.info("Nenhuma ação consolidada. Revise as decisões e o relatório final.")
    for action in actions:
        cols = st.columns([4, 1, 2, 1])
        cols[0].write(action["description"])
        cols[1].write(action["priority"])
        cols[2].write(action["responsible_role"] or "Função não definida")
        choice = cols[3].selectbox("Status", ["pendente", "em_andamento", "concluida", "cancelada"],
                                  index=["pendente", "em_andamento", "concluida", "cancelada"].index(action["status"]),
                                  key=f"action_{action['id']}", label_visibility="collapsed")
        if choice != action["status"] and cols[3].button("Salvar", key=f"save_{action['id']}"):
            ok, result = api_request("PATCH", f"/api/v1/exercises/{exercise['id']}/actions/{action['id']}",
                                     json={"status": choice})
            st.success("Status atualizado.") if ok else _show_error(result)
    st.subheader("Comunicações (rascunhos)")
    for draft in data.get("communications", []):
        with st.expander(f"{draft['audience']} · {draft['approval_status']}"):
            st.write(draft["message"])
            st.caption("Aprovação e envio permanecem responsabilidade humana; envio automático desativado.")
            if profile.get("role") in {"admin", "facilitator"} and draft["approval_status"] not in {"aprovado", "rejeitado"}:
                rationale = st.text_input("Justificativa da revisão", key=f"approval_reason_{draft['id']}")
                approve_col, reject_col = st.columns(2)
                for column, status_value, label in [
                    (approve_col, "aprovado", "Aprovar rascunho"),
                    (reject_col, "rejeitado", "Rejeitar rascunho"),
                ]:
                    if column.button(label, key=f"{status_value}_{draft['id']}"):
                        ok, result = api_request(
                            "PATCH",
                            f"/api/v1/exercises/{exercise['id']}/communications/{draft['id']}",
                            json={"status": status_value, "rationale": rationale},
                        )
                        st.success("Revisão registrada; nenhum envio foi realizado.") if ok else _show_error(result)


def show_report() -> None:
    st.title("Relatório final")
    exercises = _exercises()
    if not exercises:
        st.info("Nenhum exercício disponível.")
        return
    exercise = st.selectbox("Exercício concluído", exercises, format_func=lambda item: item["title"], key="report_exercise")
    if exercise["status"] != "concluido":
        st.warning("Finalize o exercício antes de gerar o relatório.")
        return
    ok, report = api_request("GET", f"/api/v1/exercises/{exercise['id']}/report")
    if not ok or not isinstance(report, dict):
        _show_error(report)
        return
    st.subheader("Resumo executivo")
    st.write(report.get("executive_summary", ""))
    st.markdown("### Pontos de melhoria")
    for item in report.get("improvement_areas", []):
        st.write(f"- {item}")
    st.markdown("### Recomendações")
    for item in report.get("recommendations", []):
        st.write(f"- {item}")
    for export_format in ("markdown", "html"):
        ok, content = api_request("GET", f"/api/v1/exercises/{exercise['id']}/report?format={export_format}")
        if ok and isinstance(content, bytes):
            st.download_button(f"Baixar relatório {export_format.upper()}", content,
                               file_name=f"cybersim-{exercise['id']}.{ 'md' if export_format == 'markdown' else 'html' }",
                               mime="text/markdown" if export_format == "markdown" else "text/html")
        elif not ok:
            _show_error(content)


def show_powerbi() -> None:
    st.title("Exportação para Microsoft Power BI")
    st.write("Baixe a camada analítica em esquema estrela, com CSV UTF-8 BOM e chaves de relacionamento.")
    st.caption("Os dados exportados não incluem nomes de participantes nem credenciais.")
    if st.button("Gerar e baixar pacote CSV", type="primary"):
        ok, content = api_request("GET", "/api/v1/analytics/export")
        if ok and isinstance(content, bytes):
            st.download_button("Baixar ZIP Power BI", content, "cybersim-powerbi-csv.zip", "application/zip")
        elif not ok:
            _show_error(content)
    st.markdown("Manual completo em `powerbi/documentation` e medidas DAX em `powerbi/dax`.")


def show_admin() -> None:
    st.title("Administração")
    if profile.get("role") != "admin":
        st.warning("Acesso restrito ao perfil administrador.")
        return
    tab_users, tab_settings, tab_audit, tab_calendar = st.tabs(["Usuários", "IA", "Auditoria", "Calendário"])
    with tab_users:
        with st.form("user_create"):
            email = st.text_input("E-mail")
            password = st.text_input("Senha (mínimo 12 caracteres)", type="password")
            role = st.selectbox("Perfil", ["admin", "facilitator", "participant", "viewer"])
            companies = _companies()
            company = st.selectbox("Empresa", [None, *companies],
                                   format_func=lambda item: "Sem vínculo" if item is None else item["name"])
            submitted = st.form_submit_button("Criar usuário")
        if submitted:
            ok, result = api_request("POST", "/api/v1/admin/users", json={
                "email": email, "password": password, "role": role,
                "company_id": company["id"] if company else None,
            })
            st.success("Usuário criado.") if ok else _show_error(result)
        users = _rows("/api/v1/admin/users")
        st.dataframe(users, use_container_width=True, hide_index=True)
    with tab_settings:
        ok, settings = api_request("GET", "/api/v1/admin/settings")
        if ok:
            status_col, model_col, limit_col = st.columns(3)
            status_col.metric("Provedor ativo", settings.get("llm_provider", "não informado"))
            model_col.metric("Modelo", settings.get("openai_model", "não informado"))
            limit_col.metric("Chave configurada", "Sim" if settings.get("openai_api_key_configured") else "Não")
            st.caption(
                f"Timeout: {settings.get('timeout_seconds')} s · "
                f"Tentativas: {settings.get('max_retries')} · "
                f"Máximo por chamada: {settings.get('max_tokens_per_call')} tokens"
            )
            st.info(
                "Para configurar o provedor, edite OPENAI_API_KEY e LLM_PROVIDER no arquivo .env local "
                "e reinicie a API. Nunca cole chaves nesta interface, em chats ou no código. "
                "Se uma chave foi compartilhada, revogue-a e gere outra."
            )
        else:
            _show_error(settings)
    with tab_audit:
        logs = _rows("/api/v1/admin/audit")
        st.dataframe(logs, use_container_width=True, hide_index=True) if logs else st.info("Sem registros.")
    with tab_calendar:
        companies = _companies()
        with st.form("holiday"):
            holiday_date = st.date_input("Feriado")
            description = st.text_input("Descrição")
            company = st.selectbox("Empresa", companies, format_func=lambda item: item["name"]) if companies else None
            submitted = st.form_submit_button("Adicionar feriado")
        if submitted:
            ok, result = api_request("POST", "/api/v1/admin/calendar", json={
                "holiday_date": holiday_date.isoformat(), "description": description,
                "company_id": company["id"] if company else None,
            })
            st.success("Feriado incluído.") if ok else _show_error(result)
        holidays = _rows("/api/v1/admin/calendar")
        st.dataframe(holidays, use_container_width=True, hide_index=True) if holidays else st.info("Calendário sem feriados configurados.")


dispatch = {
    "Visão geral": show_home,
    "Empresas": show_companies,
    "Novo exercício": show_new_exercise,
    "Cenário": show_scenario,
    "Sala de simulação": show_simulation,
    "Análises dos agentes": show_agents,
    "Lições aprendidas": show_lessons,
    "Relatório final": show_report,
    "Power BI": show_powerbi,
    "Administração": show_admin,
}
dispatch[page]()
