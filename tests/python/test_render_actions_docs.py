"""Unit tests for ``scripts/render-actions-docs.py``.

The renderer consumes ``data/actions/`` (one JSON file per provider,
published by the ``lodolai/lodol`` server repo) and emits the
Integrations tab: one MDX page per app or built-in step group, the
directory page, the ``meta.json`` files and ``catalog.json``. These
tests cover:

    - the pure helpers (param-type mapping, mock synthesis, MDX
      escaping, JSX attributes, YAML quoting, slugs and anchors)
    - the higher-level page/directory/meta/catalog generators
    - input loading (``load_specs``) including missing/malformed input
    - end-to-end orchestration through ``render`` and ``main``

The renderer has no dependency on Python AST or on any server code, so
the tests don't need a fake provider directory — they feed dicts
directly.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2] / "scripts" / "render-actions-docs.py"
)


def _load_renderer():
    """Load the renderer script as a module (hyphen in filename)."""
    spec = importlib.util.spec_from_file_location(
        "render_actions_docs", SCRIPT_PATH
    )
    assert spec and spec.loader, "could not load renderer script"
    module = importlib.util.module_from_spec(spec)
    sys.modules["render_actions_docs"] = module
    spec.loader.exec_module(module)
    return module


ren = _load_renderer()


class ParamTypeTests(unittest.TestCase):
    def test_known_enum_values(self):
        self.assertEqual(ren._param_type("ParameterType.STRING"), "string")
        self.assertEqual(ren._param_type("ParameterType.NUMBER"), "number")
        self.assertEqual(ren._param_type("ParameterType.BOOLEAN"), "boolean")
        self.assertEqual(ren._param_type("ParameterType.OBJECT"), "object")
        self.assertEqual(ren._param_type("ParameterType.ARRAY"), "array")

    def test_unknown_falls_back_to_lowercase_leaf(self):
        self.assertEqual(ren._param_type("ParameterType.WEIRD"), "weird")

    def test_non_string_defaults_to_string(self):
        self.assertEqual(ren._param_type(None), "string")
        self.assertEqual(ren._param_type(123), "string")


class JsonBodyExampleTests(unittest.TestCase):
    def test_only_required_params_included(self):
        params = [
            {"name": "a", "type": "ParameterType.STRING", "required": True},
            {"name": "b", "type": "ParameterType.STRING", "required": False},
        ]
        self.assertEqual(ren._json_body_example(params), {"a": "your_a"})

    def test_synthesises_value_per_type(self):
        params = [
            {"name": "s", "type": "ParameterType.STRING", "required": True},
            {"name": "n", "type": "ParameterType.NUMBER", "required": True},
            {"name": "b", "type": "ParameterType.BOOLEAN", "required": True},
            {"name": "o", "type": "ParameterType.OBJECT", "required": True},
            {"name": "a", "type": "ParameterType.ARRAY", "required": True},
        ]
        self.assertEqual(
            ren._json_body_example(params),
            {"s": "your_s", "n": 10, "b": True, "o": {}, "a": []},
        )

    def test_ignores_non_dict_entries(self):
        params = [
            "not a dict",
            {"name": "x", "type": "ParameterType.STRING", "required": True},
        ]
        self.assertEqual(ren._json_body_example(params), {"x": "your_x"})

    def test_empty_input(self):
        self.assertEqual(ren._json_body_example([]), {})


class SchemaExampleTests(unittest.TestCase):
    def test_primitives(self):
        self.assertEqual(ren._schema_example({"type": "string"}), "example_value")
        self.assertEqual(ren._schema_example({"type": "number"}), 1)
        self.assertEqual(ren._schema_example({"type": "integer"}), 1)
        self.assertEqual(ren._schema_example({"type": "boolean"}), True)
        self.assertEqual(ren._schema_example({"type": "array"}), [])

    def test_object_with_properties(self):
        schema = {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "count": {"type": "number"},
            },
        }
        self.assertEqual(
            ren._schema_example(schema), {"id": "example_value", "count": 1}
        )

    def test_object_without_properties(self):
        self.assertEqual(ren._schema_example({"type": "object"}), {})

    def test_default_type_string(self):
        self.assertEqual(ren._schema_example({}), "example_value")

    def test_unknown_type(self):
        self.assertIsNone(ren._schema_example({"type": "weird"}))


class MockFromReturnsTests(unittest.TestCase):
    def test_non_dict_returns_default_success(self):
        self.assertEqual(ren._mock_from_returns(None), {"status": "success"})
        self.assertEqual(ren._mock_from_returns("oops"), {"status": "success"})

    def test_null_or_missing_type(self):
        self.assertEqual(ren._mock_from_returns({}), {"status": "success"})
        self.assertEqual(
            ren._mock_from_returns({"type": "null"}), {"status": "success"}
        )

    def test_primitive_types(self):
        self.assertEqual(ren._mock_from_returns({"type": "string"}), "example_value")
        self.assertEqual(ren._mock_from_returns({"type": "number"}), 1)
        self.assertEqual(ren._mock_from_returns({"type": "boolean"}), True)

    def test_array_of_strings(self):
        result = ren._mock_from_returns(
            {"type": "array", "items": {"type": "string"}}
        )
        self.assertEqual(result, ["value_1", "value_2"])

    def test_array_of_objects(self):
        schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"id": {"type": "string"}},
            },
        }
        self.assertEqual(ren._mock_from_returns(schema), [{"id": "example_value"}])

    def test_array_with_no_items(self):
        self.assertEqual(ren._mock_from_returns({"type": "array"}), [])

    def test_object_with_properties(self):
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "score": {"type": "number"},
            },
        }
        self.assertEqual(
            ren._mock_from_returns(schema),
            {"name": "example_value", "score": 1},
        )

    def test_object_without_properties(self):
        self.assertEqual(
            ren._mock_from_returns({"type": "object"}),
            {"status": "success"},
        )

    def test_integer_is_a_number(self):
        self.assertEqual(ren._mock_from_returns({"type": "integer"}), 1)


class ReturnsExampleTests(unittest.TestCase):
    def test_uses_the_first_example_the_schema_lists(self):
        schema = {"type": "number", "examples": [42.5, 7]}
        self.assertEqual(ren._returns_example(schema), 42.5)

    def test_an_example_can_be_falsy(self):
        schema = {"type": "boolean", "examples": [False]}
        self.assertIs(ren._returns_example(schema), False)

    def test_without_examples_makes_one_up_from_the_type(self):
        self.assertEqual(ren._returns_example({"type": "string"}), "example_value")
        self.assertEqual(
            ren._returns_example({"type": "string", "examples": []}), "example_value"
        )
        self.assertEqual(ren._returns_example(None), {"status": "success"})


class OutputsSectionTests(unittest.TestCase):
    """The outputs and example part of an action's section."""

    def _section(self, **action):
        return ren.generate_action_section(
            "act", {"display_name": "Act", "description": "", **action}
        )

    def test_starts_with_the_outputs_description(self):
        out = self._section(
            returns={"type": "number", "description": "The sum, {rounded}."},
            mock_response=12,
        )
        self.assertIn('<Fields title="Outputs" description="The sum, {rounded}." />', out)
        self.assertIn("```json\n12\n```", out)

    def test_lists_each_output_field_with_its_type_and_description(self):
        out = self._section(
            returns={
                "type": "object",
                "properties": {
                    "label_id": {"type": "string", "description": "Label ID"},
                    "count": {"type": "integer"},
                },
            }
        )
        self.assertIn('<Field id="label_id" type="text" description="Label ID" />', out)
        self.assertIn('<Field id="count" type="number" />', out)

    def test_a_primitive_output_says_what_it_returns(self):
        self.assertIn('description="Returns a number."', self._section(returns={"type": "number"}))
        self.assertIn('description="Returns text."', self._section(returns={"type": "string"}))
        self.assertIn('description="Returns a list."', self._section(returns={"type": "array"}))

    def test_shows_the_schemas_example_when_there_is_no_mock(self):
        out = self._section(returns={"type": "number", "examples": [42.5]})
        self.assertIn("```json\n42.5\n```", out)

    def test_a_mock_wins_over_the_schemas_example(self):
        out = self._section(
            returns={"type": "number", "examples": [42.5]}, mock_response=3
        )
        self.assertIn("```json\n3\n```", out)
        self.assertNotIn("42.5", out)

    def test_the_example_is_tucked_away(self):
        out = self._section(returns={"type": "number"}, mock_response=3)
        self.assertIn("<Example>\n\n```json\n3\n```\n\n</Example>", out)

    def test_no_output_says_so_instead_of_a_made_up_payload(self):
        out = self._section(returns={"type": "null"})
        self.assertIn('<Fields title="Outputs" description="This action has no output." />', out)
        self.assertNotIn("```json", out)
        self.assertNotIn('"status"', out)

    def test_no_output_with_a_description_shows_only_the_description(self):
        out = self._section(
            returns={"type": "null", "description": "Nothing; the run pauses here."}
        )
        self.assertIn('description="Nothing; the run pauses here."', out)
        self.assertNotIn("has no output", out)
        self.assertNotIn("```json", out)

    def test_a_mock_is_still_shown_when_the_schema_says_null(self):
        out = self._section(returns={"type": "null"}, mock_response={"sent": True})
        self.assertIn('"sent": true', out)


