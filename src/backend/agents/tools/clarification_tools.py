from langchain_core.tools import tool


@tool
def request_clarification(question: str) -> dict:
    """Use this when the patient's request is too ambiguous to safely route or
    act on — e.g. it doesn't say which department/symptom area, whether they
    want to book/reschedule/cancel, or which appointment/document it refers
    to. Call this instead of guessing or calling any other tool, with one
    short, specific question to ask the patient. This pauses the workflow
    until the patient replies; do not call it more than once per turn."""
    return {"clarification_requested": True, "question": question}
