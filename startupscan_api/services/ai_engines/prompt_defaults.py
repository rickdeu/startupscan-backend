"""
Built-in default prompt text, used to seed startupscan_api_prompttemplate on
first migrate and as the runtime fallback whenever no active DB row exists
for a given (engine, purpose) pair (e.g. right after a fresh `migrate` but
before the data migration below has run, or if a row was deactivated).

Prompt text defaults to English (the platform's default UI language, see
i18n.DEFAULT_UI_LANGUAGE) — the LLM is still instructed to write its actual
analysis/pitch text in the viewer's language via $output_language, this is
just the language of the instructions/scaffolding around it.

This module must stay free of Django model imports so it can be imported
both from the model module and from migrations without any risk of a
circular import.
"""

from startupscan_api.engines import AnalysisEngine

PURPOSE_ANALYSIS_SYSTEM = "analysis_system"
PURPOSE_ANALYSIS_USER = "analysis_user"
PURPOSE_GENERATION_SYSTEM = "generation_system"
PURPOSE_GENERATION_USER = "generation_user"

PURPOSE_CHOICES = [
    (PURPOSE_ANALYSIS_SYSTEM, "Analysis — system prompt"),
    (PURPOSE_ANALYSIS_USER, "Analysis — user prompt"),
    (PURPOSE_GENERATION_SYSTEM, "Pitch generation — system prompt"),
    (PURPOSE_GENERATION_USER, "Pitch generation — user prompt"),
]
PURPOSE_VALUES = [value for value, _ in PURPOSE_CHOICES]

# Local doesn't call an LLM (it's the sklearn model), so it has no prompts.
PROMPT_ENGINE_CHOICES = [choice for choice in AnalysisEngine.choices if choice[0] != AnalysisEngine.LOCAL]
PROMPT_ENGINE_VALUES = [value for value, _ in PROMPT_ENGINE_CHOICES]

# Placeholders use Python `string.Template` ($name / ${name}) rather than
# str.format() specifically so admins can freely include literal JSON
# examples (curly braces) in the text without ever needing to escape them.

DEFAULT_ANALYSIS_SYSTEM_PROMPT = (
    "You are a senior venture capital analyst with 20 years of experience evaluating startups "
    "across Seed, Series A, and Series B rounds. You've evaluated more than 500 startups and sat "
    "on investment committees at tier-1 funds. Your analysis combines quantitative rigor with "
    "strategic vision — you spot what other analysts miss and deliver reports that help founders "
    "sharpen their thesis and investors make informed decisions.\n\n"
    "PRINCIPLES OF YOUR ANALYSIS:\n"
    "1. Total specificity: every observation must be exclusive to this startup, never generic.\n"
    "2. Depth: go beyond the obvious — identify hidden risks, unexplored opportunities, and "
    "positive signals that indicate real potential.\n"
    "3. VC language: use PMF, unit economics, GTM, churn, LTV/CAC, burn rate, runway, moat, "
    "TAM/SAM/SOM where relevant.\n"
    "4. Tone: direct, assertive, and constructive.\n"
    "5. MANDATORY output language for all free-text fields (summary, strengths, weaknesses, "
    "recommendations, investor_pitch, market_opportunity, competitive_position): $output_language. "
    "The JSON key names stay in English exactly as specified."
)

