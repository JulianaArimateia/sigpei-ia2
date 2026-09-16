# SIGPEI-IA

**Sistema Inteligente de Gestão do Plano Educacional Individualizado**

Ferramenta desenvolvida para apoiar professores e equipes pedagógicas na elaboração de PEIs (Planos Educacionais Individualizados) para alunos com necessidades educacionais especiais. A IA analisa descrições em texto ou voz e extrai automaticamente os campos do documento, seguindo a LDBEN e a Resolução CNE/CEB nº 4/2009.

---

## Funcionalidades

- Entrada por **voz** (gravação direta), **texto livre** ou **upload de documentos** (PDF, DOCX, TXT, imagens)
- **IA extrai automaticamente** os campos do PEI: identificação do aluno, diagnóstico, habilidades, objetivos, estratégias e adaptações
- **Revisão e edição** de todos os campos antes de salvar
- **Exportação em PDF** formatado e pronto para impressão
- **Histórico de registros** com busca por nome de aluno
- **Painel de acompanhamento** com estatísticas gerais
- **App mobile** (Flet) com o mesmo fluxo da versão web, otimizado para tela de celular

---

## Arquitetura

```
SIGPEI-IA/
├── app2.0.py          # Interface web (Streamlit)
├── mobile_app.py      # App mobile (Flet) — mesmo fluxo da web, para celular
├── ai_processor.py    # Integração com IA (Groq, Mistral e OpenRouter — 100% em nuvem, gratuitos)
├── database.py        # Banco de dados SQLite
├── pei_generator.py   # Geração de PDF
├── .env.example       # Modelo de variáveis de ambiente
└── pyproject.toml     # Dependências do projeto
```

> `app2.0.py` (web) e `mobile_app.py` (mobile) são duas interfaces independentes
> que chamam os mesmos módulos Python (`ai_processor`, `database`,
> `pei_generator`) diretamente — não há uma API REST intermediária.

### Como a IA funciona

A IA roda inteiramente em **nuvem gratuita** — nenhum modelo é instalado ou
executado localmente. `ai_processor.py` mantém uma cadeia de provedores com
fallback automático: se o primeiro provedor configurado falhar ou atingir o
limite gratuito, o sistema tenta o próximo, sem intervenção do usuário. A
ordem prioriza a postura de privacidade em relação aos dados do aluno
(informação sensível de saúde/deficiência) acima de velocidade ou tamanho do
free tier — ver comparação completa em [`relatorio.txt`](relatorio.txt).

| Ordem | Provedor | Uso | Por que nessa posição |
|---|---|---|---|
| 1ª | **Groq** | Web + mobile | Nunca usa dados da API para treinar, em nenhum plano; Zero Data Retention opcional; muito rápido, sem cartão de crédito |
| 2ª | **Mistral** (La Plateforme) | Web + mobile | Sediada na UE (GDPR nativo); plano pago não treina, mas o **free tier treina por padrão** — é preciso desativar manualmente em Privacy Settings |
| 3ª | **OpenRouter** (modelos `:free`) | Web + mobile | Rede de segurança final; agrega vários modelos gratuitos de terceiros com política de dados variável por modelo |

Basta configurar **uma** das chaves para o sistema funcionar; configurar mais
de uma aumenta a resiliência (menos chance de ficar sem IA por limite de uso).

---

## Pré-requisitos

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (gerenciador de pacotes)
- Uma chave gratuita de IA em nuvem (Groq, Mistral e/ou OpenRouter — não é preciso instalar nada localmente)

Web e mobile usam as mesmas dependências Python (`uv sync` resolve as duas).

---

## Instalação e Execução

### 1. Clone o repositório

```bash
git clone https://github.com/JulianaArimateia/sigpei-ia2.git
cd sigpei-ia2
```

### 2. Configure as variáveis de ambiente

```bash
cp .env.example .env
```

