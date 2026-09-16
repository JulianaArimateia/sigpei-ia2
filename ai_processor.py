import os
import json
import time
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ── Cadeia de provedores de IA em nuvem (100% gratuitos, nenhum roda localmente) ──
# Ordem de prioridade definida por postura de privacidade dos dados do aluno
# (informação sensível: diagnóstico, deficiência, saúde) > velocidade > limite
# de free tier. Detalhes e comparação completa em relatorio.txt.
#
# 1) Groq  — nunca usa Inputs/Outputs para treinar, em nenhum plano (inclusive
#    o gratuito), e oferece Zero Data Retention opcional. É a opção mais segura.
# 2) Mistral — o plano pago não treina com os dados, mas o plano gratuito
#    ("Experiment") treina por padrão, com opt-out manual disponível em
#    console.mistral.ai → Privacy. Desative "Data trained" no console antes de
#    usar com dados reais de alunos.
# 3) OpenRouter — agrega modelos gratuitos de terceiros; a política de dados de
#    cada modelo depende do provedor por trás dele. É a rede de segurança
#    final. Recomenda-se desativar "Enable free endpoints that may train on
#    inputs" nas configurações de privacidade da conta sempre que possível.
#
# Cada provedor só é usado se sua respectiva *_API_KEY estiver definida no .env.

# NOTA: catálogos de modelo gratuito mudam com frequência nos 3 provedores —
# os slugs abaixo foram verificados com chamadas reais em 16/09/2026. Se a
# cadeia inteira voltar a falhar, o mais provável é que um provedor tenha
# descontinuado/renomeado um modelo; confira a lista atual em
# console.groq.com/docs/models, docs.mistral.ai/getting-started/models ou
# openrouter.ai/models?max_price=0 antes de trocar os slugs.
_PROVIDERS = [
    {
        "name": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "api_key": os.getenv("GROQ_API_KEY"),
        "models": ["qwen/qwen3.8-27b", "openai/gpt-oss-120b", "openai/gpt-oss-20b"],
    },
    {
        "name": "Mistral",
        "base_url": "https://api.mistral.ai/v1",
        "api_key": os.getenv("MISTRAL_API_KEY"),
        "models": ["mistral-small-latest", "ministral-8b-latest"],
    },
    {
        "name": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key": os.getenv("OPENROUTER_API_KEY"),
        "models": [
            "google/gemma-4-26b-a4b-it:free",
            "nvidia/nemotron-3.5-lightning:free",
        ],
    },
]

_SYSTEM = (
    "Você é especialista em educação inclusiva no Brasil e no Plano Educacional Individualizado (PEI). "
    "Extraia e organize informações para o PEI seguindo LDBEN e Resolução CNE/CEB nº 4/2009. "
    "Responda SEMPRE em português do Brasil. "
    "Quando solicitado JSON: retorne APENAS o objeto JSON, começando com { e terminando com }. "
    "Sem texto antes, sem texto depois, sem markdown."
)

_SCHEMA = {
    "nome": "string ou null",
    "data_nascimento": "string DD/MM/AAAA ou null",
    "escola": "string ou null",
    "serie": "string ou null",
    "turma": "string ou null",
    "turno": "Matutino ou Vespertino ou Noturno ou Integral ou null",
    "diagnostico": "string ou null",
    "cid": "string ex F84.0 ou null",
    "professor": "string ou null",
    "equipe": ["string"],
    "habilidades_atuais": {
        "cognitiva": "string ou null",
        "comunicacao": "string ou null",
        "socializacao": "string ou null",
        "motora": "string ou null",
        "autocuidado": "string ou null",
        "academica": "string ou null",
    },
    "objetivos_longo_prazo": ["string"],
    "objetivos_curto_prazo": [{"objetivo": "string", "criterio": "string", "prazo": "string"}],
    "estrategias": ["string"],
    "adaptacoes_curriculares": ["string"],
    "servicos_apoio": ["string"],
    "avaliacao": "string ou null",
    "data_elaboracao": "string DD/MM/AAAA ou null",
    "data_revisao": "string DD/MM/AAAA ou null",
}

