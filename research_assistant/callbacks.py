import re
import json
from google.adk.tools import BaseTool, ToolContext


def name_in_texts(name: str, texts: list[str]) -> bool:
    """Check whether the name appears as a whole term in any of the texts."""

    if isinstance(texts, str):
        texts = [texts]

    pattern = rf"(?<!\w){re.escape(name.casefold())}(?!\w)"
    return any(re.search(pattern, text.casefold()) for text in texts)


def guard_compound_lookup(
    tool: BaseTool, args: dict, tool_context: ToolContext
) -> dict | None:
    """
    Guard compound-name lookups against silent name correction.

    Applies only to `lookup_compound_by_name`. The lookup is allowed only when
    the requested compound name appears in the user's message. This prevents
    the agent from correcting, changing, or substituting a compound name before
    performing a lookup.

    Args:
        tool: Tool being called.
        args: Arguments passed to the tool, including the compound `name`.
        tool_context: Context containing the current user message.

    Returns:
        None if the tool call is allowed. Otherwise, an error dictionary
        explaining why the lookup was blocked.
    """

    if tool.name != "lookup_compound_by_name":
        return None

    saved = tool_context.state.get("original_user_message")

    if saved:
        texts = [saved]
    elif tool_context.user_content is not None:
        texts = [part.text for part in tool_context.user_content.parts if part.text]
    else:
        return {
            "status": "error",
            "error_message": "There is no user message to check against. Ask the user to confirm the compound name.",
        }

    name = args.get("name", "")

    if name_in_texts(name, texts) is False:
        return {
            "status": "error",
            "error_message": f"The name '{name}' does not appear in the user's message. "
            "Do not correct or change compound names; ask the user to "
            "confirm the intended compound.",
        }

    return None


def save_user_message(callback_context) -> None:
    """Store the user's original message in state, so specialists can check against it."""

    content = callback_context.user_content
    texts = [part.text for part in content.parts if part.text] if content else []
    callback_context.state["original_user_message"] = "\n".join(texts)

    return None


def extract_smiles(tool_name: str, data: dict) -> list[str]:
    """Return the SMILES contained in a PubChem or ChEMBL tool result."""

    if tool_name == "lookup_compound_by_name":
        smiles = data.get("smiles")
        return [smiles] if smiles else []

    if tool_name == "get_target_activities":
        return [c["smiles"] for c in data.get("compounds", []) if c.get("smiles")]

    return []


def record_trusted_smiles(
    tool: BaseTool, args: dict, tool_context: ToolContext, tool_response: dict
) -> None:
    """
    Record trusted SMILES returned by approved tool calls.

    Parses the tool response and extracts SMILES using `extract_smiles`.
    Any extracted SMILES are appended to `trusted_smiles` in the tool context
    state so they can be recognized as trusted inputs by subsequent tool calls.

    If the response cannot be parsed or contains no trusted SMILES, the
    function leaves the context state unchanged.

    Args:
        tool: Tool that produced the response.
        args: Arguments passed to the tool.
        tool_context: Tool context containing the persistent state used to
            store trusted SMILES.
        tool_response: Tool response containing the data from which trusted
            SMILES may be extracted.

    Returns:
        None.
    """

    try:
        data = json.loads(tool_response["content"][0]["text"])
    except (KeyError, IndexError, TypeError, ValueError):
        return None

    new = extract_smiles(tool.name, data)

    if new:
        existing = tool_context.state.get("trusted_smiles", [])
        tool_context.state["trusted_smiles"] = existing + new

    return None