class MockToJsonTests(unittest.TestCase):
    def test_none_returns_default_success_payload(self):
        out = ren._mock_to_json(None)
        self.assertIn('"status"', out)
        self.assertIn('"success"', out)

    def test_pretty_prints_with_two_spaces(self):
        out = ren._mock_to_json({"a": 1, "b": [2]})
        self.assertIn('\n  "a": 1', out)

    def test_handles_tuples_and_sets(self):
        out = ren._mock_to_json({"items": (1, 2, 3), "tags": {"b", "a"}})
        parsed = json.loads(out)
        self.assertEqual(parsed["items"], [1, 2, 3])
        self.assertEqual(parsed["tags"], ["a", "b"])

    def test_unserialisable_falls_back_to_string(self):
        class Weird:
            def __repr__(self):
                return "weird-thing"

        out = ren._mock_to_json(Weird())
        parsed = json.loads(out)
        self.assertIsInstance(parsed, str)
        self.assertIn("weird", parsed)


class EscapeMdxTests(unittest.TestCase):
    def test_escapes_jsx_delimiters(self):
        self.assertEqual(ren._escape_mdx("{a}"), "&#123;a&#125;")

    def test_escapes_less_than(self):
        self.assertEqual(ren._escape_mdx("a < b"), "a &lt; b")

    def test_none_returns_empty(self):
        self.assertEqual(ren._escape_mdx(None), "")

    def test_non_string_is_stringified(self):
        self.assertEqual(ren._escape_mdx(123), "123")

    def test_cell_escapes_pipes_and_newlines(self):
        self.assertEqual(
            ren._escape_mdx_cell("a|b\nc"),
            "a\\|b c",
        )

    def test_cell_combines_mdx_and_table_escapes(self):
        self.assertEqual(
            ren._escape_mdx_cell("{x}|y<z"),
            "&#123;x&#125;\\|y&lt;z",
        )

    def test_escapes_image_syntax(self):
        self.assertEqual(
            ren._escape_mdx("Mention someone with ![](@U123)."),
            "Mention someone with !\\[](@U123).",
        )

    def test_leaves_image_syntax_in_code_spans(self):
        text = "Mention someone with `![](@U123)` or ``a ` ![](#C123)``."
        self.assertEqual(ren._escape_mdx(text), text)

    def test_unclosed_or_escaped_backtick_does_not_start_code_span(self):
        self.assertEqual(ren._escape_mdx("a ` ![](x)"), "a ` !\\[](x)")
        self.assertEqual(ren._escape_mdx("\\` ![](x) `"), "\\` !\\[](x) `")


