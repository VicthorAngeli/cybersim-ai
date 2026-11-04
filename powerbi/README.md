# CyberSim AI — relatório Power BI

O projeto inclui um relatório **PBIP/PBIR** com modelo semântico **TMDL**, em português brasileiro, pronto para abrir no Power BI Desktop. Os dados demonstrativos são incorporados às partições M do modelo durante a geração; nenhum serviço pago ou caminho local de CSV é necessário para abrir o relatório.

## Abrir o projeto

Abra [`CyberSim AI.pbip`](CyberSim%20AI.pbip) no Power BI Desktop. O relatório contém seis páginas:

- Executiva
- Linha do tempo
- Operação SOC
- LGPD e comunicação
- Lições aprendidas
- Inteligência Artificial

O modelo contém 15 tabelas, medidas DAX e relações dimensionais unidirecionais. As seis páginas compartilham filtros de empresa, período, cenário, dificuldade e status, fundo cinza-azulado, cartões brancos arredondados, sombras discretas e uma paleta de seis cores inspirada na referência visual. As métricas legais e de ANPD são indicativas da simulação, não uma conclusão de conformidade.

## Atualizar dados

Os CSVs em `powerbi/exports` são a fonte dos snapshots usados para gerar o modelo. Após substituir o pacote completo por uma nova exportação, execute `build_pbip.py` novamente para incorporar os dados atualizados e reabra o projeto no Power BI Desktop. Mantenha nomes de arquivos, colunas e chaves substitutas.

Para gerar uma exportação:

1. Inicie a API e autentique-se, ou obtenha um JWT em `POST /api/v1/auth/token`.
2. Solicite `GET /api/v1/analytics/export` com o cabeçalho `Authorization: Bearer <JWT>` e baixe o ZIP `cybersim-powerbi-csv.zip`. A resposta inclui `X-Export-Record-Count`.
3. Extraia todos os CSVs e substitua o pacote completo, preservando as chaves substitutas.
4. Para exportar diretamente do banco local, execute `python -m scripts.export_powerbi`. Use `--output "C:\dados\cybersim"` para escolher o destino. Para a demonstração, execute primeiro `python -m scripts.seed_demo`.

## Construir e validar

Após alterar o modelo ou as páginas, execute na raiz do workspace:

```powershell
.\.venv\Scripts\python.exe .\powerbi\scripts\build_pbip.py
.\.venv\Scripts\python.exe .\powerbi\scripts\validate_pbip.py
```

O validador verifica os JSONs contra os schemas oficiais publicados pela Microsoft, referências de campos/medidas, integridade das chaves, GUIDs duplicados, ciclos/caminhos ambíguos e se as partições TMDL não dependem de arquivos locais. A validação final do TMDL deve ser conferida no Power BI Desktop.

## Alternativa: importar CSV manualmente

1. No Power BI Desktop, escolha **Obter dados → Texto/CSV**.
2. Selecione os 15 arquivos `dim_*.csv` e `fato_*.csv`.
3. Confirme a origem como UTF-8 (65001) para preservar acentuação.
4. Confira os tipos: chaves, contagens, sequência, score, latência e tokens como inteiros; datas ISO como Data ou Data/Hora; indicadores binários como inteiros 0/1.
5. Carregue as tabelas, crie as relações documentadas em [relationships.md](documentation/relationships.md), copie as medidas de [measures.dax](dax/measures.dax) e importe [cybersim-theme.json](theme/cybersim-theme.json).
6. Salve como `.pbix` somente pelo Power BI Desktop.

## Modelo e privacidade

Veja [relationships.md](documentation/relationships.md) para granularidade e chaves e [report_pages.md](documentation/report_pages.md) para a descrição analítica das páginas. Os CSVs são snapshots; mantenha o pacote inteiro sincronizado para evitar chaves órfãs. O modelo não exibe dados pessoais. A coluna de comunicação possível à ANPD é exclusivamente simulada e não deve ser interpretada como decisão legal.

`sql/analytical_views.sql` contém views analíticas para uma eventual conexão PostgreSQL. Se usar essa alternativa, utilize credenciais autorizadas e uma conta somente leitura.