Edite o `.env` com pelo menos uma chave gratuita:

```env
GROQ_API_KEY=sua-chave-aqui         # console.groq.com/keys
MISTRAL_API_KEY=sua-chave-aqui      # console.mistral.ai/api-keys
OPENROUTER_API_KEY=sua-chave-aqui   # openrouter.ai → Keys
```

---

### Interface Web (Streamlit)

**Passo 1 — Instale as dependências Python:**

```bash
uv sync
```

**Passo 2 — Inicie a aplicação:**

```bash
uv run streamlit run app2.0.py
```

Acesse em: `http://localhost:8501`

---

### App Mobile (Flet)

Interface separada, com o mesmo fluxo em 3 passos (entrada → revisão → salvar),
otimizada para tela de celular. Chama os mesmos módulos Python da versão web
diretamente — não depende de nenhuma API REST.

```bash
uv run python mobile_app.py
```

Abre automaticamente em `http://localhost:8502` (funciona no navegador do
próprio celular, desde que ele esteja na mesma rede do computador que está
rodando o comando, usando o IP local em vez de `localhost`).

---

## Como usar o sistema

### Criando um novo PEI

1. Acesse a aba **"Novo PEI"** no menu lateral
2. Escolha a forma de entrada:
   - **Gravar voz**: clique no microfone e fale livremente sobre o aluno
   - **Digitar texto**: descreva o aluno, diagnóstico, habilidades e objetivos
   - **Carregar documentos**: suba laudos, relatórios ou avaliações em PDF, DOCX ou TXT
3. Clique em **"Analisar com IA"** — os campos do PEI serão preenchidos automaticamente
4. Revise e edite os campos gerados
5. Clique em **"Confirmar e Salvar"**
6. Baixe o **PDF** do PEI finalizado

### Consultando registros

- Acesse **"Registros"** para ver todos os PEIs salvos
- Use a busca por nome do aluno
- Gere o PDF de qualquer registro anterior

### Painel

- Acesse **"Painel"** para visualizar estatísticas: total de PEIs, escolas atendidas e registros do mês

---

## Banco de Dados

O sistema usa **SQLite** (`sigpei.db`), criado automaticamente na primeira execução. Três tabelas:

- `students` — dados de identificação do aluno
- `pei_records` — todos os campos do PEI vinculados ao aluno
- `documents` — textos extraídos de documentos anexados

O arquivo `sigpei.db` é local e não é versionado pelo Git.

---

## Tecnologias utilizadas

| Camada | Tecnologia |
|---|---|
| Interface web | [Streamlit](https://streamlit.io) |
| App mobile | [Flet](https://flet.dev) |
| IA (1ª opção) | [Groq](https://groq.com) (Llama/Gemma, free tier) |
| IA (2ª opção) | [Mistral](https://mistral.ai) — La Plateforme (free tier) |
| IA (3ª opção) | [OpenRouter](https://openrouter.ai) (modelos `:free` de terceiros) |
| Banco de dados | SQLite |
| Geração de PDF | [ReportLab](https://www.reportlab.com) |
| Extração de texto | pdfplumber, python-docx, pytesseract |
| Transcrição de voz | SpeechRecognition (Google) |
| Gerenciador Python | [uv](https://docs.astral.sh/uv/) |

---

## Base Legal

O PEI gerado pelo SIGPEI-IA segue as diretrizes da:

- **LDBEN** — Lei de Diretrizes e Bases da Educação Nacional (Lei nº 9.394/1996)
- **Resolução CNE/CEB nº 4/2009** — Diretrizes Operacionais para o Atendimento Educacional Especializado

---

## Contribuição

1. Fork o repositório
2. Crie uma branch: `git checkout -b minha-funcionalidade`
3. Commit suas alterações: `git commit -m 'feat: descrição da mudança'`
4. Push para a branch: `git push origin minha-funcionalidade`
5. Abra um Pull Request
