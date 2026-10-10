import re
import json

from google.adk.tools import BaseTool, ToolContext
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse
from google.genai import types

from research_assistant.tools.chem_tools import _clean_smiles


def name_in_texts(name: str, texts: list[str]) -> bool:
    """Check whether a name appears as an exact term in any provided text.

    Args:
        name: Name to search for.
        texts: Text or list of texts to search.

    Returns:
        True if the name is found as an exact term, otherwise False.
    """

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
    """Store the user's original message and mutation summary in the callback state.

    Args:
        callback_context: Context containing the user message and state.

    Returns:
        None.
    """

    content = callback_context.user_content
    texts = [part.text for part in content.parts if part.text] if content else []
    callback_context.state["original_user_message"] = "\n".join(texts)
    callback_context.state["mutation_summary"] = None

    return None


def extract_smiles(tool_name: str, data: dict) -> list[str]:
    """Extract SMILES from supported PubChem or ChEMBL tool results.

    Args:
        tool_name: Name of the tool that produced the result.
        data: Parsed tool result containing molecular data.

    Returns:
        List of SMILES found in the tool result, or an empty list if none are found.
    """

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

    for smiles in extract_smiles(tool.name, data):
        tool_context.state[f"trusted_smiles:{smiles}"] = True

    return None


def smiles_in_user_text(text: str) -> set[str]:
    """
    Extract candidate SMILES tokens from user-provided text.

    Splits the text on whitespace, commas, and semicolons, then removes common
    surrounding delimiters and trailing sentence punctuation. The resulting
    tokens can be used to check whether a SMILES passed to a tool was explicitly
    present in the user's message.

    This function does not validate whether the extracted tokens are chemically
    valid SMILES.

    Args:
        text: User-provided text to tokenize.

    Returns:
        Set of cleaned candidate tokens from the text.
    """

    tokens = re.split(r"[\s,;]+", text)

    return {_clean_smiles(t.rstrip(".?!")) for t in tokens if t}


def guard_trusted_smiles(
    tool: BaseTool, args: dict, tool_context: ToolContext
) -> dict | None:
    """
    Guard RDKit tool calls against untrusted or altered SMILES.

    Applies only to `assess_druglikeness` and `tanimoto_similarity`. Every
    SMILES passed to these tools must come from one of two allowed sources:
    it must either appear explicitly in the user's original message or have
    been returned by an approved lookup tool and recorded in `trusted_smiles`.

    Both `smiles_list` entries and `query_smiles` are checked. SMILES are
    cleaned only for comparison with their trusted or user-provided forms.
    This prevents the agent from inventing, reconstructing, correcting, or
    altering SMILES before passing them to RDKit tools.

    Args:
        tool: Tool being called.
        args: Arguments the agent intends to pass to the tool.
        tool_context: Tool context containing trusted SMILES and user-message
            information.

    Returns:
        None if all requested SMILES have an allowed source or the guard does
        not apply to the tool. Otherwise, an error dictionary identifying the
        untrusted SMILES and blocking the tool call.
    """

    if tool.name not in ("assess_druglikeness", "tanimoto_similarity"):
        return None

    # collect every SMILES the LLM wants to use in this call
    smiles_list = args.get("smiles_list", [])

    if isinstance(smiles_list, str):
        smiles_list = [smiles_list]
    requested = list(smiles_list)

    if args.get("query_smiles"):
        requested.append(args["query_smiles"])

    # checking the two allowed sources

    user_text = tool_context.state.get("original_user_message") or ""

    if not user_text and tool_context.user_content is not None:
        user_text = "\n".join(p.text for p in tool_context.user_content.parts if p.text)

    user_tokens = smiles_in_user_text(user_text)

    untrusted = [
        s
        for s in requested
        if f"trusted_smiles:{_clean_smiles(s)}" not in tool_context.state
        and _clean_smiles(s) not in user_tokens
    ]

    if untrusted:
        return {
            "status": "error",
            "error_message": (
                f"These SMILES were not returned by a lookup tool or given by the user "
                f"(they may have been altered while copying): {untrusted}. "
                "Use SMILES exactly as returned; do not retype, shorten, or correct them."
            ),
        }

    return None


def record_mutation_summary(
    tool: BaseTool, args: dict, tool_context: ToolContext, tool_response: dict
) -> None:
    """Store the mutation summary returned by `get_target_activities` in state.

    Args:
        tool: Tool that produced the response.
        args: Arguments passed to the tool.
        tool_context: Context containing the state used to store the summary.
        tool_response: Tool response containing the mutation summary.

    Returns:
        None.
    """

    if tool.name != "get_target_activities":
        return None

    try:
        data = json.loads(tool_response["content"][0]["text"])
    except (KeyError, IndexError, TypeError, ValueError):
        return None

    summary = data.get("mutation_summary")
    if summary:
        tool_context.state["mutation_summary"] = summary
    return None


def append_mutation_summary(
    callback_context: CallbackContext,
    llm_response: LlmResponse,
) -> LlmResponse | None:
    """Append the stored ChEMBL mutation summary if missing from the final response.

    Args:
        callback_context: Context containing the stored mutation summary.
        llm_response: Model response to inspect and optionally modify.

    Returns:
        Modified LLM response if the mutation summary is appended, otherwise None.
    """

    summary = callback_context.state.get("mutation_summary")

    if not summary or llm_response.partial:
        return None

    content = llm_response.content

    if not content or not content.parts:
        return None

    if any(part.function_call for part in content.parts):
        return None

    text = "".join(part.text or "" for part in content.parts)

    if summary in text:
        return None

    content.parts.append(
        types.Part(text=f"\n\n**Mutation note (from ChEMBL):** {summary}")
    )
    return llm_response