class YamlQuoteTests(unittest.TestCase):
    def test_basic_quote(self):
        self.assertEqual(ren._yaml_quote("hello"), '"hello"')

    def test_escapes_backslash_and_quote(self):
        self.assertEqual(ren._yaml_quote('a\\b"c'), '"a\\\\b\\"c"')

    def test_none_yields_empty_quoted_string(self):
        self.assertEqual(ren._yaml_quote(None), '""')


class ProviderIdToSlugTests(unittest.TestCase):
    def test_underscores_become_hyphens(self):
        self.assertEqual(ren.provider_id_to_slug("google_sheets"), "google-sheets")
        self.assertEqual(ren.provider_id_to_slug("notion"), "notion")
        self.assertEqual(ren.provider_id_to_slug("a_b_c_d"), "a-b-c-d")


class TypeLabelTests(unittest.TestCase):
    def test_parameter_types_use_the_editors_words(self):
        self.assertEqual(ren._type_label("ParameterType.STRING"), "text")
        self.assertEqual(ren._type_label("ParameterType.ARRAY"), "list")
        self.assertEqual(ren._type_label("ParameterType.BOOLEAN"), "true/false")
        self.assertEqual(ren._type_label("ParameterType.DATETIME"), "date and time")

    def test_schema_types_too(self):
        self.assertEqual(ren._type_label("integer"), "number")
        self.assertEqual(ren._type_label("object"), "object")
        self.assertEqual(ren._type_label(["string", "null"]), "text")

    def test_unknown_or_missing(self):
        self.assertEqual(ren._type_label("ParameterType.WEIRD"), "weird")
        self.assertEqual(ren._type_label(None), "")


class JsxAttrTests(unittest.TestCase):
    def test_plain_text_is_quoted(self):
        self.assertEqual(ren._jsx_attr("name", "Message ID"), 'name="Message ID"')

    def test_markup_characters_stay_as_written(self):
        # A quoted attribute holds `<`, braces and pipes as they are.
        self.assertEqual(
            ren._jsx_attr("description", "a <b> {c} | `d`"),
            'description="a <b> {c} | `d`"',
        )

    def test_quotes_ampersands_and_backslashes_become_an_expression(self):
        self.assertEqual(ren._jsx_attr("d", 'say "hi"'), 'd={"say \\"hi\\""}')
        self.assertEqual(ren._jsx_attr("d", "R&D"), 'd={"R&D"}')
        self.assertEqual(ren._jsx_attr("d", "a\\b"), 'd={"a\\\\b"}')

    def test_line_breaks_are_flattened(self):
        self.assertEqual(ren._jsx_attr("d", "one\ntwo  three"), 'd="one two three"')


