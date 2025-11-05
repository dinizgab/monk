# Monk – Tradução de Linguagem Natural para SQL Federado

## Visão Geral
Monk é uma ferramenta que orquestra todo o fluxo de tradução de perguntas em linguagem natural
para planos de execução SQL sobre múltiplos bancos de dados. O projeto coleta metadados das bases,
utliza um modelo de linguagem para gerar planos de consulta federados e disponibiliza utilidades para
executar esses planos e validar os resultados. O objetivo é apoiar cenários de dados distribuídos nos
quais diferentes fontes (MySQL e PostgreSQL) precisam ser combinadas sem que o usuário final escreva SQL manualmente.

O repositório inclui:
- Extração automatizada de metadados dos bancos informados via SQLAlchemy.【F:src/utils/metadata_extraction.py†L7-L38】
- Serialização dos esquemas (tabelas e colunas) em JSON, com tratamento de tipos, nullability e outros atributos.【F:src/utils/column_serialization.py†L1-L26】
- Geração de planos de execução com múltiplos passos por meio de um LLM da OpenAI, incluindo dependências entre consultas e instruções de agregação final.【F:src/query_translation.py†L12-L104】
- Modelo de dados tipado para representar cada passo do plano e auxiliar na validação dos retornos do LLM.【F:src/models/execution_plan.py†L4-L15】
- Utilidades para executar cada etapa do plano e consolidar os resultados em um `DataFrame` final.【F:src/plan_execution.py†L24-L118】

## Instalação e Pré-requisitos
1. **Python:** utilize Python 3.11+.
2. **Dependências:** instale as bibliotecas necessárias.
   ```bash
   pip install -r requirements.txt
   ```
3. **Variáveis de ambiente:** configure as credenciais da OpenAI com `OPENAI_API_KEY` para que a etapa de tradução utilize a API.【F:src/query_translation.py†L1-L127】
4. **Bancos de teste:** o diretório `test/compose.yaml` contém um `docker-compose` com os containers de bancos de dados usados nos cenários de validação.

## Como usar
O módulo `main.py` expõe comandos `typer` para os fluxos principais.【F:main.py†L1-L60】

1. **Extrair metadados**
   ```bash
   python main.py extract_metadata "mysql://user:pass@host:3306/db" "postgresql://user:pass@host:5432/db" --output-path ./metadata.json
   ```
   O comando conecta em cada URL, enriquece o driver (quando necessário) e gera um arquivo JSON com os esquemas das tabelas.【F:src/utils/metadata_extraction.py†L7-L54】

2. **Traduzir uma pergunta**
   ```bash
   python main.py translate --metadata-path ./metadata.json "Quais clientes fizeram mais pedidos no último mês?"
   ```
   O LLM retorna um plano de execução com as consultas individuais, dependências e orientações de agregação. O plano é ordenado e salvo em `./plans` por padrão.【F:main.py†L30-L58】【F:src/query_translation.py†L12-L104】

3. **Executar um plano**
   Há uma função utilitária (`execute_plan`) que recebe a estrutura retornada pelo LLM e executa cada passo, resolvendo joins e placeholders entre etapas.【F:src/plan_execution.py†L24-L118】
   ```python
   from src.plan_execution import execute_plan
   from src.query_translation import TranslationReturn

   plan = TranslationReturn.model_validate_json(Path("./plans/exemplo.json").read_text(encoding="utf-8"))
   final_df = execute_plan(plan)
   ```

## Estrutura do JSON de metadados
Cada item do array produzido pela extração descreve uma base de dados específica com os campos abaixo：【F:src/utils/metadata_extraction.py†L18-L38】【F:src/utils/column_serialization.py†L14-L26】

| Campo | Descrição |
| ----- | --------- |
| `dialect` | Nome do dialeto SQL detectado (`mysql`, `postgresql`, etc.). |
| `drivername` | Driver Python utilizado para a conexão (ex.: `pymysql`, `psycopg`). |
| `username`, `password`, `host`, `port`, `database` | Credenciais e endereço da base de dados. |
| `tables` | Dicionário onde cada chave é o nome de uma tabela e o valor é a lista de colunas serializadas. |
| `name` | Nome da coluna. |
| `type` | Tipo de dados conforme reportado pelo dialeto/driver. |
| `nullable` | Indica se a coluna aceita valores nulos. |
| `default` | Valor padrão informado pelo catálogo da base. |
| `comment` | Comentário associado à coluna, quando existente. |
| `autoincrement` | Sinaliza se a coluna possui incremento automático. |

Esse arquivo é o insumo para o prompt enviado ao LLM na etapa de tradução.【F:src/query_translation.py†L12-L48】

## Estrutura do plano de execução gerado pelo LLM
O retorno padrão contém três blocos principais.【F:src/query_translation.py†L24-L47】【F:src/models/execution_plan.py†L4-L15】

