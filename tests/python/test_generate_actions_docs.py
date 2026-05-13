"""Unit tests for ``scripts/generate-actions-docs.py``.

The generator is a stand-alone script (no package), so we load it via
``importlib`` from the file path. Tests cover the pure helpers
(extraction, escaping, schema-to-example synthesis, slug generation) and
the higher-level MDX/index/meta generators. Provider parsing is
exercised end-to-end against a synthesised ``provider.py`` on disk so we
don't depend on the live integrations library being checked out.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import sys
import textwrap
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2] / "scripts" / "generate-actions-docs.py"
)


def _load_generator():
    """Load the generator script as a module under a synthetic name.

    The file uses a hyphen in its name so it can't be imported directly.
    """
    spec = importlib.util.spec_from_file_location(
        "generate_actions_docs", SCRIPT_PATH
    )
    assert spec and spec.loader, "could not load generator script"
    module = importlib.util.module_from_spec(spec)
    sys.modules["generate_actions_docs"] = module
    spec.loader.exec_module(module)
    return module


gen = _load_generator()


def _parse_expr(src: str) -> ast.expr:
    """Parse a Python expression and return the underlying ast node."""
    return ast.parse(src, mode="eval").body


class ExtractTests(unittest.TestCase):
    """Tests for the recursive AST value extractor ``gen._extract``."""

    def test_constants(self):
        self.assertEqual(gen._extract(_parse_expr('"hello"')), "hello")
        self.assertEqual(gen._extract(_parse_expr("42")), 42)
        self.assertAlmostEqual(gen._extract(_parse_expr("3.14")), 3.14)

    def test_named_singletons(self):
        self.assertIs(gen._extract(_parse_expr("True")), True)
        self.assertIs(gen._extract(_parse_expr("False")), False)
        self.assertIsNone(gen._extract(_parse_expr("None")))

    def test_name_reference(self):
        # Bare identifiers are preserved as strings so callers can keep
        # track of enum references like ``ParameterType``.
        self.assertEqual(gen._extract(_parse_expr("ParameterType")), "ParameterType")

    def test_attribute_on_name(self):
        self.assertEqual(
            gen._extract(_parse_expr("ParameterType.STRING")),
            "ParameterType.STRING",
        )

    def test_attribute_on_attribute_returns_leaf(self):
        # ``a.b.c`` → only the leaf attribute is preserved; this matches
        # the simplified behaviour the generator depends on.
        self.assertEqual(gen._extract(_parse_expr("a.b.c")), "c")

    def test_dict_list_tuple_set(self):
        self.assertEqual(gen._extract(_parse_expr("{'a': 1, 'b': 2}")), {"a": 1, "b": 2})
        self.assertEqual(gen._extract(_parse_expr("[1, 2, 3]")), [1, 2, 3])
        self.assertEqual(gen._extract(_parse_expr("(1, 2)")), (1, 2))
        self.assertEqual(gen._extract(_parse_expr("{1, 2, 3}")), {1, 2, 3})

    def test_unary_minus(self):
        self.assertEqual(gen._extract(_parse_expr("-7")), -7)
        self.assertAlmostEqual(gen._extract(_parse_expr("-2.5")), -2.5)

    def test_call_with_kwargs_returns_dict(self):
        node = _parse_expr("ActionSpec(name='hello', required=True)")
        self.assertEqual(
            gen._extract(node), {"name": "hello", "required": True}
        )

    def test_call_captures_positional_args(self):
        node = _parse_expr("Foo('a', 'b', x=1)")
        out = gen._extract(node)
        self.assertEqual(out["x"], 1)
        self.assertEqual(out["__args__"], ["a", "b"])

    def test_joined_string(self):
        # f"hello {name}" → "hello {...}" (placeholders are opaque)
        node = _parse_expr("f'hello {name}'")
        self.assertEqual(gen._extract(node), "hello {...}")

    def test_none_input(self):
        self.assertIsNone(gen._extract(None))


class ParamTypeTests(unittest.TestCase):
    def test_known_enum_values(self):
        self.assertEqual(gen._param_type("ParameterType.STRING"), "string")
        self.assertEqual(gen._param_type("ParameterType.NUMBER"), "number")
        self.assertEqual(gen._param_type("ParameterType.BOOLEAN"), "boolean")
        self.assertEqual(gen._param_type("ParameterType.OBJECT"), "object")
        self.assertEqual(gen._param_type("ParameterType.ARRAY"), "array")

    def test_unknown_falls_back_to_lowercase_leaf(self):
        self.assertEqual(gen._param_type("ParameterType.WEIRD"), "weird")

    def test_non_string_defaults_to_string(self):
        self.assertEqual(gen._param_type(None), "string")
        self.assertEqual(gen._param_type(123), "string")


class JsonBodyExampleTests(unittest.TestCase):
    def test_only_required_params_included(self):
        params = [
            {"name": "a", "type": "ParameterType.STRING", "required": True},
            {"name": "b", "type": "ParameterType.STRING", "required": False},
        ]
        self.assertEqual(gen._json_body_example(params), {"a": "your_a"})

    def test_synthesises_value_per_type(self):
        params = [
            {"name": "s", "type": "ParameterType.STRING", "required": True},
            {"name": "n", "type": "ParameterType.NUMBER", "required": True},
            {"name": "b", "type": "ParameterType.BOOLEAN", "required": True},
            {"name": "o", "type": "ParameterType.OBJECT", "required": True},
            {"name": "a", "type": "ParameterType.ARRAY", "required": True},
        ]
        self.assertEqual(
            gen._json_body_example(params),
            {"s": "your_s", "n": 10, "b": True, "o": {}, "a": []},
        )

    def test_ignores_non_dict_entries(self):
        params = [
            "not a dict",
            {"name": "x", "type": "ParameterType.STRING", "required": True},
        ]
        self.assertEqual(gen._json_body_example(params), {"x": "your_x"})

    def test_empty_input(self):
        self.assertEqual(gen._json_body_example([]), {})


class SchemaExampleTests(unittest.TestCase):
    def test_primitives(self):
        self.assertEqual(gen._schema_example({"type": "string"}), "example_value")
        self.assertEqual(gen._schema_example({"type": "number"}), 1)
        self.assertEqual(gen._schema_example({"type": "integer"}), 1)
        self.assertEqual(gen._schema_example({"type": "boolean"}), True)
        self.assertEqual(gen._schema_example({"type": "array"}), [])

    def test_object_with_properties(self):
        schema = {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "count": {"type": "number"},
            },
        }
        self.assertEqual(
            gen._schema_example(schema), {"id": "example_value", "count": 1}
        )

    def test_object_without_properties(self):
        self.assertEqual(gen._schema_example({"type": "object"}), {})

    def test_default_type_string(self):
        # Missing ``type`` is treated as ``string``.
        self.assertEqual(gen._schema_example({}), "example_value")

    def test_unknown_type(self):
        self.assertIsNone(gen._schema_example({"type": "weird"}))


class MockFromReturnsTests(unittest.TestCase):
    def test_non_dict_returns_default_success(self):
        self.assertEqual(gen._mock_from_returns(None), {"status": "success"})
        self.assertEqual(gen._mock_from_returns("oops"), {"status": "success"})

    def test_null_or_missing_type(self):
        self.assertEqual(gen._mock_from_returns({}), {"status": "success"})
        self.assertEqual(
            gen._mock_from_returns({"type": "null"}), {"status": "success"}
        )

    def test_primitive_types(self):
        self.assertEqual(gen._mock_from_returns({"type": "string"}), "example_value")
        self.assertEqual(gen._mock_from_returns({"type": "number"}), 1)
        self.assertEqual(gen._mock_from_returns({"type": "boolean"}), True)

    def test_array_of_strings(self):
        result = gen._mock_from_returns(
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
        self.assertEqual(gen._mock_from_returns(schema), [{"id": "example_value"}])

    def test_array_with_no_items(self):
        self.assertEqual(gen._mock_from_returns({"type": "array"}), [])

    def test_object_with_properties(self):
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "score": {"type": "number"},
            },
        }
        self.assertEqual(
            gen._mock_from_returns(schema),
            {"name": "example_value", "score": 1},
        )

    def test_object_without_properties(self):
        self.assertEqual(
            gen._mock_from_returns({"type": "object"}),
            {"status": "success"},
        )


class MockToJsonTests(unittest.TestCase):
    def test_none_returns_default_success_payload(self):
        out = gen._mock_to_json(None)
        self.assertIn('"status"', out)
        self.assertIn('"success"', out)

    def test_pretty_prints_with_two_spaces(self):
        out = gen._mock_to_json({"a": 1, "b": [2]})
        self.assertIn('\n  "a": 1', out)

    def test_handles_tuples_and_sets(self):
        out = gen._mock_to_json({"items": (1, 2, 3), "tags": {"b", "a"}})
        parsed = json.loads(out)
        self.assertEqual(parsed["items"], [1, 2, 3])
        # Sets are sorted on serialisation.
        self.assertEqual(parsed["tags"], ["a", "b"])

    def test_unserialisable_falls_back_to_string(self):
        class Weird:
            def __repr__(self):
                return "weird-thing"

        out = gen._mock_to_json(Weird())
        # Should be valid JSON containing a string representation.
        parsed = json.loads(out)
        self.assertIsInstance(parsed, str)
        self.assertIn("weird", parsed)


class EscapeMdxTests(unittest.TestCase):
    def test_escapes_jsx_delimiters(self):
        self.assertEqual(gen._escape_mdx("{a}"), "&#123;a&#125;")

    def test_escapes_less_than(self):
        self.assertEqual(gen._escape_mdx("a < b"), "a &lt; b")

    def test_none_returns_empty(self):
        self.assertEqual(gen._escape_mdx(None), "")

    def test_non_string_is_stringified(self):
        self.assertEqual(gen._escape_mdx(123), "123")

    def test_cell_escapes_pipes_and_newlines(self):
        self.assertEqual(
            gen._escape_mdx_cell("a|b\nc"),
            "a\\|b c",
        )

    def test_cell_combines_mdx_and_table_escapes(self):
        self.assertEqual(
            gen._escape_mdx_cell("{x}|y<z"),
            "&#123;x&#125;\\|y&lt;z",
        )


class YamlQuoteTests(unittest.TestCase):
    def test_basic_quote(self):
        self.assertEqual(gen._yaml_quote("hello"), '"hello"')

    def test_escapes_backslash_and_quote(self):
        self.assertEqual(gen._yaml_quote('a\\b"c'), '"a\\\\b\\"c"')

    def test_none_yields_empty_quoted_string(self):
        self.assertEqual(gen._yaml_quote(None), '""')


class ProviderIdToSlugTests(unittest.TestCase):
    def test_underscores_become_hyphens(self):
        self.assertEqual(gen.provider_id_to_slug("google_sheets"), "google-sheets")
        self.assertEqual(gen.provider_id_to_slug("notion"), "notion")
        self.assertEqual(
            gen.provider_id_to_slug("a_b_c_d"), "a-b-c-d"
        )


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

    def test_includes_header_and_endpoint(self):
        out = gen.generate_action_section("send_message", self._action())
        self.assertIn("### Send Message", out)
        self.assertIn("POST /actions/library/slack/send-message", out)
        self.assertIn("Sends a chat message.", out)

    def test_includes_parameter_table(self):
        out = gen.generate_action_section("send_message", self._action())
        self.assertIn("**Parameters**", out)
        self.assertIn("| `channel` | string | Yes |", out)
        self.assertIn("| `thread` | string | No |", out)

    def test_curl_example_uses_only_required_params(self):
        out = gen.generate_action_section("send_message", self._action())
        self.assertIn("curl -X POST https://api.skipflow.com/v1/actions/library/slack/send-message", out)
        self.assertIn('"channel": "your_channel"', out)
        self.assertNotIn('"thread"', out)

    def test_uses_mock_response_when_present(self):
        out = gen.generate_action_section("send_message", self._action())
        self.assertIn('"status": "success"', out)
        self.assertIn('"ts": "123"', out)

    def test_falls_back_to_returns_schema_when_no_mock(self):
        action = self._action(
            mock_response=None,
            returns={"type": "object", "properties": {"id": {"type": "string"}}},
        )
        out = gen.generate_action_section("send_message", action)
        self.assertIn('"id": "example_value"', out)

    def test_omits_parameters_table_when_none(self):
        action = self._action(parameters=())
        out = gen.generate_action_section("send_message", action)
        self.assertNotIn("**Parameters**", out)

    def test_falls_back_to_action_name_for_display(self):
        action = self._action()
        del action["display_name"]
        out = gen.generate_action_section("my_action_name", action)
        self.assertIn("### My Action Name", out)

    def test_uses_default_method_post_when_missing(self):
        action = self._action()
        del action["method"]
        out = gen.generate_action_section("send_message", action)
        self.assertIn("POST ", out)

    def test_escapes_jsx_characters_in_description(self):
        out = gen.generate_action_section(
            "x",
            self._action(description="payload like {key: <value>}"),
        )
        self.assertNotIn("{key:", out)
        self.assertIn("&#123;key:", out)
        # `<` is escaped, but `>` is not — MDX only treats `<` as a JSX
        # tag opener, so escaping `>` would be cosmetic.
        self.assertIn("&lt;value>&#125;", out)


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
                    "parameters": (),
                }
            },
        }
        out = gen.generate_provider_mdx(provider)
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
                    "parameters": (),
                },
            },
        }
        out = gen.generate_provider_mdx(provider)
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
        out = gen.generate_index_mdx(providers)
        # Slack has 2 actions → plural; Google Sheets has 1 → singular.
        self.assertIn('description="2 actions available"', out)
        self.assertIn('description="1 action available"', out)
        # Slugs follow the hyphenation rule.
        self.assertIn("/docs/api-reference/actions/google-sheets", out)
        self.assertIn("/docs/api-reference/actions/slack", out)

    def test_alphabetical_ordering(self):
        providers = [
            {"id": "zzz", "display_name": "Zeta", "actions": {"a": {}}},
            {"id": "aaa", "display_name": "Alpha", "actions": {"a": {}}},
        ]
        out = gen.generate_index_mdx(providers)
        self.assertLess(out.index('title="Alpha"'), out.index('title="Zeta"'))

    def test_skips_non_dict_actions_in_count(self):
        providers = [
            {
                "id": "x",
                "display_name": "X",
                "actions": {"good": {}, "bogus": "not a dict"},
            }
        ]
        out = gen.generate_index_mdx(providers)
        self.assertIn('description="1 action available"', out)


class GenerateMetaJsonTests(unittest.TestCase):
    def test_pages_listed_alphabetically_by_display_name(self):
        providers = [
            {"id": "zzz", "display_name": "Zeta", "actions": {}},
            {"id": "aaa", "display_name": "Alpha", "actions": {}},
        ]
        meta = json.loads(gen.generate_meta_json(providers))
        self.assertEqual(meta["title"], "Actions")
        self.assertEqual(meta["pages"], ["index", "aaa", "zzz"])

    def test_underscores_converted_to_hyphens(self):
        providers = [
            {"id": "google_sheets", "display_name": "Google Sheets", "actions": {}},
        ]
        meta = json.loads(gen.generate_meta_json(providers))
        self.assertIn("google-sheets", meta["pages"])


PROVIDER_SRC = textwrap.dedent(
    '''
    from enum import Enum

    class ParameterType(Enum):
        STRING = "string"
        NUMBER = "number"

    class FakeProvider:
        display_name: str = "Fake"
        description: str = "A fake provider."
        action_specs: dict = {
            "send": {
                "display_name": "Send",
                "description": "Sends a message.",
                "path": "/actions/library/fake/send",
                "method": "POST",
                "parameters": [
                    {
                        "name": "channel",
                        "type": ParameterType.STRING,
                        "required": True,
                        "description": "Where to send it.",
                    }
                ],
                "mock_response": {"status": "success"},
            }
        }
    '''
)


class ParseProviderTests(unittest.TestCase):
    """Tests for ``parse_provider`` and ``discover_providers``."""

    def _make_provider_dir(self, providers_dir: Path, name: str, source: str) -> None:
        pdir = providers_dir / name
        pdir.mkdir(parents=True)
        (pdir / "provider.py").write_text(source)

    def test_parses_provider_attributes_and_actions(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as tmp:
            providers_dir = Path(tmp) / "providers"
            self._make_provider_dir(providers_dir, "fake", PROVIDER_SRC)
            with mock.patch.object(gen, "PROVIDERS_DIR", providers_dir):
                info = gen.parse_provider("fake")

        self.assertIsNotNone(info)
        self.assertEqual(info["id"], "fake")
        self.assertEqual(info["display_name"], "Fake")
        self.assertEqual(info["description"], "A fake provider.")
        self.assertIn("send", info["actions"])
        send = info["actions"]["send"]
        self.assertEqual(send["display_name"], "Send")
        self.assertEqual(send["method"], "POST")

    def test_returns_none_when_no_actions(self):
        from tempfile import TemporaryDirectory

        src = textwrap.dedent(
            '''
            class EmptyProvider:
                display_name: str = "Empty"
                description: str = ""
            '''
        )

        with TemporaryDirectory() as tmp:
            providers_dir = Path(tmp) / "providers"
            self._make_provider_dir(providers_dir, "empty", src)
            with mock.patch.object(gen, "PROVIDERS_DIR", providers_dir):
                self.assertIsNone(gen.parse_provider("empty"))

    def test_returns_none_for_missing_file(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as tmp:
            providers_dir = Path(tmp) / "providers"
            providers_dir.mkdir()
            with mock.patch.object(gen, "PROVIDERS_DIR", providers_dir):
                self.assertIsNone(gen.parse_provider("missing"))

    def test_handles_plain_assignment(self):
        from tempfile import TemporaryDirectory

        src = textwrap.dedent(
            '''
            class XProvider:
                display_name = "X"
                description = "x-desc"
                action_specs = {
                    "a": {"display_name": "A", "path": "/p", "method": "POST"}
                }
            '''
        )

        with TemporaryDirectory() as tmp:
            providers_dir = Path(tmp) / "providers"
            self._make_provider_dir(providers_dir, "x", src)
            with mock.patch.object(gen, "PROVIDERS_DIR", providers_dir):
                info = gen.parse_provider("x")

        self.assertIsNotNone(info)
        self.assertEqual(info["display_name"], "X")
        self.assertEqual(info["description"], "x-desc")
        self.assertIn("a", info["actions"])

    def test_returns_none_on_syntax_error(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as tmp:
            providers_dir = Path(tmp) / "providers"
            self._make_provider_dir(
                providers_dir, "broken", "this is not python ::: ::"
            )
            with mock.patch.object(gen, "PROVIDERS_DIR", providers_dir):
                self.assertIsNone(gen.parse_provider("broken"))

    def test_falls_back_to_titlecased_id_when_no_display_name(self):
        from tempfile import TemporaryDirectory

        src = textwrap.dedent(
            '''
            class NoNameProvider:
                action_specs = {"a": {"path": "/p", "method": "POST"}}
            '''
        )

        with TemporaryDirectory() as tmp:
            providers_dir = Path(tmp) / "providers"
            self._make_provider_dir(providers_dir, "google_sheets", src)
            with mock.patch.object(gen, "PROVIDERS_DIR", providers_dir):
                info = gen.parse_provider("google_sheets")

        self.assertIsNotNone(info)
        self.assertEqual(info["display_name"], "Google Sheets")


class DiscoverProvidersTests(unittest.TestCase):
    def test_lists_provider_dirs_with_provider_py(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as tmp:
            providers_dir = Path(tmp) / "providers"
            providers_dir.mkdir()
            # Valid provider.
            (providers_dir / "slack").mkdir()
            (providers_dir / "slack" / "provider.py").write_text("")
            # Underscore-prefixed dir → ignored.
            (providers_dir / "_internal").mkdir()
            (providers_dir / "_internal" / "provider.py").write_text("")
            # Directory without provider.py → ignored.
            (providers_dir / "no_provider").mkdir()
            # File in providers dir → ignored.
            (providers_dir / "loose.py").write_text("")

            with mock.patch.object(gen, "PROVIDERS_DIR", providers_dir):
                self.assertEqual(gen.discover_providers(), ["slack"])

    def test_returns_empty_when_dir_missing(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as tmp:
            missing = Path(tmp) / "does-not-exist"
            with mock.patch.object(gen, "PROVIDERS_DIR", missing):
                self.assertEqual(gen.discover_providers(), [])

    def test_results_are_sorted(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as tmp:
            providers_dir = Path(tmp) / "providers"
            providers_dir.mkdir()
            for name in ("zeta", "alpha", "mike"):
                (providers_dir / name).mkdir()
                (providers_dir / name / "provider.py").write_text("")
            with mock.patch.object(gen, "PROVIDERS_DIR", providers_dir):
                self.assertEqual(
                    gen.discover_providers(), ["alpha", "mike", "zeta"]
                )


class MainIntegrationTests(unittest.TestCase):
    """End-to-end test covering the full ``main`` orchestration."""

    def test_main_writes_index_meta_and_provider_files(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            providers_dir = tmp_path / "providers"
            # ``main`` prints ``output_dir.relative_to(DOCS_ROOT)``, so
            # the output dir must live underneath the patched DOCS_ROOT.
            output_dir = tmp_path / "out"
            pdir = providers_dir / "fake"
            pdir.mkdir(parents=True)
            (pdir / "provider.py").write_text(PROVIDER_SRC)

            with mock.patch.object(gen, "PROVIDERS_DIR", providers_dir), \
                 mock.patch.object(gen, "OUTPUT_DIR", output_dir), \
                 mock.patch.object(gen, "DOCS_ROOT", tmp_path):
                gen.main()

            self.assertTrue((output_dir / "meta.json").exists())
            self.assertTrue((output_dir / "index.mdx").exists())
            self.assertTrue((output_dir / "fake.mdx").exists())

            meta = json.loads((output_dir / "meta.json").read_text())
            self.assertEqual(meta["pages"], ["index", "fake"])

            provider_mdx = (output_dir / "fake.mdx").read_text()
            self.assertIn("### Send", provider_mdx)
            self.assertIn("Sends a message.", provider_mdx)


if __name__ == "__main__":
    unittest.main()
