"""Unit tests for ``scripts/render-actions-docs.py``.

The renderer consumes ``data/actions/`` (one JSON file per provider,
published by the ``lodolai/lodol`` server repo) and emits one MDX page
per provider plus an index and a ``meta.json``. These tests cover:

    - the pure helpers (param-type mapping, mock synthesis, MDX
      escaping, YAML quoting, slug generation)
    - the higher-level MDX/index/meta generators
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


class ResponseSectionTests(unittest.TestCase):
    """The **Response** part of an action's section."""

    def _section(self, **action):
        return ren.generate_action_section(
            "act", {"display_name": "Act", "description": "", **action}
        )

    def test_starts_with_the_outputs_description(self):
        out = self._section(
            returns={"type": "number", "description": "The sum, {rounded}."},
            mock_response=12,
        )
        self.assertIn(
            "**Response**\n\nThe sum, &#123;rounded&#125;.\n\n```json\n12\n```", out
        )

    def test_shows_the_schemas_example_when_there_is_no_mock(self):
        out = self._section(returns={"type": "number", "examples": [42.5]})
        self.assertIn("```json\n42.5\n```", out)

    def test_a_mock_wins_over_the_schemas_example(self):
        out = self._section(
            returns={"type": "number", "examples": [42.5]}, mock_response=3
        )
        self.assertIn("```json\n3\n```", out)
        self.assertNotIn("42.5", out)

    def test_no_output_says_so_instead_of_a_made_up_payload(self):
        out = self._section(returns={"type": "null"})
        self.assertIn("**Response**\n\nThis action has no output.", out)
        self.assertNotIn("```json", out)
        self.assertNotIn('"status"', out)

    def test_no_output_with_a_description_shows_only_the_description(self):
        out = self._section(
            returns={"type": "null", "description": "Nothing; the run pauses here."}
        )
        self.assertIn("**Response**\n\nNothing; the run pauses here.", out)
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
        self.assertIn("### Send Message", out)
        self.assertIn("Sends a chat message.", out)

    def test_does_not_include_endpoint_or_curl(self):
        out = ren.generate_action_section("send_message", self._action())
        self.assertNotIn("POST /actions/library/slack/send-message", out)
        self.assertNotIn("curl", out)

    def test_includes_parameter_table(self):
        out = ren.generate_action_section("send_message", self._action())
        self.assertIn("**Parameters**", out)
        self.assertIn("| `channel` | string | Yes |", out)
        self.assertIn("| `thread` | string | No |", out)

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

    def test_omits_parameters_table_when_none(self):
        action = self._action(parameters=[])
        out = ren.generate_action_section("send_message", action)
        self.assertNotIn("**Parameters**", out)

    def test_falls_back_to_action_name_for_display(self):
        action = self._action()
        del action["display_name"]
        out = ren.generate_action_section("my_action_name", action)
        self.assertIn("### My Action Name", out)

    def test_renders_without_method_field(self):
        action = self._action()
        del action["method"]
        out = ren.generate_action_section("send_message", action)
        self.assertIn("### Send Message", out)

    def test_escapes_jsx_characters_in_description(self):
        out = ren.generate_action_section(
            "x",
            self._action(description="payload like {key: <value>}"),
        )
        self.assertNotIn("{key:", out)
        self.assertIn("&#123;key:", out)
        self.assertIn("&lt;value>&#125;", out)

    def test_escapes_image_syntax_in_parameter_descriptions(self):
        action = self._action()
        action["parameters"][0]["description"] = "Mention someone with ![](@U123)."
        out = ren.generate_action_section("send_message", action)
        self.assertIn("Mention someone with !\\[](@U123).", out)
        self.assertNotIn("![](", out)


class GenerateProviderMdxTests(unittest.TestCase):
    def test_includes_frontmatter_and_actions(self):
        provider = {
            "id": "slack",
            "display_name": "Slack",
            "description": "Slack integration.",
            "actions": {
                "send": {
                    "display_name": "Send",
                    "description": "Send a message.",
                    "path": "/actions/library/slack/send",
                    "method": "POST",
                    "parameters": [],
                }
            },
        }
        out = ren.generate_provider_mdx(provider)
        self.assertTrue(out.startswith("---\n"))
        self.assertIn('title: "Slack"', out)
        self.assertIn('description: "API actions for the Slack integration."', out)
        self.assertIn("## Slack", out)
        self.assertIn("### Send", out)
        self.assertTrue(out.endswith("\n"))

    def test_skips_non_dict_action_entries(self):
        provider = {
            "id": "slack",
            "display_name": "Slack",
            "description": "",
            "actions": {
                "bogus": "not a dict",
                "good": {
                    "display_name": "Good",
                    "description": "",
                    "path": "/p",
                    "method": "POST",
                    "parameters": [],
                },
            },
        }
        out = ren.generate_provider_mdx(provider)
        self.assertIn("### Good", out)
        self.assertNotIn("bogus", out)


