import pytest
from research_assistant.callbacks import name_in_texts, guard_compound_lookup, save_user_message
from types import SimpleNamespace
from google.genai import types


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

    content = types.Content(role="user", 
                            parts=[types.Part(text="Is sotorasibb drug-like?")])
    context = SimpleNamespace(user_content=content, state={})

    save_user_message(context)

    assert context.state["original_user_message"] == "Is sotorasibb drug-like?"


def test_guard_uses_saved_user_message():
   
    content = types.Content(role="user", parts=[types.Part(text="Get SMILES for sotorasib")])
  
    context = SimpleNamespace(user_content=content,
                              state={"original_user_message": "Is sotorasibb drug-like?"})
    tool = SimpleNamespace(name="lookup_compound_by_name")

    result = guard_compound_lookup(tool, {"name": "sotorasib"}, context)

    assert result is not None
    assert result["status"] == "error"


def test_guard_falls_back_to_user_content():
    content = types.Content(role="user", parts=[types.Part(text="Is aspirin drug-like?")])
    context = SimpleNamespace(user_content=content, state={})  
    tool = SimpleNamespace(name="lookup_compound_by_name")

    result = guard_compound_lookup(tool, {"name": "aspirin"}, context)

    assert result is None

