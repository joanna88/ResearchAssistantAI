import pytest
import json

from types import SimpleNamespace
from google.genai import types
from google.adk.models.llm_response import LlmResponse

from research_assistant.callbacks import (
    name_in_texts,
    guard_compound_lookup,
    save_user_message,
    extract_smiles,
    record_trusted_smiles,
    smiles_in_user_text,
    guard_trusted_smiles,
    record_mutation_summary,
    append_mutation_summary,
)


# testing name_in_text function


def test_basic_correctness():

    name = "aspirin"
    text = ["Is aspirin drug-like?"]

    assert name_in_texts(name, text) is True


def test_capitalization():

    name = "Sotorasib"
    text = ["is sotorasib drug-like?"]

    assert name_in_texts(name, text) is True


def test_substring_trap():

    name = "sotorasib"
    text = ["Is sotorasibb drug-like?"]

    assert name_in_texts(name, text) is False


def test_special_characters():

    name = "2,4-D"
    text = ["Is 2,4-D toxic?"]

    assert name_in_texts(name, text) is True


def test_empty_list():

    name = "aspirin"
    text = []

    assert name_in_texts(name, text) is False


def test_stereo_name():

    name = "(S)-ibuprofen"
    text = ["Is (S)-ibuprofen active?"]

    assert name_in_texts(name, text) is True


def test_string_text():

    name = "(S)-ibuprofen"
    text = "Is (S)-ibuprofen active?"

    assert name_in_texts(name, text) is True


# testing guard_compound_lookup tool
def test_guard_blocks_corrected_name():

    tool = SimpleNamespace(name="lookup_compound_by_name")
    content = types.Content(
        role="user", parts=[types.Part(text="Is sotorasibb drug-like?")]
    )
    context = SimpleNamespace(user_content=content, state={})
    args = {"name": "sotorasib"}

    result = guard_compound_lookup(tool, args, context)

    assert result is not None
    assert result["status"] == "error"
    assert "sotorasib" in result["error_message"]


def test_guard_allows_correct_name():

    tool = SimpleNamespace(name="lookup_compound_by_name")
    content = types.Content(
        role="user", parts=[types.Part(text="Is sotorasibb drug-like?")]
    )
    context = SimpleNamespace(user_content=content, state={})
    args = {"name": "sotorasibb"}

    result = guard_compound_lookup(tool, args, context)

    assert result is None


def test_guard_allows_other_tools():

    tool = SimpleNamespace(name="assess_druglikeness")
    content = types.Content(
        role="user", parts=[types.Part(text="Is sotorasibb drug-like?")]
    )
    context = SimpleNamespace(user_content=content, state={})
    args = {"name": "sotorasibb"}

    result = guard_compound_lookup(tool, args, context)

    assert result is None


def test_guard_no_user_message():

    tool = SimpleNamespace(name="lookup_compound_by_name")
    context = SimpleNamespace(user_content=None, state={})
    args = {"name": "aspirin"}

    result = guard_compound_lookup(tool, args, context)

    assert result is not None
    assert result["status"] == "error"


def test_guard_message_without_text():

    tool = SimpleNamespace(name="lookup_compound_by_name")
    content = types.Content(role="user", parts=[types.Part(text=None)])
    context = SimpleNamespace(user_content=content, state={})
    args = {"name": "aspirin"}

    result = guard_compound_lookup(tool, args, context)

    assert result["status"] == "error"


def test_guard_image_in_text():

    tool = SimpleNamespace(name="lookup_compound_by_name")
    content = types.Content(
        role="user",
        parts=[
            types.Part(inline_data=types.Blob(mime_type="image/png", data=b"x")),
            types.Part(text="Is aspirin drug-like?"),
        ],
    )
    context = SimpleNamespace(user_content=content, state={})
    args = {"name": "aspirin"}

    result = guard_compound_lookup(tool, args, context)

    assert result is None


# testing save_user_message


def test_save_user_message_stores_text():

    content = types.Content(
        role="user", parts=[types.Part(text="Is sotorasibb drug-like?")]
    )
    context = SimpleNamespace(user_content=content, state={"mutation_summary": "old"})

    save_user_message(context)

    assert context.state["original_user_message"] == "Is sotorasibb drug-like?"
    assert context.state["mutation_summary"] is None