_DEFAULTS = {
    "nome": None, "data_nascimento": None, "escola": None, "serie": None,
    "turma": None, "turno": None, "diagnostico": None, "cid": None,
    "professor": None, "equipe": [],
    "habilidades_atuais": {k: None for k in ["cognitiva","comunicacao","socializacao","motora","autocuidado","academica"]},
    "objetivos_longo_prazo": [], "objetivos_curto_prazo": [],
    "estrategias": [], "adaptacoes_curriculares": [],
    "servicos_apoio": [], "avaliacao": None,
    "data_elaboracao": None, "data_revisao": None,
}


def _extract_json(raw: str) -> str:
    raw = raw.strip().replace("```json", "").replace("```", "").strip()
    start = raw.find("{")
    if start == -1:
        raise ValueError("Nenhum JSON na resposta.")
    depth, in_str, esc = 0, False, False
    for i, ch in enumerate(raw[start:], start=start):
        if esc:             esc = False; continue
        if ch == "\\" and in_str: esc = True; continue
        if ch == '"':       in_str = not in_str; continue
        if in_str:          continue
        if ch == "{":       depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return raw[start:i + 1]
    return raw[start:]


def _call(messages: list, max_tokens: int = 4096) -> str:
    configured = [p for p in _PROVIDERS if p["api_key"]]
    if not configured:
        raise RuntimeError(
            "Nenhuma chave de IA configurada.\n"
            "Defina ao menos uma das variáveis MISTRAL_API_KEY, GROQ_API_KEY ou "
            "OPENROUTER_API_KEY no arquivo .env (todas têm plano gratuito)."
        )

    last_err = None
    for provider in configured:
        client = OpenAI(api_key=provider["api_key"], base_url=provider["base_url"])
        for model in provider["models"]:
            for attempt in range(3):
                try:
                    r = client.chat.completions.create(
                        model=model, messages=messages,
                        temperature=0.1, max_tokens=max_tokens,
                    )
                    return r.choices[0].message.content
                except Exception as e:
                    last_err = e
                    s = str(e)
                    if "401" in s or "User not found" in s or "Invalid API key" in s or "Unauthorized" in s:
                        break  # chave inválida para este provedor: tenta o próximo provedor
                    if "429" in s or "rate" in s.lower():
                        time.sleep(6 * (attempt + 1))
                        continue
                    break
    raise RuntimeError(
        f"Todos os provedores de IA configurados falharam. Tente novamente em alguns instantes.\n"
        f"Último erro ({last_err.__class__.__name__ if last_err else '—'}): {last_err}"
    )


def extract_pei_info(text: str, doc_context: str = "") -> dict:
    parts = [f"Texto:\n{text}"]
    if doc_context:
        parts.append(f"Documentos:\n{doc_context}")

    prompt = (
        "Analise e extraia informações para um PEI escolar.\n\n"
        + "\n\n".join(parts)
        + f"\n\nRetorne APENAS este JSON preenchido:\n{json.dumps(_SCHEMA, ensure_ascii=False, indent=2)}"
    )

    raw = _call(
        [{"role": "system", "content": _SYSTEM}, {"role": "user", "content": prompt}],
    )

    try:
        data = json.loads(_extract_json(raw))
    except Exception:
        raw2 = _call(
            [{"role": "user", "content": f"Corrija este JSON com erro e retorne apenas o JSON válido:\n{raw}"}],
        )
        data = json.loads(_extract_json(raw2))

    result = dict(_DEFAULTS)
    result.update({k: v for k, v in data.items() if k in _DEFAULTS})
    if isinstance(result.get("habilidades_atuais"), dict):
        hab = dict(_DEFAULTS["habilidades_atuais"])
        hab.update(result["habilidades_atuais"])
        result["habilidades_atuais"] = hab
    return result


def improve_transcription(raw_text: str) -> str:
    return _call([
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": (
            "Corrija erros de transcrição de voz. Mantenha todas as informações. "
            f"Retorne apenas o texto corrigido:\n\n{raw_text}"
        )},
    ], max_tokens=1024).strip()
    