from app.schemas.agents import ScenarioInjectOutput, ScenarioOutput


_BASE_QUESTIONS = [
    "Quais informações estão confirmadas e quais ainda precisam ser verificadas?",
    "Quem deve tomar a próxima decisão e como ela será registrada?",
    "Como manter os processos essenciais durante a avaliação?",
]


def get_demo_scenario(company: dict, incident_type: str, difficulty: str) -> ScenarioOutput:
    name, intro, personal_data, outage = {
        "comprometimento_conta": (
            "Conta corporativa sob suspeita",
            "Relatos fictícios indicam atividade incomum em uma conta corporativa.",
            False, False,
        ),
        "indisponibilidade_sistema": (
            "Sistema crítico indisponível",
            "Uma equipe relata indisponibilidade inesperada de um sistema essencial.",
            False, True,
        ),
        "exposicao_acidental": (
            "Exposição acidental e serviço crítico",
            "Um aviso fictício aponta possível exposição de informações de clientes enquanto um serviço crítico apresenta instabilidade.",
            True, True,
        ),
        "fornecedor_terceirizado": (
            "Incidente comunicado por fornecedor",
            "Um fornecedor informa um incidente que pode afetar serviços utilizados pela empresa.",
            True, True,
        ),
        "nuvem_indisponivel": (
            "Indisponibilidade de serviço em nuvem",
            "Um serviço em nuvem essencial apresenta indisponibilidade hipotética.",
            False, True,
        ),
    }.get(incident_type, (
        "Exercício de resposta a incidente",
        "Uma situação cibernética fictícia exige coordenação e decisões documentadas.",
        False, False,
    ))
    systems = company.get("critical_systems", []) or ["sistema corporativo crítico"]
    categories = company.get("data_categories", []) or ["informações de clientes"]
    stages = [
        ("INJECT 1 — ALERTA INICIAL", "Uma pessoa relata dificuldade de acesso a um serviço corporativo importante.", False, outage),
        ("INJECT 2 — AGRAVAMENTO", "Outras áreas informam impacto operacional e solicitam orientação.", False, outage),
        ("INJECT 3 — POSSÍVEL EXPOSIÇÃO", f"Surge uma evidência fictícia de que {categories[0]} pode ter sido acessada indevidamente.", personal_data, False),
        ("INJECT 4 — PRESSÃO EXTERNA", "A diretoria recebe questionamentos de clientes e parceiros; os fatos ainda estão sendo apurados.", personal_data, False),
        ("INJECT 5 — RECUPERAÇÃO", "A equipe deve priorizar continuidade, comunicação aprovada e acompanhamento das medidas.", personal_data, outage),
    ]
    injects = [
        ScenarioInjectOutput(
            sequence=index,
            title=title,
            description=description,
            questions=_BASE_QUESTIONS,
            facilitator_notes=f"Nota reservada ao facilitador: adaptar a discussão aos sistemas {', '.join(systems)}. Não revelar resposta esperada.",
            involves_personal_data=contains_data,
            involves_outage=contains_outage,
            requires_communication=index >= 4,
        )
        for index, (title, description, contains_data, contains_outage) in enumerate(stages, start=1)
    ]
    return ScenarioOutput(
        name=name,
        executive_summary=f"{intro} Exercício exclusivamente fictício, adaptado ao contexto de {company.get('name', 'empresa')} (setor {company.get('segment', 'não informado')}).",
        incident_type=incident_type,
        context={
            "segmento": company.get("segment", "não informado"),
            "sistemas": ", ".join(systems),
            "dados": ", ".join(categories),
            "origem": "Cenário de treinamento; sem interação com sistemas reais.",
        },
        affected_assets=[*systems, "processos de atendimento e continuidade"],
        difficulty=difficulty,
        learning_objectives=[
            "Praticar classificação e escalonamento de incidentes.",
            "Registrar decisões, responsáveis e evidências.",
            "Avaliar continuidade operacional e comunicação.",
            "Identificar pontos para revisão de privacidade e proteção de dados.",
        ],
        timeline=[f"{(index - 1) * 10} min — {inject.title}" for index, inject in enumerate(injects, start=1)],
        injects=injects,
        facilitator_notes="Material reservado ao facilitador. Todas as ocorrências, organizações e evidências são fictícias.",
        demo_data=True,
    )
