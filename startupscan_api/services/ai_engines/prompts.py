import json
from string import Template

from startupscan_api.engines import AnalysisEngine
from startupscan_api.modeling import _GPT_OUTPUT_LANGUAGE_INSTRUCTIONS, _build_uniqueness_key
from startupscan_api.services.ai_engines.prompt_defaults import PURPOSE_ANALYSIS_SYSTEM, PURPOSE_ANALYSIS_USER
from startupscan_api.services.ai_engines.prompt_store import get_prompt_content


def build_pitch_analysis_prompts(text, financial_data, metadata, language: str = "en", engine: str = AnalysisEngine.GPT):
    """
    Builds the system/user prompt pair for the analysis engines (GPT,
    DeepSeek, Ollama), reading the editable template for `engine` from the
    database (see PromptTemplate / superadmin "Prompts" panel) and falling
    back to the built-in default if none is configured.

    Returns (system_prompt, user_prompt, startup_name, uniqueness_key).
    """
    startup_name = str((metadata or {}).get("startup_name", "") or "").strip()
    uniqueness_key = _build_uniqueness_key(text, financial_data, metadata)
    output_language = _GPT_OUTPUT_LANGUAGE_INSTRUCTIONS.get(language, _GPT_OUTPUT_LANGUAGE_INSTRUCTIONS["en"])

    system_prompt = Template(get_prompt_content(engine, PURPOSE_ANALYSIS_SYSTEM)).safe_substitute(
        output_language=output_language,
    )
    user_prompt = Template(get_prompt_content(engine, PURPOSE_ANALYSIS_USER)).safe_substitute(
        startup_name=startup_name,
        uniqueness_key=uniqueness_key,
        text=text,
        financial_data_json=json.dumps(financial_data or {}, ensure_ascii=False),
        metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
    )

    return system_prompt, user_prompt, startup_name, uniqueness_key