class SlugTests(unittest.TestCase):
    def test_github_slug(self):
        self.assertEqual(ren.github_slug("Send a message to a channel"), "send-a-message-to-a-channel")
        self.assertEqual(ren.github_slug("Get (v2) message: <id>!"), "get-v2-message-id")
        self.assertEqual(ren.github_slug("Today's date"), "todays-date")
        self.assertEqual(ren.github_slug("Café_au lait"), "café_au-lait")

    def test_repeated_headings_get_a_counter(self):
        slugger = ren.Slugger()
        self.assertEqual(
            [slugger.slug(t) for t in ["Actions", "Send", "Send", "Actions", "Send"]],
            ["actions", "send", "send-1", "actions-1", "send-2"],
        )


class FirstSentenceTests(unittest.TestCase):
    def test_takes_the_first_sentence(self):
        self.assertEqual(
            ren._first_sentence("Send email. Also read it."), "Send email."
        )

    def test_keeps_text_without_a_full_stop(self):
        self.assertEqual(ren._first_sentence("Send email"), "Send email")

    def test_does_not_split_inside_a_word(self):
        self.assertEqual(
            ren._first_sentence("Use v1.2 of the API. Then more."),
            "Use v1.2 of the API.",
        )

    def test_does_not_stop_at_an_abbreviation_or_initial(self):
        self.assertEqual(
            ren._first_sentence("Search the U.S. register, e.g. rules. Then more."),
            "Search the U.S. register, e.g. rules.",
        )
        self.assertEqual(
            ren._first_sentence("A dataset built by Greta R. Smith. More."),
            "A dataset built by Greta R. Smith.",
        )

    def test_a_question_or_exclamation_ends_a_sentence(self):
        self.assertEqual(ren._first_sentence("Ready? Go."), "Ready?")


class BuiltInTests(unittest.TestCase):
    def test_lodols_own_steps_are_built_in(self):
        self.assertTrue(ren.is_built_in({"id": "skipflow_review"}))
        self.assertFalse(ren.is_built_in({"id": "slack"}))

    def test_paths(self):
        self.assertEqual(ren.provider_path({"id": "google_sheets"}), "google-sheets")
        self.assertEqual(ren.provider_path({"id": "skipflow_review"}), "built-in/review")
        self.assertEqual(
            ren.provider_url({"id": "skipflow_datetime"}),
            "/docs/integrations/built-in/datetime",
        )

    def test_section_markers_are_left_out_and_the_rest_sorted_by_name(self):
        provider = {
            "id": "skipflow_conditions",
            "actions": {
                "else": {"display_name": "Otherwise", "handler": "_control_flow", "parameters": []},
                "endif": {"display_name": "End if", "handler": "_control_flow", "parameters": []},
                "if": {"display_name": "If", "handler": "_control_flow", "parameters": [{"name": "condition"}]},
            },
        }
        self.assertEqual([n for n, _ in ren.visible_actions(provider)], ["if", "else"])


