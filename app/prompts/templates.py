"""
Prompt template formatters for formatting incoming user requests safely into model inputs.
"""



def build_analysis_prompt(
    decision_description: str,
    drawing_factors: str,
    options_considered: str | None = None,
    deadline_or_stakes: str | None = None,
) -> str:
    """
    Wraps user decision input inside explicit data delimiter tags
    to resist prompt injection and enforce context boundaries.
    """
    options_part = f"\n- Options Being Considered: {options_considered}" if options_considered else ""
    deadline_part = f"\n- Timeline / Deadline / Stakes: {deadline_or_stakes}" if deadline_or_stakes else ""

    return f"""Please perform a thorough Socratic cognitive analysis on the following decision scenario.
Break it down into the requested structured JSON format, referencing the user's specific circumstances.

<USER_DECISION_DATA>
- Decision Details & Context:
{decision_description.strip()}

- What is Drawing the User Toward It / Salient Focus:
{drawing_factors.strip()}
{options_part}
{deadline_part}
</USER_DECISION_DATA>

Remember:
- Do NOT advise or make a decision.
- Identify what was emphasized, what was overlooked, unstated assumptions with how to test them, internal conflicts with direct quotes, the strongest case for the other perspective, and 5-7 open Socratic probing questions.
"""


def build_followup_prompt(
    original_context_summary: str,
    question: str,
    user_answer: str,
    reflection_history: list | None = None,
) -> str:
    """
    Constructs the prompt for the follow-up reflection loop.
    """
    history_text = ""
    if reflection_history:
        history_text = "\nPrevious Reflection Steps:\n"
        for step in reflection_history[-3:]:  # Keep recent history concise
            history_text += f"- Question: {step.get('question')}\n  Answer: {step.get('answer')}\n"

    return f"""Context Summary of Original Decision:
{original_context_summary}
{history_text}
Current Reflection Step:
<QUESTION_PROBED>
{question.strip()}
</QUESTION_PROBED>

<USER_RESPONSE_DATA>
{user_answer.strip()}
</USER_RESPONSE_DATA>

Provide an objective summary of their reflection, 1 to 3 deeper follow-up questions, and any newly exposed blind spots.
Do NOT give advice or decide for the user.
"""