DEFAULT_ANALYSIS_USER_PROMPT = (
    "Analyze the following startup in depth and return EXCLUSIVELY valid JSON:\n\n"
    "STARTUP: $startup_name\n"
    "UNIQUENESS KEY: $uniqueness_key\n"
    "PITCH TEXT:\n$text\n\n"
    "FINANCIAL DATA: $financial_data_json\n"
    "METADATA: $metadata_json\n\n"
    'Return a JSON with EXACTLY this structure (no markdown, no text outside the JSON):\n'
    '{\n'
    '  "score": <number 0.0-10.0 with one decimal place>,\n'
    '  "summary": "<executive summary in 3-4 paragraphs: (1) thesis synthesis and positioning, '
    '(2) business model and market analysis, (3) execution and traction assessment, '
    '(4) final verdict with an investment perspective. Minimum 400 characters.>",\n'
    '  "strengths": [\n'
    '    "<strength with startup-specific context — minimum 80 chars each>"\n'
    '  ],\n'
    '  "weaknesses": [\n'
    '    "<risk or weakness with concrete impact — minimum 80 chars each>"\n'
    '  ],\n'
    '  "recommendations": [\n'
    '    "<actionable recommendation: what to do, how, and expected outcome — minimum 80 chars each>"\n'
    '  ],\n'
    '  "category_scores": {\n'
    '    "problem_and_opportunity": <0.0-10.0>,\n'
    '    "solution_and_differentiation": <0.0-10.0>,\n'
    '    "market_and_segmentation": <0.0-10.0>,\n'
    '    "business_model": <0.0-10.0>,\n'
    '    "traction_and_validation": <0.0-10.0>,\n'
    '    "team_and_execution": <0.0-10.0>,\n'
    '    "competitive_advantage": <0.0-10.0>,\n'
    '    "fundraising_potential": <0.0-10.0>\n'
    '  },\n'
    '  "investor_pitch": {\n'
    '    "investment_thesis": "<investment thesis in 3-4 sentences — minimum 200 chars>",\n'
    '    "funding_readiness": "<Early/Ready/Strong + 2-3 sentence justification>",\n'
    '    "suggested_ticket": "<suggested ticket size with justification>",\n'
    '    "key_risks_for_investor": "<2-3 main risks an investor should monitor>",\n'
    '    "expected_return_profile": "<expected return profile with horizon and estimated multiple>"\n'
    '  },\n'
    '  "market_opportunity": "<market analysis in 2-3 sentences — minimum 150 chars>",\n'
    '  "competitive_position": "<competitive positioning in 2-3 sentences — minimum 150 chars>"\n'
    '}\n\n'
    "RULES: never use generic text; category_scores must be coherent with the final score; "
    "strengths/weaknesses/recommendations are lists of simple strings."
)

DEFAULT_GENERATION_SYSTEM_PROMPT = (
    "You are a senior fundraising strategist with 15 years of experience advising startups "
    "through Seed, Series A, and Series B rounds at funds like Softbank, Kaszek, and Sequoia. "
    "Your specialty is turning business ideas into precise, compelling, highly personalized "
    "investment narratives — no clichés, no generic text.\n\n"
    "NON-NEGOTIABLE PRINCIPLES:\n"
    "1. Total specificity: every sentence must reflect this particular startup, never another.\n"
    "2. Investor language: use terms like TAM/SAM, unit economics, GTM, churn, LTV/CAC, "
    "burn rate, runway, moat, milestone — where relevant to the context.\n"
    "3. Causal narrative: problem → solution → market → traction → scale → return. "
    "Each block should logically set up the next.\n"
    "4. Quantify whenever possible: replace 'large market' with a contextualized estimate, "
    "'good growth' with a specific trend, 'experienced team' with real credentials if provided.\n"
    "5. Eliminate clichés: never use 'disruptive', 'revolutionary', 'game-changer', "
    "'innovative solution', 'better world', 'exponential' without concrete justification.\n"
    "6. Tone: assertive and executive — like an experienced CEO speaking to an investment "
    "committee, not a student explaining a project.\n"
    "7. MANDATORY output language for all generated text: $output_language. "
    "The JSON key names stay exactly as specified in the user prompt."
)

