from startupscan_api.services.ai_engines.prompt_defaults import DEFAULT_PROMPTS


def get_prompt_content(engine: str, purpose: str) -> str:
    """
    Active DB-stored prompt text for (engine, purpose), falling back to the
    built-in default if no active row exists yet (e.g. right after a fresh
    `migrate` on a database the seed data migration hasn't reached, or a row
    an admin deactivated).
    """
    from startupscan_api.models import PromptTemplate

    row = PromptTemplate.objects.filter(engine=engine, purpose=purpose, is_active=True).first()
    if row is not None:
        return row.content
    return DEFAULT_PROMPTS.get(purpose, "")