### `execution_plan`
Lista ordenada de passos, cada um com:
- `id`: identificador numérico do passo (usado para referenciar dependências).
- `description`: resumo em linguagem natural da consulta executada.
- `database`: URL de conexão utilizada na etapa.
- `query`: SQL completo que deve ser executado no banco daquele passo.
- `depends_on`: lista de `id`s de passos anteriores que precisam terminar antes deste.
- `join_info` (opcional): orienta como os dados devem ser combinados na aplicação. Contém `type` (INNER/LEFT/RIGHT/FULL) e `on`, um dicionário com `current_step_column` e `dependency_step_column` para guiar o merge de resultados.

### `final_aggregation`
Dicionário com:
- `type`: operação a ser aplicada após todos os passos (`COUNT`, `SUM`, `AVG`, `MAX`, `MIN` ou `NONE`).
- `column`: nome da coluna alvo da agregação. Quando `type = "NONE"`, nenhuma agregação adicional é aplicada.

### `final_output_columns`
Lista com os nomes das colunas que devem aparecer no resultado consolidado. O executor filtra o `DataFrame` final para conter apenas essas colunas, garantindo consistência entre as etapas.【F:src/plan_execution.py†L70-L118】

O módulo de execução substitui automaticamente placeholders como `$step1.customer_id` pelos valores retornados em etapas anteriores e realiza merges conforme `join_info`. Em seguida aplica agregações globais e filtros de coluna antes de devolver o `DataFrame` final.【F:src/plan_execution.py†L52-L118】

## Bancos de dados de teste incluídos
O repositório acompanha três domínios de exemplo usados para validar as traduções: `ecommerce`, `bakery_1` e `sales`. Os metadados encontram-se em `*.json` na raiz e os esquemas completos em `test/schemas`.

### Domínio Ecommerce
- **MySQL `products_db` – tabela `Products`:** catálogo de produtos com identificadores, atributos descritivos (cor, tamanho, descrição) e preço padrão.【F:ecommerce_metadata.json†L2-L67】
- **MySQL `orders_db`:** tabelas `Invoices`, `Order_Items` e `Orders` armazenam notas fiscais, itens de pedido e cabeçalhos de pedidos, incluindo status, data e chaves de relacionamento com clientes e produtos.【F:ecommerce_metadata.json†L71-L174】
- **PostgreSQL `users_db`:** tabela `customers` registra dados cadastrais (nome, email, endereço, país) e `customer_payment_methods` contém os métodos de pagamento associados.【F:ecommerce_metadata.json†L177-L308】
- **PostgreSQL `shipments_db`:** tabelas `shipments` e `shipment_items` relacionam pedidos, notas fiscais e itens despachados, com informações de rastreamento e data de envio.【F:ecommerce_metadata.json†L311-L381】

### Domínio Bakery 1
- **MySQL `receipts_db` – tabela `receipts`:** comprovantes emitidos pela padaria com número do recibo, data e referência ao cliente.【F:bakery_1_metadata.json†L1-L36】
- **MySQL `items_db` – tabela `items`:** itens individuais de cada recibo, contendo ordinal e descrição do produto comprado.【F:bakery_1_metadata.json†L39-L73】
- **PostgreSQL `customers_db` – tabela `customers`:** cadastro de clientes com identificador sequencial, nome e sobrenome.【F:bakery_1_metadata.json†L76-L110】
- **PostgreSQL `goods_db` – tabela `goods`:** catálogo de produtos vendidos pela padaria (id textual, sabor, tipo de alimento e preço).【F:bakery_1_metadata.json†L113-L155】

### Domínio Sales (EUA e Europa)
- **PostgreSQL `sales_eu`:** tabela `customers` guarda dados de contato, país e opt-in de marketing; tabela `orders` registra pedidos com valor em euro e cupons aplicados.【F:test/schemas/sales/postgres/eu-sales/eu_sales_db.sql†L1-L48】
- **PostgreSQL `sales_us`:** tabela `customers` inclui estado e consentimento para SMS; tabela `orders` acompanha pedidos com valores em dólar e cupons.【F:test/schemas/sales/postgres/us-sales/us_sales_db.sql†L1-L54】

Esses esquemas cobrem cenários típicos de consultas federadas, permitindo avaliar como o LLM lida com junções entre bancos heterogêneos e agregações distribuídas.

## Resultados de referência
Os diretórios `plans/<domínio>` e `test_data/results/<domínio>` armazenam planos gerados e CSVs de resultados usados para comparação automática. Eles servem como benchmark para validar novas versões do pipeline e investigar diferenças de tradução ou execução.【F:main.py†L73-L111】

## Licença
Este projeto é distribuído internamente para experimentação com NL2SQL e não possui uma licença pública definida. Ajuste conforme a necessidade do seu ambiente.