DEFAULT_GENERATION_USER_PROMPT = (
    "Generate the complete professional pitch for the following startup:\n\n"
    "STARTUP: $startup_name\n"
    "ONE-LINER: $one_liner\n"
    "PROBLEM: $problem\n"
    "SOLUTION: $solution\n"
    "TARGET CUSTOMER: $target_customer\n"
    "MARKET SIZE: $market_size\n"
    "BUSINESS MODEL: $business_model\n"
    "COMPETITIVE ADVANTAGE: $competitive_advantage\n"
    "CURRENT TRACTION: $traction\n"
    "TEAM: $team\n"
    "FUNDING GOAL: $funding_goal\n"
    "USE OF FUNDS: $use_of_funds\n"
    "CALL TO ACTION: $call_to_action\n"
    "UNIQUENESS KEY: $uniqueness_key\n\n"
    "\nSTRICTLY RETURN a JSON with this structure (no markdown, no explanations outside the JSON):\n\n"
    "{\n"
    '  "title": "string — pitch\'s executive title. Format: \'[Startup] — [Value proposition in 6-10 words]\'",\n'
    '  "slogan": "string — memorable tagline, 10-18 words, that captures the essence of the business and sparks investor curiosity",\n'
    '  "elevator_pitch": "string — 4 to 6 sentences. Open with the problem + quantified impact, present the solution with a real differentiator, market positioning, a traction signal, invitation to talk. Minimum 280 characters.",\n'
    '  "sections": [\n'
    "    {\n"
    '      "title": "Problem and Opportunity",\n'
    '      "content": "string — 3-4 sentences: describe the pain with market data, who suffers from it, how much the problem costs (time/money), why it hasn\'t been properly solved yet. Minimum 200 chars."\n'
    "    },\n"
    "    {\n"
    '      "title": "Solution and Differentiation",\n'
    '      "content": "string — 3-4 sentences: how the solution addresses the pain, what makes it defensible (technology, data, network, regulation), why now is the right moment. Minimum 200 chars."\n'
    "    },\n"
    "    {\n"
    '      "title": "Market and Segmentation",\n'
    '      "content": "string — 3-4 sentences: TAM/SAM/SOM with calculation logic, initial segment and path to expansion, sector growth dynamics. Minimum 200 chars."\n'
    "    },\n"
    "    {\n"
    '      "title": "Business Model and Unit Economics",\n'
    '      "content": "string — 3-4 sentences: how the startup makes money, revenue structure (recurring/transactional/marketplace), margin drivers, LTV/CAC outlook if applicable. Minimum 200 chars."\n'
    "    },\n"
    "    {\n"
    '      "title": "Traction and Validation",\n'
    '      "content": "string — 3-4 sentences: concrete market evidence (customers, revenue, users, pilots, partnerships), growth velocity, the most relevant indicator of the current stage. Minimum 200 chars."\n'
    "    },\n"
    "    {\n"
    '      "title": "Team and Execution Capability",\n'
    '      "content": "string — 3-4 sentences: founders\' relevant credentials for this specific problem, team complementarity, advisors and network. Minimum 200 chars."\n'
    "    },\n"
    "    {\n"
    '      "title": "Go-to-Market Strategy",\n'
    '      "content": "string — 3-4 sentences: primary acquisition channel, expected acquisition cost, strategic partners, geographic or vertical expansion playbook. Minimum 200 chars."\n'
    "    },\n"
    "    {\n"
    '      "title": "Competitive Advantage and Moat",\n'
    '      "content": "string — 3-4 sentences: competitive landscape analysis, what makes the position defensible long-term (proprietary data, network effects, switching costs, regulation, IP). Minimum 200 chars."\n'
    "    }\n"
    "  ],\n"
    '  "investment": {\n'
    '    "funding_goal": "string — amount requested with round stage (e.g. \'$3M — Seed Round\')",\n'
    '    "use_of_funds": "string — allocation across 3-4 priority fronts with approximate percentage or amount and associated milestones. E.g.: \'40% product (MVP v2 + mobile), 35% commercial (10 enterprise customers), 25% operations (18-month runway)\'",\n'
    '    "runway_months": "string — runway estimate with this capital (e.g. \'18-22 months\')",\n'
    '    "key_milestones": "string — 2-3 concrete milestones that will be reached with this capital and that set up the next round"\n'
    "  },\n"
    '  "script_3min": [\n'
    '    "string — Step 1: Opening (0-20s): emotional hook or surprising data point about the problem",\n'
    '    "string — Step 2: Problem (20-45s): the specific pain and who\'s suffering from it today",\n'
    '    "string — Step 3: Solution (45-75s): how it works, the technical/commercial differentiator, and why now",\n'
    '    "string — Step 4: Market and Traction (75-110s): size of the prize and evidence that it\'s already working",\n'
    '    "string — Step 5: Team and Credibility (110-140s): why this team will win this market",\n'
    '    "string — Step 6: Ask and Next Steps (140-180s): what\'s being asked, for what, and the direct invitation"\n'
    "  ],\n"
    '  "pitch_deck": [\n'
    '    {"slide": 1, "title": "Cover", "bullets": ["tagline", "founder\'s name", "date and context of the pitch"]},\n'
    '    {"slide": 2, "title": "The Problem", "bullets": ["3-4 bullets with specific data about the pain"]},\n'
    '    {"slide": 3, "title": "Our Solution", "bullets": ["3-4 bullets describing how it works and the differentiator"]},\n'
    '    {"slide": 4, "title": "Addressable Market", "bullets": ["TAM/SAM/SOM with calculation logic", "sector growth driver"]},\n'
    '    {"slide": 5, "title": "Business Model", "bullets": ["main revenue stream", "key unit economics", "path to scale"]},\n'
    '    {"slide": 6, "title": "Traction and Validation", "bullets": ["most relevant metrics", "active customers or pilots", "growth velocity"]},\n'
    '    {"slide": 7, "title": "GTM Strategy", "bullets": ["main channel", "estimated acquisition cost", "planned expansion"]},\n'
    '    {"slide": 8, "title": "Competitive Advantage", "bullets": ["differentiator vs. alternatives", "long-term moat", "why it\'s hard to copy"]},\n'
    '    {"slide": 9, "title": "Team", "bullets": ["founders with relevant credentials", "strategic advisors"]},\n'
    '    {"slide": 10, "title": "Fundraising and Use of Capital", "bullets": ["amount requested and round stage", "allocation by front", "milestones and runway"]},\n'
    '    {"slide": 11, "title": "Vision and Roadmap", "bullets": ["where it will be in 18 months", "product or market expansion", "next round prepared"]},\n'
    '    {"slide": 12, "title": "Conclusion and Call to Action", "bullets": ["summary of the investment thesis", "direct invitation and next steps"]}\n'
    "  ],\n"
    '  "closing": "string — 3-4 final impactful sentences: synthesis of the investment thesis, why this startup will win in this market, and a clear, confident invitation for the next step. Minimum 180 chars."\n'
    "}\n\n"
    "CRITICAL RULES:\n"
    "- All \"content\" fields and long text must exclusively reflect this startup's data.\n"
    "- Never use generic text like 'large market', 'innovative solution', 'experienced team'.\n"
    "- Each pitch_deck bullet must be a complete, specific sentence (not just a word or label).\n"
    "- The script_3min should sound like the founder speaking live — not a corporate script.\n"
    "- Use the provided data as a base; where data is missing, make plausible inferences based on the sector."
)

DEFAULT_PROMPTS = {
    PURPOSE_ANALYSIS_SYSTEM: DEFAULT_ANALYSIS_SYSTEM_PROMPT,
    PURPOSE_ANALYSIS_USER: DEFAULT_ANALYSIS_USER_PROMPT,
    PURPOSE_GENERATION_SYSTEM: DEFAULT_GENERATION_SYSTEM_PROMPT,
    PURPOSE_GENERATION_USER: DEFAULT_GENERATION_USER_PROMPT,
}
