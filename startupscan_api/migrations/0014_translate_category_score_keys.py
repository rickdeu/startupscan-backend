from django.db import migrations

OLD_TO_NEW_CATEGORY_KEY = {
    "clareza_da_ideia": "idea_clarity",
    "proposta_de_valor": "value_proposition",
    "inovacao": "innovation",
    "viabilidade_tecnica_financeira": "technical_financial_feasibility",
    "escalabilidade": "scalability",
    "mercado_alvo": "target_market",
    "equipe_fundadora": "founding_team",
    "sustentabilidade": "sustainability",
}
NEW_TO_OLD_CATEGORY_KEY = {v: k for k, v in OLD_TO_NEW_CATEGORY_KEY.items()}

CATEGORY_LABELS_EN = {
    "idea_clarity": "Idea Clarity",
    "value_proposition": "Value Proposition",
    "innovation": "Innovation",
    "technical_financial_feasibility": "Technical & Financial Feasibility",
    "scalability": "Scalability",
    "target_market": "Target Market",
    "founding_team": "Founding Team",
    "sustainability": "Sustainability",
}


def _rename_keys(scores, mapping):
    if not isinstance(scores, dict):
        return scores
    return {mapping.get(key, key): value for key, value in scores.items()}


def forwards_translate_category_keys(apps, schema_editor):
    PitchAnalysis = apps.get_model("startupscan_api", "PitchAnalysis")
    for analysis in PitchAnalysis.objects.all().iterator():
        report = analysis.report
        if not isinstance(report, dict):
            continue
        scores = report.get("category_scores")
        if not isinstance(scores, dict):
            continue
        if not any(key in OLD_TO_NEW_CATEGORY_KEY for key in scores):
            continue
        report["category_scores"] = _rename_keys(scores, OLD_TO_NEW_CATEGORY_KEY)
        report.setdefault("category_labels", {})
        report["category_labels"] = {
            key: CATEGORY_LABELS_EN.get(key, key) for key in report["category_scores"]
        }
        report.setdefault("language", "pt")
        PitchAnalysis.objects.filter(pk=analysis.pk).update(report=report)


def backwards_translate_category_keys(apps, schema_editor):
    PitchAnalysis = apps.get_model("startupscan_api", "PitchAnalysis")
    for analysis in PitchAnalysis.objects.all().iterator():
        report = analysis.report
        if not isinstance(report, dict):
            continue
        scores = report.get("category_scores")
        if not isinstance(scores, dict):
            continue
        if not any(key in NEW_TO_OLD_CATEGORY_KEY for key in scores):
            continue
        report["category_scores"] = _rename_keys(scores, NEW_TO_OLD_CATEGORY_KEY)
        report.pop("category_labels", None)
        PitchAnalysis.objects.filter(pk=analysis.pk).update(report=report)


class Migration(migrations.Migration):

    dependencies = [
        ("startupscan_api", "0013_translate_pitch_idea_investor_labels"),
    ]

    operations = [
        migrations.RunPython(forwards_translate_category_keys, backwards_translate_category_keys),
    ]