class GenerateActionSectionTests(unittest.TestCase):
    def _action(self, **overrides):
        base = {
            "display_name": "Send Message",
            "description": "Sends a chat message.",
            "path": "/actions/library/slack/send-message",
            "method": "POST",
            "parameters": [
                {
                    "name": "channel",
                    "display_name": "Channel",
                    "type": "ParameterType.STRING",
                    "required": True,
                    "description": "Target channel id.",
                },
                {
                    "name": "thread",
                    "type": "ParameterType.STRING",
                    "required": False,
                    "description": "Optional thread id.",
                },
            ],
            "mock_response": {"status": "success", "ts": "123"},
        }
        base.update(overrides)
        return base

    def test_includes_header_and_description(self):
        out = ren.generate_action_section("send_message", self._action())
        self.assertTrue(out.startswith("## Send Message\n"))
        self.assertIn("Sends a chat message.", out)

    def test_does_not_include_endpoint_or_curl(self):
        out = ren.generate_action_section("send_message", self._action())
        self.assertNotIn("/actions/library/slack/send-message", out)
        self.assertNotIn("curl", out)

    def test_lists_inputs_by_the_label_the_editor_shows(self):
        out = ren.generate_action_section("send_message", self._action())
        self.assertIn(
            '<Field name="Channel" id="channel" type="text" required '
            'description="Target channel id." />',
            out,
        )

    def test_an_input_without_a_label_is_named_by_its_key(self):
        out = ren.generate_action_section("send_message", self._action())
        self.assertIn(
            '<Field name="thread" id="thread" type="text" description="Optional thread id." />',
            out,
        )

    def test_uses_mock_response_when_present(self):
        out = ren.generate_action_section("send_message", self._action())
        self.assertIn('"status": "success"', out)
        self.assertIn('"ts": "123"', out)

    def test_falls_back_to_returns_schema_when_no_mock(self):
        action = self._action(
            mock_response=None,
            returns={"type": "object", "properties": {"id": {"type": "string"}}},
        )
        out = ren.generate_action_section("send_message", action)
        self.assertIn('"id": "example_value"', out)

    def test_an_action_with_no_inputs_says_so(self):
        out = ren.generate_action_section("send_message", self._action(parameters=[]))
        self.assertIn('<Fields title="Inputs" />', out)

    def test_falls_back_to_action_name_for_display(self):
        action = self._action()
        del action["display_name"]
        out = ren.generate_action_section("my_action_name", action)
        self.assertIn("## My Action Name", out)

    def test_escapes_jsx_characters_in_description(self):
        out = ren.generate_action_section(
            "x",
            self._action(description="payload like {key: <value>}"),
        )
        self.assertNotIn("{key:", out)
        self.assertIn("&#123;key:", out)
        self.assertIn("&lt;value>&#125;", out)

    def test_parameter_descriptions_keep_markup_characters_as_written(self):
        action = self._action()
        action["parameters"][0]["description"] = "Mention someone with ![](@U123) or {name}."
        out = ren.generate_action_section("send_message", action)
        self.assertIn('description="Mention someone with ![](@U123) or {name}."', out)

    def test_an_inputs_choices_and_default_follow_its_description(self):
        action = self._action()
        action["parameters"][1].update(
            options=[
                {"value": "main", "label": "Main thread"},
                {"value": "side", "label": "Side thread"},
            ],
            default="main",
        )
        out = ren.generate_action_section("send_message", action)
        self.assertIn(
            'description="Optional thread id." '
            'facts="One of: `main` (Main thread), `side` (Side thread). Default: `main`."',
            out,
        )

    def test_an_input_without_choices_range_or_default_has_no_facts(self):
        out = ren.generate_action_section("send_message", self._action())
        self.assertNotIn("facts=", out)


class ParameterFactsTests(unittest.TestCase):
    def _options(self, *values):
        return [{"value": v, "label": f"Label {v}"} for v in values]

    def test_choices_show_labels_that_say_more_than_the_value(self):
        facts = ren._parameter_facts(
            {
                "options": [
                    {"value": "all", "label": "Films and TV"},
                    {"value": "movie", "label": "Movie"},
                ]
            }
        )
        self.assertEqual(facts, "One of: `all` (Films and TV), `movie`.")

    def test_multi_select_and_array_parameters_take_one_or_more(self):
        options = self._options("a")
        self.assertTrue(
            ren._parameter_facts({"options": options, "multi_select": True})
            .startswith("One or more of: ")
        )
        self.assertTrue(
            ren._parameter_facts({"options": options, "type": "ParameterType.ARRAY"})
            .startswith("One or more of: ")
        )

    def test_a_long_choice_list_is_cut_after_ten(self):
        facts = ren._parameter_facts({"options": self._options(*range(13))})
        self.assertIn("`9` (Label 9), and 3 more.", facts)
        self.assertNotIn("`10`", facts)

    def test_a_choice_list_of_twelve_is_listed_in_full(self):
        facts = ren._parameter_facts({"options": self._options(*range(12))})
        self.assertIn("`11` (Label 11).", facts)
        self.assertNotIn("more", facts)

    def test_range(self):
        self.assertEqual(
            ren._parameter_facts({"minimum": 1, "maximum": 500}), "From 1 to 500."
        )
        self.assertEqual(ren._parameter_facts({"minimum": 0}), "At least 0.")
        self.assertEqual(ren._parameter_facts({"maximum": 0.5}), "At most 0.5.")

    def test_default_is_written_as_the_caller_would_send_it(self):
        self.assertEqual(ren._parameter_facts({"default": "all"}), "Default: `all`.")
        self.assertEqual(ren._parameter_facts({"default": False}), "Default: `false`.")
        self.assertEqual(ren._parameter_facts({"default": 0}), "Default: `0`.")
        self.assertEqual(
            ren._parameter_facts({"default": ["a", "b"]}), 'Default: `["a", "b"]`.'
        )

    def test_empty_defaults_say_nothing(self):
        for default in (None, "", [], {}):
            self.assertEqual(ren._parameter_facts({"default": default}), "")

    def test_choices_then_range_then_default(self):
        facts = ren._parameter_facts(
            {
                "options": [{"value": "10", "label": "10"}],
                "minimum": 1,
                "maximum": 10,
                "default": 10,
            }
        )
        self.assertEqual(facts, "One of: `10`. From 1 to 10. Default: `10`.")

    def test_values_are_code_and_labels_plain_text(self):
        facts = ren._parameter_facts(
            {
                "options": [
                    {"value": "<=", "label": "at most"},
                    {"value": "a|b", "label": "pipe"},
                    {"value": "x`y", "label": "tick"},
                    {"value": "", "label": "Any {kind}"},
                ]
            }
        )
        # The facts reach the page as a JSX attribute, shown as written.
        self.assertEqual(
            facts,
            'One of: `<=` (at most), `a|b` (pipe), ``x`y`` (tick), `""` (Any {kind}).',
        )

    def test_nothing_declared_says_nothing(self):
        self.assertEqual(ren._parameter_facts({"name": "q"}), "")


