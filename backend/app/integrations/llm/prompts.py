"""
LLM Prompt templates and prompt engineering for technician recommendations.

Separates prompt structure from network transport adapters.
Enforces privacy restrictions and grounding rules to prevent model hallucinations.
"""

from __future__ import annotations

import json

from app.integrations.llm.provider import LLMRecommendationRequest

SYSTEM_PROMPT = """You are an Intelligent IT Service Management (I-ITSM) Recommendation Assistant.
Your sole responsibility is to evaluate an explicit list of pre-filtered technician candidates
and rank them according to their suitability for resolving a reported IT incident.

STRICT OPERATIONAL & PRIVACY RULES:
1. ONLY reason over information provided in the input payload.
2. DO NOT invent, extrapolate, or hallucinate:
   - Past incident resolutions or unlisted achievements.
   - Additional skills or certifications not explicitly provided.
   - Fictional employee identities, names, or contact details.
3. Hard eligibility (availability and core skill requirements) has ALREADY been enforced
   by deterministic rules. Your role is contextual ranking, tie-breaking, and generating
   transparent, explainable justifications.
4. Output MUST BE valid JSON conforming strictly to the requested schema. No conversational filler,
   no Markdown ticks, just the raw JSON object.
"""

USER_PROMPT_TEMPLATE = """Evaluate the following technician candidates for this incident:

=== INCIDENT DETAILS ===
Category: {category}
Priority: {priority}
Required Skill: {required_skill}
Description: {description}

=== ELIGIBLE CANDIDATES ===
{candidates_json}

=== REQUIRED JSON OUTPUT FORMAT ===
{{
  "rankings": [
    {{
      "technicianId": "<UUID string matching candidate id>",
      "rank": 1,
      "relevanceScore": <float 0.0 to 100.0>,
      "explanation": "<factual explanation referencing candidate skill level, experience, and current workload>"
    }}
  ],
  "reasoning": "<concise synthesis of why the top technician is recommended>",
  "confidence": <float 0.0 to 1.0>
}}
"""


def build_recommendation_prompt(request: LLMRecommendationRequest) -> dict[str, str]:
    """
    Format system and user prompts from the incoming structured recommendation request.
    """
    candidates_data = [
        {
            "id": c.id,
            "skills": c.skills,
            "experienceYears": c.experience_years,
            "activeIncidents": c.active_incidents,
            "maxCapacity": c.max_capacity,
        }
        for c in request.candidates
    ]

    candidates_formatted = json.dumps(candidates_data, indent=2)

    user_prompt = USER_PROMPT_TEMPLATE.format(
        category=request.incident_category,
        priority=request.incident_priority,
        required_skill=request.required_skill,
        description=request.incident_description,
        candidates_json=candidates_formatted,
    )

    return {
        "system": SYSTEM_PROMPT.strip(),
        "user": user_prompt.strip(),
    }
