# SmartSuite integration — feasibility research

**Status:** implemented. The provider ships 47 actions on
`lodolai/lodol`, branch `claude/smartsuite-integration-research-9tn0g5`
(`projects/server/src/skipflow/integrations/providers/smartsuite/`).
**Date:** 2026-09-17, implementation 2026-09-18.
**Scope:** what a SmartSuite provider would look like in the Lodol provider
library, what the SmartSuite API actually supports, and what the real
constraints are.

## What shipped

Everything in [Part 5](#part-5--full-scope-of-buildable-actions) that is
buildable from public documentation — 47 actions across records (CRUD, bulk,
restore, trash), comments, views, files, solutions, tables, fields, members,
teams and webhooks, plus the derived actions. The `list_fields` action was
added beyond the Part 5 inventory because field slugs are opaque and nothing
else exposes the slug-to-label mapping.

No trigger ships, for the quota reason in
[Triggers](#triggers--the-one-real-problem).

Two follow-ups remain:

1. **Brand icon.** `projects/web-app/public/app-icons/smartsuite-icon.png`
   plus a line in `src/utils/app_utils.ts`. Left out deliberately rather than
   inventing artwork — the UI falls back to initials, so nothing is broken
   meanwhile.
2. **The three live-workspace questions** below. Each has a defensive
   behaviour in the code (the bulk-add-fields path falls back on a 404, the
   view action takes a pasted id), but they should be confirmed rather than
   left to a reviewer.

---

## Verdict

**Feasible, and a good fit.** SmartSuite ships a documented, stable REST API
that covers everything our existing database-style providers (Airtable,
Baserow, Coda, Monday) do: list containers, list/read/create/update/delete
records, comments, members, and schema metadata. Nothing about the platform
blocks an integration.

Two things are genuinely different from Airtable and need a decision before
implementation:

1. **Two credentials, not one.** Every request needs both an API token and a
   workspace id (`ACCOUNT-ID` header). There is no documented endpoint that
   resolves a workspace from a token, so the workspace id has to be collected
   at connection time. Our `secret_fields` already supports this (Airtable
   collects `apiKey` + `baseUrl`), so this is a UX detail, not a blocker.
2. **A polling trigger is not viable on most SmartSuite plans.** See
   [Triggers](#triggers-the-one-real-problem) — the arithmetic doesn't work
   against SmartSuite's monthly API quotas. Recommendation: ship actions only
   in v1.

All official documentation was reachable; every claim below links to the page
it came from. Sources are listed at the end.

---

## Part 1 — How integrations work in our codebase

The provider library lives in the **server** repo (`lodolai/lodol`), not in
this docs repo. `lodol-docs` only renders a generated artifact. Worth stating
plainly because it determines where the work happens:

```
lodolai/lodol                                     lodolai/lodol-docs
  providers/<id>/provider.py  ──extract──▶  data/actions.json  ──render──▶  content/docs/api-reference/actions/<slug>.mdx
```

- `projects/server/scripts/extract_action_specs.py` walks
  `src/skipflow/integrations/providers/`, parses each `provider.py` with the
  stdlib `ast` module (it never imports the server), and emits the aggregate
  JSON.
- The `publish-action-specs` workflow opens an automated PR against this repo
  with the refreshed `data/actions.json`.
- `scripts/render-actions-docs.py` here turns that into one MDX page per
  provider plus an index and `meta.json`. The output directory is
  `.gitignore`d and regenerated on every `predev` / `prebuild`.

**Nothing needs to be hand-written in this repo for a new provider.** Adding
SmartSuite to the server automatically produces
`/docs/api-reference/actions/smartsuite`.

Current scale: 643 provider directories on the server, 640 published
providers, 6,348 actions. 585 providers are `kind = "api_key"`, 33 are
`"oauth"`.

### Anatomy of a provider

Registration is by autodiscovery — `core/registry.py` does
`walk_packages` over the `providers` package and imports every module, and
each `provider.py` ends with `register(TheProvider())`. Dropping in a
directory is all it takes to register.

A provider directory contains:

| File | Responsibility |
| --- | --- |
| `actions.py` | HTTP client dataclass, one handler function per action, and a `format_*_output` function per action for human-readable step output. |
| `provider.py` | `upload_secrets`, `adapter` (credential adapter), `client_factory`, cache-source fetchers, and the provider class carrying all metadata + `action_specs`. Ends with `register(...)`. |
| `executors.py` | One `@register_executor("/actions/library/<id>/<action>")` per action — validates the request body and calls `run_action`. |
| `triggers.py` | *Optional.* Polling trigger handler + `TriggerSpec`. Only 27 of 643 providers have one. |

Plus tests at `projects/server/tests/unit/integrations/providers/<id>/`
(Airtable has `test_provider.py`, `test_actions.py`, `test_executors.py`,
`test_triggers.py`), and a frontend icon: a PNG at
`projects/web-app/public/app-icons/<id>-icon.png` registered in
`projects/web-app/src/utils/app_utils.ts`.

### The provider class

Taking `AirtableProvider` as the reference shape:

```python
class AirtableProvider:
    id: str = "airtable"
    kind: Kind = "api_key"                  # oauth | api_key | service_account | client_credentials
    display_name: str = "Airtable"
    credential_adapter: CredentialAdapter = staticmethod(adapter)
    client_factory: ClientFactory = staticmethod(client_factory)
    upload_secrets = staticmethod(upload_secrets)

    cache_sources: dict[str, CacheSourceSpec] = {...}   # backs the builder's dropdowns
    action_specs: dict[str, ActionSpec] = {...}         # the public contract

    description: str = "Work with Airtable bases, tables, and records."
    categories: tuple[Category, ...] = (Category.DATABASES, Category.SPREADSHEETS)
    badge: str | None = "API Key"
    icon: str | None = "📋"
    search_keywords: tuple[str, ...] = ("Database", "Spreadsheet", "Records", "Bases")
    docs_url: str | None = "https://airtable.com/developers/web/api/overview"
    setup_instructions: tuple[SetupInstruction, ...] = (...)
    secret_fields: tuple[SecretFieldSpec, ...] = (...)
```

`secret_fields` is a tuple, so a provider can collect several values from the
user at install time. Airtable collects a required `apiKey` (PASSWORD) and an
optional `baseUrl` (TEXT). **This is the mechanism SmartSuite's workspace id
would use.**

### `ActionSpec`

```python
ActionSpec(
    id="airtable_list_records",            # "<provider>_<action>"
    name="list_records",
    display_name="List records",
    description="Retrieve records from an Airtable table.",
    handler=actions.list_records,
    parameters=(ParameterSpec(...), ...),
    display_str_template="List records from '{1}' in base '{0}'.",
    result_str_template="Returned {2} records.",
    path="/actions/library/airtable/list-records",   # kebab-case, matches the executor
    method="POST",
    returns={...},                         # JSON-schema-ish; drives the docs "Response"
    mock_response={...},                   # used by docs + evaluation
    output_formatter=actions.format_list_records_output,
)
```

`display_str_template` / `result_str_template` index into the action's
positional parameters (`{0}` is the first parameter, etc.).

### Dynamic dropdowns (`cache_sources`)

This is the part that makes a database provider feel good in the builder. A
`ParameterSpec` with `dynamic_source="tables"` renders as a dropdown fed by
the named `CacheSourceSpec`; `dynamic_source_depends_on=("base_id",)` makes it
cascade. `eager=True` pre-fetches a dependency-free source at install time;
everything else is fetched on demand and on the field's refresh button.

Airtable's cascade — the template for SmartSuite:

```python
cache_sources = {
    "bases":   CacheSourceSpec(key="bases",   fetch=_fetch_bases,   eager=True),
    "tables":  CacheSourceSpec(key="tables",  fetch=_fetch_tables,  depends_on=("base_id",)),
    "records": CacheSourceSpec(key="records", fetch=_fetch_records, depends_on=("base_id", "table_name")),
    "fields":  CacheSourceSpec(key="fields",  fetch=_fetch_fields,  depends_on=("base_id", "table_name")),
}
```

A fetcher returns `[{"value": ..., "label": ...}]`. On an `OBJECT` parameter,
`dynamic_source` behaves differently: the builder auto-populates one fixed key
per fetched option, so the user only fills in values and can't invent keys.
That is exactly how the `fields` editor works on Airtable's create/update
actions, and exactly what SmartSuite needs given its opaque field slugs.

Airtable's `_fetch_fields` filters out computed/read-only field types
(`formula`, `rollup`, `count`, `autoNumber`, `createdTime`, …) so the picker
can't offer a field that will fail on write. SmartSuite needs the same filter
with its own type names.

### House pattern for database-style providers

| Provider | Actions | Shape |
| --- | --- | --- |
| Airtable | 7 | `list_bases`, `list_tables`, `list_records`, `get_record`, `create_record`, `update_record`, `delete_record` |
| Baserow | 5 | `list_rows`, `get_row`, `create_row`, `update_row`, `delete_row` |
| Coda | 5 | `list_docs`, `list_tables`, `list_rows`, `add_row`, `update_row` |
| Monday.com | 6 | `list_boards`, `list_board_items`, `list_users`, `create_item`, `update_item_status`, `add_update` |

5–7 actions, container listing first, then record CRUD. A SmartSuite provider
should land in the same range and not try to expose all 40+ endpoints.

---

## Part 2 — SmartSuite API research

All pages below are from SmartSuite's official developer site and help centre.
**Every page I needed was reachable** — no paywalled or missing documentation.

### Object model

```
Workspace  (the ACCOUNT-ID; 8-char slug from the app URL)
 └─ Solution           /api/v1/solutions/
     └─ Table ("App")  /api/v1/applications/          ← note the legacy path name
         ├─ Field      table.structure[] — identified by an opaque `slug`
         ├─ Record     /api/v1/applications/{tableId}/records/
         └─ View       /api/v1/applications/{tableId}/records-for-report/
Members   /api/v1/members/list/
Teams     /api/v1/teams/list/
Comments  /api/v1/comments/
```

SmartSuite renamed "Apps" to "Tables" in the product, but the API path is
still `/applications/`. Their docs call this out explicitly.

Base URL: `https://app.smartsuite.com/api/v1`.

### Authentication

Two headers on every request:

```
Authorization: Token YOUR_API_KEY
ACCOUNT-ID:    WORKSPACE_ID
```

- The API key is generated per-user from the profile menu ("API Key" section)
  and **carries exactly that member's permissions** — a read-only member's key
  can only read. SmartSuite's own guidance is to create a dedicated
  least-privilege API member.
- The workspace id is the 8 characters after `https://app.smartsuite.com/` in
  the logged-in URL (e.g. `sv25cxf2`).
- API access is available on **all plan types** (with differing quotas).

**OAuth 2 exists but is gated.** The authentication page says OAuth access
tokens are "recommended for building an integration where other users grant
your service access to SmartSuite's API on their behalf", and their API
roadmap post says to **email support@smartsuite.com to request an OAuth
registration**. There is no public OAuth page in the developer docs sitemap —
no authorize/token URLs, no scope list, no PKCE details. So OAuth is a
business conversation with SmartSuite, not something that can be implemented
from published docs today. For v1, `kind = "api_key"` is the only option
documented well enough to build against.

### Rate limits and quotas — read this before designing anything

| Usage level | Rate |
| --- | --- |
| Under plan limit | 5 requests/second per user |
| 100–125% of plan limit | 2 requests/second per user (throttled) |
| Above 125% | **API access blocked until next billing cycle** |

| Plan | Included requests/month | Hard ceiling (125%) |
| --- | --- | --- |
| Team | 5,000 | 6,250 |
| Professional | 50,000 | 62,500 |
| Enterprise | 250,000 | 312,500 |

Overages are sold as an add-on at **$15 per 1,000 calls**. Limits are enforced
per user but counted workspace-wide, and usage from Zapier/Make/Softr counts
against the same pool. A 429 requires waiting 30 seconds.

These are small numbers. Every dropdown refresh in our builder is a real API
call against the customer's monthly quota, so `eager` pre-fetching and cache
reuse matter more here than they do for Airtable.

### Endpoint inventory

Everything relevant, from the official docs. [Part 5](#part-5--full-scope-of-buildable-actions)
takes the same list and works through what each one would become as an action.

| Area | Endpoint | Method | Notes |
| --- | --- | --- | --- |
| Solutions | `/solutions/` | GET | List all solutions in the workspace. |
| Solutions | `/solutions/{id}/` | GET | Single solution. |
| Solutions | `/solutions/` | POST | Create. Also duplicate + name validation endpoints. |
| Tables | `/applications/` | GET | List tables; `?solution={id}` filters, `?fields=` projects. Returns full `structure` (the field schema). |
| Tables | `/applications/{id}/` | GET | Single table incl. `structure` and `primary_field`. |
| Tables | `/applications/` | POST | Create table (needs ≥1 field in `structure`). |
| Records | `/applications/{tableId}/records/list/` | **POST** | List. Sort/filter in the body; `?offset=&limit=` (limit ≤ 1000, default 100); `?all=true` includes deleted. |
| Records | `/applications/{tableId}/records/{id}/` | GET | Single record. |
| Records | `/applications/{tableId}/records/` | POST | Create. |
| Records | `/applications/{tableId}/records/{id}/` | PATCH / PUT | **PATCH = partial, PUT = destructive** (clears unspecified fields). |
| Records | `/applications/{tableId}/records/{id}/` | DELETE | Delete. |
| Records | `/applications/{tableId}/records/bulk/` | POST / PATCH | Bulk create/update, **max 25 items**. Bulk create does *not* enforce required fields. |
| Records | `/applications/{tableId}/records/bulk_delete/` | PATCH | Bulk delete, max 25 ids. |
| Records | `/applications/{tableId}/records/{id}/restore/` | POST | Restore a deleted record (title gets `(Restored)` appended). |
| Records | `/deleted-records/` | POST | List deleted records for a solution. |
| Views | `/applications/{tableId}/records-for-report/?report={viewId}` | GET | Records as a saved View returns them. |
| Fields | `/applications/{tableId}/` + add/update/delete/bulk-add field endpoints | various | Schema manipulation. |
| Comments | `/comments/?record={id}` | GET | List; can also scope by `application` or `solution`. |
| Comments | `/comments/` | POST | Add comment or reply. Body accepts SmartDoc **or** plain `{"message": {"html": "..."}}`. |
| Members | `/members/list/` | POST | List workspace members; same sort/filter/pagination shape as records. |
| Teams | `/teams/list/` | POST | List teams. |
| Files | `/recordfiles/{tableId}/{recordId}/{fieldSlug}/` | POST | `multipart/form-data` binary upload. |
| Files | `/shared-files/{handle}/url/` | GET | Public URL for a stored file (20-year lifetime). |
| Webhooks | `https://webhooks.smartsuite.com/smartsuite.webhooks.engine.Webhooks/*` | POST | Separate host, RPC-style paths. **BETA.** |

### Sorting and filtering

`records/list/` is a POST specifically so it can take sort/filter JSON:

```json
{
  "filter": {
    "operator": "and",
    "fields": [{ "field": "status", "comparison": "is_not", "value": "Complete" }]
  },
  "sort": [{ "field": "title", "direction": "asc" }]
}
```

`operator` is required even for a single filter. `field` is the field **slug**.
Comparison operators vary by field type (`is`, `is_not`, `is_empty`,
`is_not_empty`, `contains`, `not_contains`, … and they're case-sensitive).
Date filters take a `{"date_mode": ..., "date_mode_value": ...}` object rather
than a bare value.

### Pagination

Offset-based, not cursor-based:

```json
{ "total": 5000, "offset": 0, "limit": 0, "items": [...] }
```

`?limit=100&offset=100` for the next page. Max `limit` is 1000.

---

## Part 3 — Things that will bite the implementer

1. **Field slugs are opaque.** A record comes back as
   `{"title": "...", "sef1a6a113": {...}}`. `sef1a6a113` is a user-created
   field. The only way to map "Due Date" → `sef1a6a113` is to read the table's
   `structure`. This makes the `fields` cache source **mandatory**, not a nice
   -to-have, for `create_record` / `update_record` to be usable at all.
2. **Field values are structured, not scalar.** SmartSuite has 46 field types
   and many take object values: `status` is `{"value": "in_progress"}`,
   a date range is `{"from_date": {"date": ..., "include_time": ...},
   "to_date": {...}}`, rich text is a SmartDoc (`{"data": ..., "html": ...}`),
   `assigned_to` is an array of member ids. A create/update handler that just
   forwards `{"Due Date": "2026-01-01"}` will fail. We need a coercion layer
   keyed off `field_type` from the table structure, or the create/update
   actions should be documented as accepting SmartSuite-native shapes.
   Their [field types reference][ss-field-types] documents the exact shape for
   each type.
3. **`hydrated: true` should probably be our default on reads.** Without it,
   select/status/user/lookup fields come back as raw ids. With it, SmartSuite
   returns human-readable labels — much better for a workflow variable or an
   LLM step consuming the output. It's a body param on `records/list/` and a
   query param on the single-record GET.
4. **Empty values are omitted from responses.** `""`, `[]` and `false` are
   dropped, so a key's absence does not mean the field doesn't exist. Output
   formatters shouldn't assume a stable key set.
5. **PUT is destructive.** Our `update_record` must use PATCH.
6. **Computed fields can't be written**: Auto Number, Count, First Created,
   Formula, Last Updated, Record ID, Rollup, Vote. Filter these out of the
   `fields` dropdown the way Airtable's `_READONLY_AIRTABLE_FIELD_TYPES` does.
   SmartSuite's type names are `autonumberfield`, `countfield`,
   `firstcreatedfield`, `formulafield`, `lastupdatedfield`, `recordidfield`,
   `rollupfield`, `votefield`, plus `lookupfield`. Button fields are also
   effectively read-only (their value is a generated URL or `null`), but the
   docs never print their API type name — confirm it against a live
   `/applications/{id}/` response rather than guessing.
7. **`/applications/` means tables.** Easy to misread as "list SmartSuite
   apps". The table id — not the solution id — is what record endpoints take.
8. **No workspace-discovery endpoint.** Nothing in the documented API maps a
   token to its workspace(s), so `ACCOUNT-ID` has to be collected from the
   user. Setup instructions should tell them to copy the 8 characters after
   `app.smartsuite.com/` from their browser URL.
9. **Response shapes are explicitly not frozen.** SmartSuite states that
   adding keys is not a breaking change. Handlers should project the fields
   they need rather than passing raw payloads through.
10. **429 handling.** Their docs say wait 30 seconds, and to back off rather
    than retry immediately.

---

## Part 4 — Proposed v1 action set

Mirrors the Airtable/Coda shape, one action per row. All `method="POST"`,
paths under `/actions/library/smartsuite/`.

| Action | SmartSuite call | Parameters |
| --- | --- | --- |
| `list_solutions` | `GET /solutions/` | — |
| `list_tables` | `GET /applications/?solution=` | `solution_id` *(dyn: `solutions`)* |
| `list_records` | `POST /applications/{t}/records/list/` | `table_id`\* *(dyn: `tables` ← `solution_id`)*, `limit`, `filter_field` *(dyn: `fields`)*, `filter_comparison`, `filter_value`, `hydrated` |
| `get_record` | `GET /applications/{t}/records/{r}/` | `table_id`\*, `record_id`\* *(dyn: `records`)* |
| `create_record` | `POST /applications/{t}/records/` | `table_id`\*, `fields`\* (OBJECT, dyn: `fields`) |
| `update_record` | `PATCH /applications/{t}/records/{r}/` | `table_id`\*, `record_id`\*, `fields`\* (OBJECT, dyn: `fields`) |
| `delete_record` | `DELETE /applications/{t}/records/{r}/` | `table_id`\*, `record_id`\* |
| `add_comment` | `POST /comments/` | `table_id`\*, `record_id`\*, `comment_text`\* (send as `{"message": {"html": ...}}`) |

`\*` = required.

Cache sources:

```python
cache_sources = {
    "solutions": CacheSourceSpec(key="solutions", fetch=_fetch_solutions, eager=True),
    "tables":    CacheSourceSpec(key="tables",    fetch=_fetch_tables,  depends_on=("solution_id",)),
    "records":   CacheSourceSpec(key="records",   fetch=_fetch_records, depends_on=("table_id",)),
    "fields":    CacheSourceSpec(key="fields",    fetch=_fetch_fields,  depends_on=("table_id",)),
}
```

Table ids are globally unique in SmartSuite, so `records` and `fields` only
need `table_id` — one dependency shallower than Airtable's cascade.

Provider metadata:

```python
kind = "api_key"
categories = (Category.DATABASES, Category.PROJECT_MANAGEMENT)
badge = "API Key"
search_keywords = ("Database", "Records", "Solutions", "Work Management", "Tables")
docs_url = "https://developers.smartsuite.com/docs/intro"
secret_fields = (
    SecretFieldSpec(id="apiKey",      label="SmartSuite API Key",      type=PASSWORD, required=True),
    SecretFieldSpec(id="workspaceId", label="SmartSuite Workspace ID", type=TEXT,     required=True,
                    placeholder="sv25cxf2"),
)
```

### Deliberately out of v1

Everything in [Part 5](#part-5--full-scope-of-buildable-actions) that isn't in
the table above. The short rationale: bulk has awkward semantics to surface in
a builder, schema writes have no precedent in our library, file upload needs a
second client, and org management is only useful once something needs to
resolve an assignee. All are buildable; none are needed to make the provider
useful on day one.

---

## Part 5 — Full scope of buildable actions

SmartSuite documents **39 REST surfaces**. Below is all of them, grouped, with
a verdict on each. "Buildable" here means documented well enough to implement
from public docs today — every row marked ✅ could be an action.

### Records — 13 surfaces

| # | Endpoint | Method | Action it would become | Verdict |
| --- | --- | --- | --- | --- |
| 1 | `/applications/{t}/records/list/` | POST | `list_records` (sort + filter + pagination + `hydrated`) | ✅ v1 |
| 2 | `/applications/{t}/records/{r}/` | GET | `get_record` | ✅ v1 |
| 3 | `/applications/{t}/records/` | POST | `create_record` | ✅ v1 |
| 4 | `/applications/{t}/records/{r}/` | PATCH | `update_record` (never PUT — destructive) | ✅ v1 |
| 5 | `/applications/{t}/records/{r}/` | DELETE | `delete_record` | ✅ v1 |
| 6 | `/applications/{t}/records/bulk/` | POST | `bulk_create_records` — max 25, **skips required-field validation** | ✅ |
| 7 | `/applications/{t}/records/bulk/` | PATCH | `bulk_update_records` — max 25, each item needs `id` | ✅ |
| 8 | `/applications/{t}/records/bulk_delete/` | PATCH | `bulk_delete_records` — max 25 ids | ✅ |
| 9 | `/applications/{t}/records/{r}/restore/` | POST | `restore_record` — title gets `(Restored)` appended | ✅ |
| 10 | `/deleted-records/` | POST | `list_deleted_records` (per solution) | ✅ |
| 11 | `/applications/{t}/records/{r}/` | PATCH | `attach_file_from_url` — file field takes a URL array | ✅ |
| 12 | `/recordfiles/{t}/{r}/{fieldSlug}/` | POST | `upload_file` — `multipart/form-data`, needs a second client path | ✅ |
| 13 | `/shared-files/{handle}/url/` | GET | `get_file_url` — 20-year public URL | ✅ |

### Views — 2 surfaces

| # | Endpoint | Method | Action | Verdict |
| --- | --- | --- | --- | --- |
| 14 | `/applications/{t}/records-for-report/?report={viewId}` | GET | `list_records_in_view` — returns records as the saved View filters/sorts them | ⚠️ see below |
| 15 | `/reports/` | POST | `create_view` — very large body (sharing flags, `state.filterWindow`, `state.fieldsWindow`, `view_mode`) | ✅ but unpleasant |

⚠️ **There is no documented REST endpoint that lists views.** The Views
category in SmartSuite's docs contains only "Create View"; the scripting API
has `retrieve_views` but that's a different runtime. So a
`list_records_in_view` action can't offer a view dropdown — the user would
paste a view id from the URL. A `GET /reports/?application=` probably works
but is undocumented and would need verifying against a live workspace before
we depend on it.

### Solutions — 5 surfaces

| # | Endpoint | Method | Action | Verdict |
| --- | --- | --- | --- | --- |
| 16 | `/solutions/` | GET | `list_solutions` | ✅ v1 |
| 17 | `/solutions/{id}/` | GET | `get_solution` | ✅ |
| 18 | `/solutions/` | POST | `create_solution` — `name`, `logo_icon`, `logo_color` (fixed 20-colour palette) | ✅ |
| 19 | `/solutions/duplicate/` | POST | `duplicate_solution` — cross-workspace, with `copy_records` / `copy_comments` toggles | ✅ |
| 20 | `/solutions/validate_name_uniqueness/` | POST | `validate_solution_name` → `{"is_unique": bool}` | ✅ but it's a helper, not a user-facing step |

### Tables — 3 surfaces

| # | Endpoint | Method | Action | Verdict |
| --- | --- | --- | --- | --- |
| 21 | `/applications/` | GET | `list_tables` — `?solution=` filters, `?fields=` projects | ✅ v1 |
| 22 | `/applications/{id}/` | GET | `get_table` — returns `structure` (the field schema) and `primary_field` | ✅ — also the engine behind the `fields` dropdown |
| 23 | `/applications/` | POST | `create_table` — needs ≥1 field in `structure` | ✅ |

### Fields — 4 surfaces

| # | Endpoint | Method | Action | Verdict |
| --- | --- | --- | --- | --- |
| 24 | `/applications/{t}/add_field/` | POST | `add_field` — caller invents a random 10-char slug; `params` is field-type-specific | ✅ |
| 25 | `/applications/{t}/bulk-add-fields/` | POST | `bulk_add_fields` | ⚠️ the docs page URL says `bulk-add-fields` but its own curl example says `bulk_add_fields` — one of them is wrong; verify live |
| 26 | `/applications/{t}/change_field/` | PUT | `update_field` | ✅ |
| 27 | `/applications/{t}/delete_field/` | POST | `delete_field` (by slug) | ✅ — destructive, should confirm in the builder |

All four need a per-field-type `params` payload across 46 field types. That's
the single largest chunk of work in the whole surface, and the least likely to
be asked for.

### Comments — 2 surfaces

| # | Endpoint | Method | Action | Verdict |
| --- | --- | --- | --- | --- |
| 28 | `/comments/?record={id}` | GET | `list_comments` — can scope by record, table, or solution | ✅ |
| 29 | `/comments/` | POST | `add_comment` **and** `reply_to_comment` (same endpoint, `parent_comment` set). Accepts plain `{"message": {"html": "..."}}` — no SmartDoc needed. Also takes `assigned_to`. | ✅ v1 (two actions from one endpoint) |

### Org management — 4 surfaces

| # | Endpoint | Method | Action | Verdict |
| --- | --- | --- | --- | --- |
| 30 | `/members/list/` | POST | `list_members` — same sort/filter/pagination shape as records | ✅ — useful as a `members` cache source for assignee pickers |
| 31 | `/members/{id}/` | PATCH | `update_member` — profile fields, role, status, timezone | ✅ but sensitive; admin-ish |
| 32 | `/teams/list/` | POST | `list_teams` | ✅ |
| 33 | `/teams/` | POST | `create_team` — quirky body: `id: null`, `type: "2"`, `first_created: null`, `comments_count: 0` all required | ✅ |

### Webhooks — 6 surfaces (BETA, separate host)

All on `https://webhooks.smartsuite.com/smartsuite.webhooks.engine.Webhooks/<Method>`, POST-only, RPC-style.

| # | Method | Action | Verdict |
| --- | --- | --- | --- |
| 34 | `CreateWebhook` | `create_webhook` — filter at solution / table / field granularity; kinds are `RECORD_CREATED`, `RECORD_UPDATED`, `RECORD_DELETED` | ⚠️ BETA |
| 35 | `GetWebhook` | `get_webhook` | ⚠️ BETA |
| 36 | `ListWebhooks` | `list_webhooks` (per solution) | ⚠️ BETA |
| 37 | `UpdateWebhook` | `update_webhook` | ⚠️ BETA |
| 38 | `DeleteWebhook` | `delete_webhook` — also deletes stored events | ⚠️ BETA |
| 39 | `ListEvents` | `list_events` — paged; **this is the only way to get event data**, the ping carries none | ⚠️ BETA |

These are buildable as plain actions today — a workflow could create a webhook
and poll `list_events` on a schedule. That's a fair bit worse than a real
trigger, but it is strictly cheaper than 1-minute polling and it's the only
change-detection mechanism SmartSuite offers. Calling `list_events` at least
weekly is also what keeps a webhook alive (7-day expiry, 14-day deletion).

### Derived actions — not 1:1 with any endpoint

Things worth building on top of the above, all composed from `records/list/`
plus its filter syntax. Several of our providers already do this kind of thing:

| Action | Built from | Why |
| --- | --- | --- |
| `find_record` | `records/list/` + filter, return first match | The single most common workflow need; saves users hand-writing filter JSON. |
| `search_records` | `records/list/` + filter builder | Guided field/comparison/value pickers instead of raw filter objects. |
| `count_records` | `records/list/` with `limit=1`, read `total` | One cheap call; the response always carries `total`. |
| `upsert_record` | filter → create or PATCH | Classic sync primitive. Two calls, so quota-aware. |
| `assign_record` | `members/list/` lookup → PATCH `assigned_to` | Users know emails, not the 24-char member ids the field actually takes. |
| `set_status` | `get_table` for choices → PATCH `{"status": {"value": ...}}` | Status takes an internal value, not the visible label. Mirrors Monday's `update_item_status`. |
| `link_records` | PATCH a `linkedrecordfield` with an id array | Linked records are core to how SmartSuite is used. |
| `download_file` | `get_file_url` → fetch | Returns a usable document to later workflow steps. |

### Not buildable

- **Delete table, duplicate table, delete view, duplicate view, resolve
  comment, update team, list views.** These exist in SmartSuite's *scripting*
  API — an in-product JavaScript runtime, not an HTTP surface — and have no
  documented REST equivalent. Not callable from outside SmartSuite.
- **OAuth connect flow.** Requires registration via support@smartsuite.com;
  no published authorize/token URLs or scopes.
- **Anything touching SmartSuite Automations.** No API surface at all.
- **List workspaces for a token.** Doesn't exist; hence the manual
  `ACCOUNT-ID`.

### Realistic sizing

| Tier | Actions | Effort |
| --- | --- | --- |
| v1 — records + comments + navigation | 8 | The proposal in Part 4. |
| v2 — bulk, files, views, org lookups | ~10 | Mostly mechanical; `upload_file` needs a multipart client path. |
| v3 — derived/composite | ~8 | No new endpoints, real UX gain. |
| v4 — schema writes + webhooks | ~13 | 46 field types' `params` payloads; webhooks are BETA. |

**~30 actions is the sensible ceiling**, out of ~39 endpoints — the gap is
helper endpoints (`validate_solution_name`) and things better folded into
another action (`reply_to_comment` shares an endpoint with `add_comment`).
For comparison, Basecamp is our largest work-management provider at 19 actions
and Airtable ships 7.

---

## Triggers — the one real problem

Our trigger system (`core/triggers/`) is **polling only**. 27 of 643 providers
have a `triggers.py`, and every one runs a background thread on an interval
from `get_plan_poll_interval`: **60s for paid plans, 900s for free**. The only
inbound webhook route in the server is Stripe billing; even Gmail polls.

Do the arithmetic against SmartSuite's quotas, assuming one request per poll:

| Poll interval | Requests/month | vs Team (5,000) | vs Professional (50,000) | vs Enterprise (250,000) |
| --- | --- | --- | --- | --- |
| 60s (paid plans) | ~43,200 | **8.6× over — throttled at ~3.5 days, blocked at ~4.3** | ~86% of quota | ~17% |
| 900s (free plan) | ~2,880 | ~58% of quota | ~6% | ~1% |

A single 1-minute "new record in SmartSuite" trigger would consume a
Professional customer's *entire* monthly API allowance, leaving nothing for
their other SmartSuite integrations (Zapier and Make usage counts against the
same pool), and would hard-block a Team customer within days. That is a
customer-visible failure we'd be causing.

**SmartSuite's own answer is webhooks**, and they're designed for exactly this:
subscribe at solution, table, or field granularity to `RECORD_CREATED` /
`RECORD_UPDATED` / `RECORD_DELETED`, receive a ping, then fetch. But:

- They are explicitly **BETA** ("use caution in production").
- The notification payload is only `{webhookId, locator}` — no event data. You
  must call `ListEvents` to get the change.
- A webhook **expires after 7 days** unless you call list-payloads, and is
  deleted after 14.
- They live on a different host (`webhooks.smartsuite.com`) with RPC-style
  paths, so they don't fit our REST client shape cleanly.
- We have no inbound webhook ingress for providers today; building one is a
  platform change, not a provider change.

**Recommendation:** ship v1 with actions only. Revisit a trigger either when
we have webhook ingress, or as a deliberately slow poll (15–30 min, quota-aware)
with the cost documented on the trigger itself.

---

## Documentation gaps

Every page requested during this research returned real content — 58 pages
across the developer site, help centre and blog, with no fetch failures and no
silent 404s. The gaps below are not access failures; they are documentation
that is account-gated, doesn't exist, or can only be settled against a live
workspace.

### Exists, but not readable from outside an account

- **`api-docs.smartsuite.com`** — a second, separate docs host. It's a React
  SPA (`<noscript>You need to enable JavaScript to run this app</noscript>`)
  and is almost certainly the in-product reference the help centre describes:
  reachable from a solution's menu → *API Documentation*, generating
  "solution-specific and table-specific examples based on your environment".
  Because it renders from the signed-in workspace's own schema, there is
  nothing static to read. **This is the most likely place the undocumented
  bits are actually written down.** Anyone with a SmartSuite login can check
  it in a minute.
- **`community.smartsuite.com`** (Developer Hub) — a Bettermode/Tribe SPA;
  thread content isn't in the served HTML and isn't well indexed by search.
  Historically where SmartSuite staff answer endpoint-level questions.

### Doesn't exist publicly at all

- **OAuth 2.** No authorize URL, token URL, scope list, PKCE details or
  registration form are published anywhere — the only pointer is "email
  support@smartsuite.com". Nothing to read; this is a conversation.
- **OpenAPI spec / Postman collection.** Not a fetch problem — they don't
  exist. It's an [open feature request][canny-openapi] on SmartSuite's Canny
  board, filed April 2025, still collecting "yes please" comments as recently
  as March 2026 with no official response. A spec would have resolved most of
  the ambiguity below for free.
- **Automations API.** No surface, no docs.

### Settled by a live workspace, not by documentation

These three are open because the docs are silent or self-contradictory, and no
amount of further reading fixes that:

| Unknown | Why it matters | How to settle it |
| --- | --- | --- |
| Does `GET /api/v1/reports/?application={id}` list views? | Decides whether `list_records_in_view` can have a view dropdown or needs a pasted id. | One authenticated GET. |
| Is the bulk-add-fields path `bulk-add-fields` or `bulk_add_fields`? | The docs page contradicts its own curl example. | One authenticated POST. |
| What is the Button field's API type name? | Needed for the read-only filter on the `fields` dropdown. | Read `structure` from any table with a Button field. |

The API is reachable from our build environment — an unauthenticated
`GET /api/v1/solutions/` returns a clean `400 Account ID is not specified`,
so connectivity and the `ACCOUNT-ID` requirement are both confirmed. **A
throwaway API key plus workspace id on any plan would close all three in
minutes.** Worth getting before implementation starts rather than discovering
them in review.

---

## Open questions for the team

1. **OAuth**: do we want to email support@smartsuite.com and start the OAuth
   registration conversation? It's the difference between "paste your API key"
   and a one-click connect, but it's not buildable from public docs today.
2. **Quota-aware dropdowns**: our dynamic sources fire real API calls on every
   refresh. Against a 5,000/month Team quota that's material. Is there an
   existing cache TTL we should lean on, or should SmartSuite's fetchers be
   more conservative than Airtable's?
3. **Field-value coercion**: do we build a `field_type`-aware coercion layer so
   users can write `"2026-01-01"` into a date field, or do we document the
   native shapes and let the builder pass them through? The first is better UX
   and more code; the second matches what Baserow/Coda do today.
4. **Trigger appetite**: is "no trigger in v1" acceptable, or is a SmartSuite
   trigger a requirement for the integration to be worth shipping?

---

## Sources

Official SmartSuite developer documentation:

- [Introduction](https://developers.smartsuite.com/docs/intro)
- [Authentication](https://developers.smartsuite.com/docs/authentication)
- [Rate Limits](https://developers.smartsuite.com/docs/rate-limits)
- [Errors](https://developers.smartsuite.com/docs/errors)
- [List Records](https://developers.smartsuite.com/docs/solution-data/records/list-records)
- [Get Record](https://developers.smartsuite.com/docs/solution-data/records/get-record)
- [Create Record](https://developers.smartsuite.com/docs/solution-data/records/create-record)
- [Update Record](https://developers.smartsuite.com/docs/solution-data/records/update-record)
- [Delete Record](https://developers.smartsuite.com/docs/solution-data/records/delete-record)
- [Bulk Add Records](https://developers.smartsuite.com/docs/solution-data/records/bulk-add-records)
- [Bulk Update Records](https://developers.smartsuite.com/docs/solution-data/records/bulk-update-records)
- [Bulk Delete Records](https://developers.smartsuite.com/docs/solution-data/records/bulk-delete-records)
- [Sorting and Filtering Records](https://developers.smartsuite.com/docs/solution-data/records/sort-filter)
- [Restore Deleted Record](https://developers.smartsuite.com/docs/solution-data/records/restore-deleted-record)
- [List Deleted Records](https://developers.smartsuite.com/docs/solution-data/records/list-deleted-records)
- [Attach File](https://developers.smartsuite.com/docs/solution-data/records/attach-file) · [Get File URL](https://developers.smartsuite.com/docs/solution-data/records/get-file-url)
- [List Solutions](https://developers.smartsuite.com/docs/solution-data/solutions/list-solutions) · [Get Solution](https://developers.smartsuite.com/docs/solution-data/solutions/get-solution) · [Create Solution](https://developers.smartsuite.com/docs/solution-data/solutions/create-solution) · [Duplicate Solution](https://developers.smartsuite.com/docs/solution-data/solutions/duplicate-solution) · [Validate Solution Name](https://developers.smartsuite.com/docs/solution-data/solutions/validate-solution-name)
- [List Tables](https://developers.smartsuite.com/docs/solution-data/tables/list-tables) · [Get Table](https://developers.smartsuite.com/docs/solution-data/tables/get-table) · [Table Object](https://developers.smartsuite.com/docs/solution-data/tables/table-object) · [Create Table](https://developers.smartsuite.com/docs/solution-data/tables/create-table)
- [Field Types and Properties][ss-field-types] · [Field Object](https://developers.smartsuite.com/docs/solution-data/fields/field-object) · [Add Field](https://developers.smartsuite.com/docs/solution-data/fields/add-field) · [Bulk Add Fields](https://developers.smartsuite.com/docs/solution-data/fields/bulk-add-fields) · [Update Field](https://developers.smartsuite.com/docs/solution-data/fields/update-field) · [Delete Field](https://developers.smartsuite.com/docs/solution-data/fields/delete-field)
- [List Comments](https://developers.smartsuite.com/docs/solution-data/comments/list-comments) · [Add Comment](https://developers.smartsuite.com/docs/solution-data/comments/add-comment)
- [Get Records for View](https://developers.smartsuite.com/docs/solution-data/views/records-for-view) · [Create View](https://developers.smartsuite.com/docs/solution-data/views/create-view)
- [Webhooks Overview](https://developers.smartsuite.com/docs/solution-data/webhooks/webhooks-overview) · [Create Webhook](https://developers.smartsuite.com/docs/solution-data/webhooks/create-webhook) · [Get Webhook](https://developers.smartsuite.com/docs/solution-data/webhooks/get-webhook) · [Update Webhook](https://developers.smartsuite.com/docs/solution-data/webhooks/update-webhook) · [Delete Webhook](https://developers.smartsuite.com/docs/solution-data/webhooks/delete-webhook) · [List Events](https://developers.smartsuite.com/docs/solution-data/webhooks/list-events) · [List Webhooks](https://developers.smartsuite.com/docs/solution-data/webhooks/list-webhooks)
- [List Members](https://developers.smartsuite.com/docs/org_management/members/list-members) · [Member Object](https://developers.smartsuite.com/docs/org_management/members/member-object) · [Update Member](https://developers.smartsuite.com/docs/org_management/members/update-member)
- [List Teams](https://developers.smartsuite.com/docs/org_management/teams/list-teams) · [Team Object](https://developers.smartsuite.com/docs/org_management/teams/team-object) · [Add Team](https://developers.smartsuite.com/docs/org_management/teams/add-team)
- [Scripting: Overview](https://developers.smartsuite.com/docs/scripting/intro) (confirms the scripting API is an in-product JavaScript runtime, not an HTTP surface)

SmartSuite help centre and blog:

- [SmartSuite API Overview](https://help.smartsuite.com/en/articles/4356333-smartsuite-api-overview)
- [API Transaction Limits](https://help.smartsuite.com/en/articles/4759981-api-transaction-limits)
- [REST API Permissions](https://help.smartsuite.com/en/articles/4856995-rest-api-permissions)
- [Generating an API Key](https://help.smartsuite.com/en/articles/4855681-generating-an-api-key)
- [Uploading and Downloading Files from the SmartSuite API](https://help.smartsuite.com/en/articles/7842079-uploading-and-downloading-files-from-the-smartsuite-api)
- [SmartSuite Public API Updates and Roadmap](https://www.smartsuite.com/blog/api-updates) (the OAuth registration announcement)

Gated or non-existent (see [Documentation gaps](#documentation-gaps)):

- `https://api-docs.smartsuite.com/` — account-scoped in-product reference, JS-only SPA
- `https://community.smartsuite.com/developer-hub-u5l41n7u` — Developer Hub, JS-only SPA
- [OpenAPI (Swagger) Specification for REST API][canny-openapi] — open feature request, not a released artifact

[ss-field-types]: https://developers.smartsuite.com/docs/solution-data/fields/field-types
[canny-openapi]: https://smartsuite.canny.io/feature-requests/p/openapi-swagger-specification-for-rest-api