class CodeSpanTests(unittest.TestCase):
    def test_plain_text(self):
        self.assertEqual(ren._code_span("all"), "`all`")

    def test_backticks_get_a_longer_fence(self):
        self.assertEqual(ren._code_span("a``b"), "```a``b```")
        self.assertEqual(ren._code_span("`a"), "`` `a ``")

    def test_newlines_are_flattened(self):
        self.assertEqual(ren._code_span("a|b\nc"), "`a|b c`")


def _provider(pid="slack", n=1, **overrides):
    actions = {
        f"act_{i}": {
            "display_name": f"Act {chr(ord('A') + i)}",
            "description": f"Does thing {i}. More detail.",
            "parameters": [],
        }
        for i in range(n)
    }
    base = {"id": pid, "display_name": "Slack", "description": "Talk to your team.", "actions": actions}
    base.update(overrides)
    return base


class GenerateProviderMdxTests(unittest.TestCase):
    def test_frontmatter_describes_the_app(self):
        out = ren.generate_provider_mdx(_provider(n=2))
        self.assertTrue(out.startswith("---\n"))
        self.assertIn('title: "Slack"\n', out)
        self.assertIn('description: "Talk to your team."\n', out)
        self.assertIn("integration: app\n", out)
        self.assertIn("actions: 2\n", out)
        self.assertTrue(out.endswith("\n"))

    def test_an_app_without_a_description_still_gets_one(self):
        out = ren.generate_provider_mdx(_provider(description=""))
        self.assertIn('description: "What Slack can do in a workflow."', out)

    def test_the_title_is_not_repeated_as_a_heading(self):
        out = ren.generate_provider_mdx(_provider(n=1))
        self.assertNotIn("## Slack", out)

    def test_three_or_more_actions_get_an_overview_linking_to_each(self):
        out = ren.generate_provider_mdx(_provider(n=3))
        self.assertIn("## Actions\n\n| Action | What it does |", out)
        self.assertIn("| [Act A](#act-a) | Does thing 0. |", out)

    def test_fewer_than_three_actions_need_no_overview(self):
        self.assertNotIn("## Actions", ren.generate_provider_mdx(_provider(n=2)))

    def test_anchors_match_headings_even_when_names_repeat(self):
        provider = _provider(
            actions={
                "a": {"display_name": "Send", "parameters": []},
                "b": {"display_name": "Send", "parameters": []},
                "c": {"display_name": "Actions", "parameters": []},
            }
        )
        out = ren.generate_provider_mdx(provider)
        # fumadocs gives the overview "actions", then each heading in order.
        self.assertIn("[Actions](#actions-1)", out)
        self.assertIn("[Send](#send)", out)
        self.assertIn("[Send](#send-1)", out)

    def test_skips_non_dict_action_entries(self):
        provider = _provider(actions={"bogus": "not a dict", "good": {"display_name": "Good", "parameters": []}})
        out = ren.generate_provider_mdx(provider)
        self.assertIn("## Good", out)
        self.assertNotIn("bogus", out)

    def test_built_in_steps_get_their_icon_and_guide(self):
        provider = _provider("skipflow_review", n=1, display_name="Approvals")
        out = ren.generate_provider_mdx(provider)
        self.assertIn("integration: built-in\n", out)
        self.assertIn("icon: UserCheck\n", out)
        self.assertIn("[Ask for approval](/docs/guides/approvals)", out)

    def test_a_built_in_step_the_renderer_has_not_met_gets_a_default_icon(self):
        out = ren.generate_provider_mdx(_provider("skipflow_new_thing", n=1))
        self.assertIn(f"icon: {ren.DEFAULT_BUILT_IN_ICON}\n", out)

    def test_built_in_steps_list_their_steps_as_steps(self):
        out = ren.generate_provider_mdx(_provider("skipflow_text", n=3))
        self.assertIn("## Steps\n\n| Step | What it does |", out)

    def test_section_markers_become_a_note(self):
        provider = {
            "id": "skipflow_loops",
            "display_name": "Repeat",
            "description": "Run steps more than once.",
            "actions": {
                "endforeach": {"display_name": "End repeat", "handler": "_control_flow", "parameters": []},
                "endwhile": {"display_name": "End repeat", "handler": "_control_flow", "parameters": []},
                "foreach": {"display_name": "Repeat for each item", "handler": "_control_flow", "parameters": [{"name": "items"}]},
            },
        }
        out = ren.generate_provider_mdx(provider)
        self.assertIn("Close each section with an **End repeat** step.", out)
        self.assertNotIn("## End repeat", out)
        self.assertIn("actions: 1\n", out)


