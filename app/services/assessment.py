ASSESSMENT_CRITERIA = (
    ("Identificação do incidente", "Detect"),
    ("Classificação do incidente", "Respond"),
    ("Comunicação interna", "Respond"),
    ("Escalonamento", "Govern"),
    ("Preservação de evidências", "Respond"),
    ("Contenção", "Respond"),
    ("Continuidade operacional", "Protect"),
    ("Avaliação LGPD", "Govern"),
    ("Comunicação externa", "Respond"),
    ("Recuperação", "Recover"),
)

ASSESSMENT_SCALE = {
    0: "Não abordado",
    1: "Abordado, sem decisão",
    2: "Decisão ou ação proposta",
    3: "Responsável e prazo definidos",
    4: "Validação documentada no exercício",
}