class GenerateIndexMdxTests(unittest.TestCase):
    def test_pluralisation_and_card_links(self):
        providers = [
            {
                "id": "slack",
                "display_name": "Slack",
                "actions": {"send": {}, "list": {}},
            },
            {
                "id": "google_sheets",
                "display_name": "Google Sheets",
                "actions": {"append": {}},
            },
        ]
        out = ren.generate_index_mdx(providers)
        self.assertIn('description="2 actions available"', out)
        self.assertIn('description="1 action available"', out)
        self.assertIn("/docs/api-reference/actions/google-sheets", out)
        self.assertIn("/docs/api-reference/actions/slack", out)

    def test_alphabetical_ordering(self):
        providers = [
            {"id": "zzz", "display_name": "Zeta", "actions": {"a": {}}},
            {"id": "aaa", "display_name": "Alpha", "actions": {"a": {}}},
        ]
        out = ren.generate_index_mdx(providers)
        self.assertLess(out.index('title="Alpha"'), out.index('title="Zeta"'))

    def test_skips_non_dict_actions_in_count(self):
        providers = [
            {
                "id": "x",
                "display_name": "X",
                "actions": {"good": {}, "bogus": "not a dict"},
            }
        ]
        out = ren.generate_index_mdx(providers)
        self.assertIn('description="1 action available"', out)

    def test_does_not_reference_direct_api_calls(self):
        providers = [{"id": "slack", "display_name": "Slack", "actions": {}}]
        out = ren.generate_index_mdx(providers)
        self.assertNotIn("call actions directly", out)
        self.assertNotIn("curl", out)
        self.assertNotIn("Endpoint Format", out)
        self.assertNotIn("Request Format", out)


class GenerateMetaJsonTests(unittest.TestCase):
    def test_pages_listed_alphabetically_by_display_name(self):
        providers = [
            {"id": "zzz", "display_name": "Zeta", "actions": {}},
            {"id": "aaa", "display_name": "Alpha", "actions": {}},
        ]
        meta = json.loads(ren.generate_meta_json(providers))
        self.assertEqual(meta["title"], "Actions")
        self.assertEqual(meta["pages"], ["index", "aaa", "zzz"])

    def test_underscores_converted_to_hyphens(self):
        providers = [
            {"id": "google_sheets", "display_name": "Google Sheets", "actions": {}},
        ]
        meta = json.loads(ren.generate_meta_json(providers))
        self.assertIn("google-sheets", meta["pages"])


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

    def test_writes_index_meta_and_provider_files(self):
        providers = [
            {
                "id": "slack",
                "display_name": "Slack",
                "description": "Slack integration.",
                "actions": {
                    "send": {
                        "display_name": "Send",
                        "description": "Sends a message.",
                        "path": "/actions/library/slack/send",
                        "method": "POST",
                        "parameters": [],
                        "mock_response": {"status": "success"},
                    }
                },
            }
        ]
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "out"
            ren.render(providers, output_dir)

            self.assertTrue((output_dir / "meta.json").exists())
            self.assertTrue((output_dir / "index.mdx").exists())
            self.assertTrue((output_dir / "slack.mdx").exists())

            meta = json.loads((output_dir / "meta.json").read_text())
            self.assertEqual(meta["pages"], ["index", "slack"])

            provider_mdx = (output_dir / "slack.mdx").read_text()
            self.assertIn("### Send", provider_mdx)
            self.assertIn("Sends a message.", provider_mdx)

    def test_writes_provider_files_as_utf8(self):
        providers = [
            {
                "id": "limits",
                "display_name": "Limits",
                "description": "Only values \u2264 10 are accepted.",
                "actions": {},
            }
        ]
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "out"
            ren.render(providers, output_dir)

            provider_mdx = (output_dir / "limits.mdx").read_text(encoding="utf-8")
            self.assertIn("Only values \u2264 10 are accepted.", provider_mdx)

    def test_recreates_output_dir_files_from_scratch(self):
        """A stale file from a previous run is removed."""
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "out"
            output_dir.mkdir()
            (output_dir / "stale.mdx").write_text("old")

            ren.render([], output_dir)

            self.assertFalse((output_dir / "stale.mdx").exists())
            # Index + meta are always written, even with zero providers.
            self.assertTrue((output_dir / "meta.json").exists())
            self.assertTrue((output_dir / "index.mdx").exists())


class MainIntegrationTests(unittest.TestCase):
    def test_main_with_explicit_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_path = tmp_path / "actions.json"
            input_path.write_text(
                json.dumps(
                    {
                        "providers": [
                            {
                                "id": "fake",
                                "display_name": "Fake",
                                "description": "A fake provider.",
                                "actions": {
                                    "ping": {
                                        "display_name": "Ping",
                                        "description": "Pings.",
                                        "path": "/actions/library/fake/ping",
                                        "method": "POST",
                                        "parameters": [],
                                    }
                                },
                            }
                        ]
                    }
                )
            )
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
            (input_dir / "fake.json").write_text(
                json.dumps(
                    {
                        "id": "fake",
                        "display_name": "Fake",
                        "description": "A fake provider.",
                        "actions": {
                            "ping": {
                                "display_name": "Ping",
                                "description": "Pings.",
                                "parameters": [],
                            }
                        },
                    }
                )
            )
            output_dir = tmp_path / "out"
            rc = ren.main(
                ["--input", str(input_dir), "--output-dir", str(output_dir)]
            )
            self.assertEqual(rc, 0)
            self.assertIn("### Ping", (output_dir / "fake.mdx").read_text())


if __name__ == "__main__":
    unittest.main()