class GenerateIndexMdxTests(unittest.TestCase):
    def test_the_directory_page(self):
        providers = [_provider("slack"), _provider("gmail"), _provider("skipflow_text")]
        out = ren.generate_index_mdx(providers)
        self.assertIn("title: Integrations\n", out)
        self.assertIn("The 2 apps and the built-in steps a workflow can use", out)
        self.assertIn("<IntegrationDirectory />", out)

    def test_does_not_reference_direct_api_calls(self):
        out = ren.generate_index_mdx([_provider()])
        self.assertNotIn("curl", out)
        self.assertNotIn("/actions/library", out)


class GenerateMetaJsonTests(unittest.TestCase):
    def test_is_the_integrations_tab(self):
        meta = json.loads(ren.generate_meta_json([_provider()]))
        self.assertEqual(meta["title"], "Integrations")
        self.assertTrue(meta["root"])

    def test_built_in_steps_come_first_then_apps_by_name(self):
        providers = [
            {"id": "zzz", "display_name": "Zeta", "actions": {}},
            {"id": "ebay", "display_name": "eBay", "actions": {}},
            {"id": "skipflow_text", "display_name": "Text", "actions": {}},
            {"id": "aaa", "display_name": "Alpha", "actions": {}},
        ]
        meta = json.loads(ren.generate_meta_json(providers))
        self.assertEqual(
            meta["pages"],
            ["index", "---Built-in steps---", "...built-in", "---Apps---", "aaa", "ebay", "zzz"],
        )

    def test_underscores_converted_to_hyphens(self):
        meta = json.loads(ren.generate_meta_json([{"id": "google_sheets", "display_name": "Google Sheets", "actions": {}}]))
        self.assertIn("google-sheets", meta["pages"])

    def test_built_in_meta_orders_steps_by_name(self):
        providers = [
            {"id": "skipflow_text", "display_name": "Text", "actions": {}},
            {"id": "skipflow_review", "display_name": "Approvals", "actions": {}},
        ]
        meta = json.loads(ren.generate_built_in_meta_json(providers))
        self.assertEqual(meta["pages"], ["review", "text"])


class CatalogTests(unittest.TestCase):
    def test_counts_and_entries(self):
        providers = [
            _provider("slack", n=3),
            _provider("gmail", n=2, display_name="Gmail"),
            _provider("skipflow_review", n=1, display_name="Approvals"),
        ]
        catalog = ren.generate_catalog(providers)
        self.assertEqual(catalog["apps"], 2)
        self.assertEqual(catalog["appActions"], 5)
        self.assertEqual([e["name"] for e in catalog["entries"]], ["Approvals", "Gmail", "Slack"])
        approvals = catalog["entries"][0]
        self.assertEqual(approvals["href"], "/docs/integrations/built-in/review")
        self.assertTrue(approvals["builtIn"])
        self.assertEqual(approvals["icon"], "UserCheck")

    def test_entries_carry_a_one_sentence_description(self):
        catalog = ren.generate_catalog([_provider(description="Talk to your team. And more.")])
        self.assertEqual(catalog["entries"][0]["description"], "Talk to your team.")

    def test_popular_apps_missing_from_the_catalog_are_left_out(self):
        catalog = ren.generate_catalog([_provider("slack"), _provider("unknown_app")])
        self.assertEqual(catalog["popular"], ["slack"])


class LoadSpecsTests(unittest.TestCase):
    def test_loads_valid_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "actions.json"
            path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "providers": [
                            {"id": "slack", "display_name": "Slack", "actions": {}}
                        ],
                    }
                )
            )
            providers = ren.load_specs(path)
            self.assertEqual(len(providers), 1)
            self.assertEqual(providers[0]["id"], "slack")

    def test_missing_file_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                ren.load_specs(Path(tmp) / "nope.json"), []
            )

    def test_malformed_payload_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "actions.json"
            path.write_text(json.dumps(["not a dict"]))
            self.assertEqual(ren.load_specs(path), [])

    def test_missing_providers_key_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "actions.json"
            path.write_text(json.dumps({"schema_version": 1}))
            self.assertEqual(ren.load_specs(path), [])

    def test_filters_non_dict_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "actions.json"
            path.write_text(
                json.dumps(
                    {
                        "providers": [
                            "garbage",
                            {"id": "slack", "display_name": "Slack", "actions": {}},
                        ]
                    }
                )
            )
            providers = ren.load_specs(path)
            self.assertEqual(len(providers), 1)
            self.assertEqual(providers[0]["id"], "slack")

    def test_loads_one_file_per_provider_from_a_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            for pid in ("zendesk", "airtable"):
                (directory / f"{pid}.json").write_text(
                    json.dumps({"id": pid, "display_name": pid, "actions": {}})
                )
            providers = ren.load_specs(directory)
            self.assertEqual([p["id"] for p in providers], ["airtable", "zendesk"])

    def test_directory_ignores_files_that_are_not_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / "slack.json").write_text(
                json.dumps({"id": "slack", "display_name": "Slack", "actions": {}})
            )
            (directory / "README.md").write_text("Published by lodolai/lodol.")
            self.assertEqual(
                [p["id"] for p in ren.load_specs(directory)], ["slack"]
            )

    def test_directory_skips_a_file_that_is_not_a_provider_object(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / "broken.json").write_text(json.dumps(["not a dict"]))
            (directory / "slack.json").write_text(
                json.dumps({"id": "slack", "display_name": "Slack", "actions": {}})
            )
            self.assertEqual(
                [p["id"] for p in ren.load_specs(directory)], ["slack"]
            )

    def test_empty_directory_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(ren.load_specs(Path(tmp)), [])

    def test_default_input_is_the_per_provider_directory(self):
        self.assertEqual(ren.DEFAULT_INPUT, ren.DOCS_ROOT / "data" / "actions")


