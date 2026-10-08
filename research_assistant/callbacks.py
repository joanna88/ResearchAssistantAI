import re
from google.adk.tools import BaseTool, ToolContext

def name_in_texts(name: str, texts: list[str]) -> bool:
    """Check whether the name appears as a whole term in any of the texts."""

    if isinstance(texts, str):
        texts = [texts]

    pattern = rf"(?<!\w){re.escape(name.casefold())}(?!\w)"
    return any(re.search(pattern, text.casefold()) for text in texts)


def guard_compound_lookup(tool: BaseTool, args: dict, tool_context: ToolContext) -> dict | None:
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

    if tool_context.user_content is None:
        return {"status": "error", 
                "error_message": "There is no user content. Ask the user to confirm the compound name"
        }
    
    parts = [part.text for part in tool_context.user_content.parts if part.text]
    name = args.get("name", "")

    if name_in_texts(name, parts) is False:
        return {"status": "error", 
                "error_message": f"The name '{name}' does not appear in the user's message. "
                                "Do not correct or change compound names; ask the user to "
                                "confirm the intended compound."
        }
    
    return None