def test_guard_uses_saved_user_message():

    content = types.Content(
        role="user", parts=[types.Part(text="Get SMILES for sotorasib")]
    )

    context = SimpleNamespace(
        user_content=content,
        state={"original_user_message": "Is sotorasibb drug-like?"},
    )
    tool = SimpleNamespace(name="lookup_compound_by_name")

    result = guard_compound_lookup(tool, {"name": "sotorasib"}, context)

    assert result is not None
    assert result["status"] == "error"


def test_guard_falls_back_to_user_content():
    content = types.Content(
        role="user", parts=[types.Part(text="Is aspirin drug-like?")]
    )
    context = SimpleNamespace(user_content=content, state={})
    tool = SimpleNamespace(name="lookup_compound_by_name")

    result = guard_compound_lookup(tool, {"name": "aspirin"}, context)

    assert result is None


# testing extract_smiles
def test_extract_smiles_from_lookup():

    data = {"status": "success", "smiles": "CCO", "cid": 702}

    assert extract_smiles("lookup_compound_by_name", data) == ["CCO"]


def test_extract_smiles_lookup_not_found():

    data = {"status": "not_found", "query": "xyz"}

    assert extract_smiles("lookup_compound_by_name", data) == []


def test_extract_smiles_from_activities():

    data = {
        "status": "success",
        "compounds": [{"smiles": "CCO"}, {"name": "no smiles"}, {"smiles": "CCN"}],
    }

    assert extract_smiles("get_target_activities", data) == ["CCO", "CCN"]


def test_extract_smiles_other_tool():

    assert extract_smiles("search_targets", {"targets": []}) == []


# testing record_trusted_smiles
def test_record_trusted_smiles_adds_to_state():

    tool = SimpleNamespace(name="lookup_compound_by_name")
    response = {
        "content": [
            {"type": "text", "text": json.dumps({"status": "success", "smiles": "CCO"})}
        ]
    }
    context = SimpleNamespace(state={"trusted_smiles:CCN": True})

    record_trusted_smiles(tool, {}, context, response)

    assert "trusted_smiles:CCN" in context.state
    assert "trusted_smiles:CCO" in context.state


def test_record_trusted_smiles_ignores_unexpected_response():

    tool = SimpleNamespace(name="lookup_compound_by_name")
    context = SimpleNamespace(state={})

    record_trusted_smiles(tool, {}, context, {})

    assert context.state == {}


# testing smiles_in_user_text
def test_user_smiles_basic():

    assert "CCO" in smiles_in_user_text("Is CCO drug-like?")


def test_user_smiles_quotes_and_commas():

    tokens = smiles_in_user_text('Compare "CCO", c1ccccc1; CCN')

    assert {"CCO", "c1ccccc1", "CCN"} <= tokens


def test_user_smiles_truncated_not_matched():

    tokens = smiles_in_user_text("Check CC(=O)Oc1ccccc1C(=O)O please")

    assert "CC(=O)Oc1ccccc1C(=O)O" in tokens
    assert "CC(=O)Oc1ccccc1" not in tokens


def test_user_smiles_quoted_at_sentence_end():

    tokens = smiles_in_user_text('Check `CC(=O)O`. Is "CCO"?')

    assert {"CC(=O)O", "CCO"} <= tokens


# testing guard_trusted_smiles
def make_context(state, user_text=None):
    """Fake tool_context with the given state and (optionally) a user message."""

    content = None
    if user_text is not None:
        content = types.Content(role="user", parts=[types.Part(text=user_text)])

    return SimpleNamespace(state=state, user_content=content)


ASSESS = SimpleNamespace(name="assess_druglikeness")


def test_trusted_smiles_allowed():

    context = make_context(state={"trusted_smiles:CCO": True})

    result = guard_trusted_smiles(ASSESS, {"smiles_list": ["CCO"]}, context)

    assert result is None


def test_user_typed_smiles_allowed():

    context = make_context(state={"original_user_message": "Is CCN drug-like?"})

    result = guard_trusted_smiles(ASSESS, {"smiles_list": ["CCN"]}, context)

    assert result is None


def test_truncated_smiles_blocked():

    context = make_context(state={"trusted_smiles:CC(=O)Oc1ccccc1C(=O)O": True})

    result = guard_trusted_smiles(ASSESS, {"smiles_list": ["CC(=O)Oc1ccccc1"]}, context)

    assert result is not None
    assert result["status"] == "error"
    assert "CC(=O)Oc1ccccc1" in result["error_message"]