@unittest.skipUnless(
    ren.DEFAULT_INPUT.is_dir(), "no published specs in this checkout"
)
class PublishedSpecsTests(unittest.TestCase):
    """The specs committed in ``data/actions/`` keep the published layout."""

    def test_each_file_is_named_after_its_provider(self):
        paths = sorted(ren.DEFAULT_INPUT.glob("*.json"))
        self.assertTrue(paths)
        for path in paths:
            provider = json.loads(path.read_text(encoding="utf-8"))
            self.assertIsInstance(provider, dict, path.name)
            self.assertEqual(provider.get("id"), path.stem, path.name)


class RenderIntegrationTests(unittest.TestCase):
    """End-to-end test through ``render``."""

    def test_writes_the_directory_catalog_meta_and_pages(self):
        providers = [
            _provider("slack", n=1),
            _provider("skipflow_review", n=1, display_name="Approvals"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "out"
            written = ren.render(providers, output_dir)

            for name in ("meta.json", "index.mdx", "catalog.json", "slack.mdx",
                         "built-in/meta.json", "built-in/review.mdx"):
                self.assertTrue((output_dir / name).exists(), name)
            self.assertEqual(written, 6)

            catalog = json.loads((output_dir / "catalog.json").read_text())
            self.assertEqual(catalog["apps"], 1)
            self.assertIn("## Act A", (output_dir / "slack.mdx").read_text())

    def test_writes_provider_files_as_utf8(self):
        providers = [
            {
                "id": "limits",
                "display_name": "Limits",
                "description": "Only values ≤ 10 are accepted.",
                "actions": {},
            }
        ]
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "out"
            ren.render(providers, output_dir)

            provider_mdx = (output_dir / "limits.mdx").read_text(encoding="utf-8")
            self.assertIn("Only values ≤ 10 are accepted.", provider_mdx)

    def test_recreates_the_output_directory_from_scratch(self):
        """A stale page or folder from a previous run is removed."""
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "out"
            (output_dir / "built-in").mkdir(parents=True)
            (output_dir / "stale.mdx").write_text("old")
            (output_dir / "built-in" / "gone.mdx").write_text("old")

            ren.render([], output_dir)

            self.assertFalse((output_dir / "stale.mdx").exists())
            self.assertFalse((output_dir / "built-in").exists())
            # The directory, catalog and meta are always written, even with
            # zero providers.
            self.assertTrue((output_dir / "meta.json").exists())
            self.assertTrue((output_dir / "index.mdx").exists())
            self.assertTrue((output_dir / "catalog.json").exists())

    def test_the_default_output_is_the_integrations_tab(self):
        self.assertEqual(
            ren.DEFAULT_OUTPUT_DIR, ren.DOCS_ROOT / "content" / "docs" / "integrations"
        )


class MainIntegrationTests(unittest.TestCase):
    def test_main_with_explicit_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_path = tmp_path / "actions.json"
            input_path.write_text(json.dumps({"providers": [_provider("fake", n=1)]}))
            output_dir = tmp_path / "out"
            rc = ren.main(
                ["--input", str(input_path), "--output-dir", str(output_dir)]
            )
            self.assertEqual(rc, 0)
            self.assertTrue((output_dir / "fake.mdx").exists())

    def test_main_reads_a_directory_of_provider_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_dir = tmp_path / "actions"
            input_dir.mkdir()
            (input_dir / "fake.json").write_text(json.dumps(_provider("fake", n=1)))
            output_dir = tmp_path / "out"
            rc = ren.main(
                ["--input", str(input_dir), "--output-dir", str(output_dir)]
            )
            self.assertEqual(rc, 0)
            self.assertIn("## Act A", (output_dir / "fake.mdx").read_text())


if __name__ == "__main__":
    unittest.main()