def test_untrusted_query_smiles_blocked():

    tool = SimpleNamespace(name="tanimoto_similarity")
    context = make_context(state={"trusted_smiles:CCO": True})

    result = guard_trusted_smiles(
        tool, {"query_smiles": "CCN", "smiles_list": ["CCO"]}, context
    )

    assert result is not None
    assert "CCN" in result["error_message"]


def test_other_tools_not_checked():

    tool = SimpleNamespace(name="search_literature")
    context = make_context(state={})

    result = guard_trusted_smiles(tool, {"question": "anything"}, context)

    assert result is None


def test_parallel_recording_keeps_both_smiles():

    tool = SimpleNamespace(name="lookup_compound_by_name")

    def response_for(smiles):
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({"status": "success", "smiles": smiles}),
                }
            ]
        }

    # 1. two parallel calls, each starting from its own copy of the same (empty) state
    call_a = SimpleNamespace(state={})
    call_b = SimpleNamespace(state={})

    # 2. each call records its own compound
    record_trusted_smiles(
        tool, {}, call_a, response_for("CC(=O)OC1=CC=CC=C1C(=O)O")
    )  # aspirin
    record_trusted_smiles(
        tool, {}, call_b, response_for("CC(C)CC1=CC=C(C=C1)C(C)C(=O)O")
    )  # ibuprofen

    # 3. the coordinator merges both results, one after the other (like ADK does)
    coordinator_state = {}
    coordinator_state.update(call_a.state)
    coordinator_state.update(call_b.state)

    # both SMILES must have survived the merge
    assert "trusted_smiles:CC(=O)OC1=CC=CC=C1C(=O)O" in coordinator_state
    assert "trusted_smiles:CC(C)CC1=CC=C(C=C1)C(C)C(=O)O" in coordinator_state


def test_record_mutation_summary_stores_it():

    tool = SimpleNamespace(name="get_target_activities")
    summary = (
        "0 of 10 results annotated with G12C (results are not filtered by mutation)"
    )
    response = {
        "content": [
            {
                "type": "text",
                "text": json.dumps({"status": "success", "mutation_summary": summary}),
            }
        ]
    }
    context = SimpleNamespace(state={})

    record_mutation_summary(tool, {}, context, response)

    assert context.state["mutation_summary"] == summary


def test_record_mutation_summary_ignores_other_tools():

    tool = SimpleNamespace(name="lookup_compound_by_name")
    context = SimpleNamespace(state={})

    record_mutation_summary(
        tool, {}, context, {"content": [{"type": "text", "text": "{}"}]}
    )

    assert "mutation_summary" not in context.state


# testing append_mutation_summary
SUMMARY = "0 of 10 results annotated with G12C (results are not filtered by mutation)"


def make_response(*parts, partial=False):
    return LlmResponse(
        content=types.Content(role="model", parts=list(parts)), partial=partial
    )


def test_append_summary_when_missing():

    context = SimpleNamespace(state={"mutation_summary": SUMMARY})
    response = make_response(
        types.Part(text="Here are the most potent KRAS compounds.")
    )

    result = append_mutation_summary(context, response)

    assert result is not None
    final_text = "".join(p.text or "" for p in result.content.parts)
    assert SUMMARY in final_text


def test_no_append_when_already_included():

    context = SimpleNamespace(state={"mutation_summary": SUMMARY})
    response = make_response(types.Part(text=f"Results below. {SUMMARY}"))

    result = append_mutation_summary(context, response)

    assert result is None


def test_no_append_to_function_call():

    context = SimpleNamespace(state={"mutation_summary": SUMMARY})
    call = types.Part(
        function_call=types.FunctionCall(name="analysis_agent", args={"request": "..."})
    )
    response = make_response(call)

    result = append_mutation_summary(context, response)

    assert result is None


def test_no_append_without_summary():

    context = SimpleNamespace(state={"mutation_summary": None})
    response = make_response(
        types.Part(text="Aspirin has a molecular weight of 180.16 Da.")
    )

    result = append_mutation_summary(context, response)

    assert result is None


def test_no_append_to_partial_response():

    context = SimpleNamespace(state={"mutation_summary": SUMMARY})
    response = make_response(types.Part(text="Here are the most"), partial=True)

    result = append_mutation_summary(context, response)

    assert result is None
