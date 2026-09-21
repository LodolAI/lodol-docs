# Unipile integration — feasibility research

**Status:** research only. No provider code written.
**Date:** 2026-09-21.
**Scope:** what a Unipile provider would look like in the Lodol provider
library, what the Unipile API actually supports, and what the real
constraints are.

**Where the code would go:** `lodolai/lodol`, not this repo. See
[Part 1](#part-1--how-integrations-work-in-our-codebase). This document lives
outside `content/docs/`, so it is not rendered onto the docs site.

---

## Verdict

**Feasible, and the single highest-leverage provider we could add right now.**

Unipile is a documented REST API with a stable v1, per-endpoint OpenAPI
definitions published for all 94 endpoints, a plain `X-API-KEY` header, and a
credential model that maps onto our existing `api_key` + multi-`secret_fields`
pattern without any platform change. Nothing about it blocks an integration.

The reason it matters more than a typical provider: **it is the only way we
have to reach LinkedIn and WhatsApp at all.**

- We ship 678 providers and **none of them is LinkedIn, WhatsApp, Messenger or
  consumer Instagram.** The closest things we have are `phantombuster` (5
  actions, launches somebody else's scrapers), `enrich_layer` (15 actions,
  read-only profile enrichment), `apollo` (8 actions, a B2B database) and
  `hyperbrowser` (3 actions, which drives a real browser).
- `hyperbrowser/PLATFORM_FEASIBILITY.md` is the record of how much that costs
  us: LinkedIn works only because LinkedIn tolerates datacenter logins, and
  Instagram and Facebook are written off as blocked at Meta's reCAPTCHA wall.
  Unipile sells exactly that problem as a product — managed sessions, a fixed
  per-account proxy chosen from 55 countries, checkpoint/2FA handling, and
  connector maintenance when a provider changes.
- One provider covers messaging on four networks, email on Google/Microsoft/IMAP,
  calendars on Google/Microsoft, and the whole LinkedIn outreach surface
  (invitations, InMail, search, Sales Navigator, Recruiter, job postings).

Five things need a decision before implementation, none of them a blocker:

1. **v1 or v2.** v1 is stable and fully documented but its base URL is a
   per-customer DSN on a **non-standard port**. v2 has a fixed base URL
   (`https://api.unipile.com/v2`), ~179 endpoints, a built-in rate limiter that
   protects the customer's LinkedIn account, response caching, and Scopes for
   multi-tenancy — but Unipile labels it **beta with breaking changes expected**.
   Recommendation and reasoning in [v1 or v2](#v1-or-v2--the-one-real-decision).
2. **Two credentials on v1, one on v2.** v1 needs an API key *and* the DSN.
   Our `secret_fields` is a tuple and already does this (Zendesk collects three,
   Airtable two), so it is a UX detail, not a blocker.
3. **Account connection happens outside Lodol.** Connecting a LinkedIn or
   WhatsApp account needs an interactive wizard (QR scan, 2FA, captcha). We do
   not have, and should not build, a place for that. The customer connects
   accounts in the Unipile dashboard; our provider discovers them through a
   `dynamic_source` dropdown on `account_id`. See
   [Part 3](#part-3--things-that-will-bite-the-implementer).
4. **Who pays Unipile.** €49/month minimum, billed per connected account. A
   bring-your-own-key provider costs us nothing and gates the integration behind
   the customer's own Unipile subscription. See [Pricing](#pricing--who-pays).
5. **The customer's LinkedIn account is the thing at risk.** Unipile's own
   limits page recommends ~100 actions/day/account and warns that exceeding
   LinkedIn's limits produces account warnings. A workflow builder makes it easy
   to build a loop that does 10,000. See
   [Part 3](#part-3--things-that-will-bite-the-implementer).

**All official documentation was reachable.** Every page, all 94 v1 API
reference pages and the v2 documentation set were fetched successfully, and the
v2 API answered a live unauthenticated request from this build environment. The
one thing that is account-gated is called out in
[Documentation gaps](#documentation-gaps).

---

## Part 1 — How integrations work in our codebase

The provider library lives in the **server** repo, not here. This repo only
renders an artifact generated from it:

```
lodolai/lodol                                     lodolai/lodol-docs
  providers/<id>/provider.py  ──extract──▶  data/actions.json  ──render──▶  content/docs/api-reference/actions/<slug>.mdx
```

- `projects/server/scripts/extract_action_specs.py` walks
  `src/skipflow/integrations/providers/`, parses each `provider.py` with the
  stdlib `ast` module (it never imports the server), and emits the aggregate
  JSON.
- The `publish-action-specs` workflow in `lodolai/lodol` opens an automated PR
  against this repo with the refreshed `data/actions.json`.
- `scripts/render-actions-docs.py` here turns it into one MDX page per provider
  plus an index and `meta.json`. That output directory is `.gitignore`d and
  regenerated on every `predev` / `prebuild`.

**Nothing needs to be hand-written in this repo for a new provider.** Adding
Unipile on the server automatically produces
`/docs/api-reference/actions/unipile` on the docs site.

Current scale, measured 2026-09-21:

| Thing | Count |
| --- | --- |
| Provider directories on the server | 678 |
| Published providers in `data/actions.json` | 677 |
| Total actions | 6,847 |
| Providers with a `triggers.py` | 28 |
| Providers whose `actions.py` imports `requests` | 585 |
| Providers declaring `kind` on one line | 664 — of which 619 `api_key`, 34 `oauth`, 9 `client_credentials`, 2 `service_account` |
| Per-provider QA workflows | 647 |
| Per-provider unit-test directories | 671 |

The overwhelming house style is: **an API-key provider that talks plain REST
over `requests`.** Unipile is exactly that shape.

### Anatomy of a provider

Registration is by autodiscovery — `core/registry.py` runs `walk_packages` over
the `providers` package and imports every `*.provider`, `*.executors` and
`*.triggers` module; each `provider.py` ends with `register(TheProvider())`.
Dropping in a directory is all it takes.

| File | Responsibility |
| --- | --- |
| `actions.py` | HTTP client dataclass, one handler per action, and a `format_*_output` per action for human-readable step output. |
| `provider.py` | `upload_secrets`, `adapter` (credential adapter), `client_factory`, cache-source fetchers, and the provider class carrying all metadata + `action_specs`. Ends with `register(...)`. |
| `executors.py` | One `@register_executor("/actions/library/<id>/<action>")` per action — validates the request body and calls `run_action`. |
| `schemas.py` | *Optional.* Shared request/response shapes. 80 of 678 providers have one. |
| `triggers.py` | *Optional.* Polling trigger handler + `TriggerSpec`. Only 28 of 678 providers have one. |

Plus tests at `projects/server/tests/unit/integrations/providers/<id>/`, a QA
workflow at `projects/server/data/qa_workflows/<id>.json`, and a frontend icon
(a PNG at `projects/web-app/public/app-icons/<id>-icon.png` registered in
`projects/web-app/src/utils/app_utils.ts`).

### The provider class

Taking `TelegramProvider` as the reference shape, since it is our closest
existing messaging provider:

```python
class TelegramProvider:
    id: str = "telegram"
    kind: Kind = "api_key"              # oauth | api_key | service_account | client_credentials
    display_name: str = "Telegram"
    credential_adapter: CredentialAdapter = staticmethod(adapter)
    client_factory: ClientFactory = staticmethod(client_factory)
    upload_secrets = staticmethod(upload_secrets)

    cache_sources: dict[str, CacheSourceSpec] = {...}   # backs the builder's dropdowns
    action_specs: dict[str, ActionSpec] = {...}         # the public contract

    description: str = "Send Telegram messages, manage chat pins, and generate invite links."
    categories: tuple[Category, ...] = (Category.MESSAGING,)
    badge: str | None = "API Key"
    icon: str | None = "📨"
    search_keywords: tuple[str, ...] = ("Chat", "Bot", "Channels", "Groups")
    docs_url: str | None = "https://core.telegram.org/bots/api"
    setup_instructions: tuple[SetupInstruction, ...] = (...)
    secret_fields: tuple[SecretFieldSpec, ...] = (...)
```

`secret_fields` is a **tuple**, so a provider can collect several values at
install time. Zendesk collects `subdomain` + `clientId` + `clientSecret`;
Airtable collects `apiKey` + `baseUrl`. **This is the mechanism Unipile's DSN
would use on v1.**

### `ActionSpec`

```python
ActionSpec(
    id="telegram_send_message",            # "<provider>_<action>"
    name="send_message",
    display_name="Send a message",
    description="Send a text message to a Telegram chat.",
    handler=actions.send_message,
    parameters=(ParameterSpec(...), ...),
    display_str_template="Send a message to '{0}'.",
    result_str_template="Message sent.",
    path="/actions/library/telegram/send-message",   # kebab-case, matches the executor
    method="POST",
    returns={...},                         # JSON-schema-ish; drives the docs "Response"
    mock_response={...},                   # used by docs + evaluation
    output_formatter=actions.format_send_message_output,
)
```

`display_str_template` / `result_str_template` index into the action's
positional parameters (`{0}` is the first parameter).

### Dynamic dropdowns (`cache_sources`)

This is the part that decides whether Unipile feels good in the builder. A
`ParameterSpec` with `dynamic_source="accounts"` renders as a dropdown fed by
the named `CacheSourceSpec`; `dynamic_source_depends_on=("account_id",)` makes
a sibling field cascade off it. `eager=True` pre-fetches a dependency-free
source at install time; everything else is fetched on demand and on the field's
refresh button. A fetcher returns `[{"value": ..., "label": ...}]`.

Telegram's source is the instructive one for Unipile, because it has the same
"the API cannot enumerate everything" property:

```python
cache_sources = {
    "chats": CacheSourceSpec(
        key="chats",
        fetch=_fetch_chats,
        accumulate=True,       # a refresh merges, it does not replace
        empty_hint="No chats found yet. …",
    ),
}
```

`ParameterSpec` also carries `dynamic_source_allows_custom`, which lets the
builder offer a text input beside the dropdown. Telegram sets it because it
accepts an `@channelusername` that will never appear in the list. Unipile needs
the same on chat and profile fields for the same reason.

### Triggers — the constraint

Our trigger system (`core/triggers/`) is **polling only**. 28 of 678 providers
have a `triggers.py`, and every one runs a background thread on an interval
from `get_plan_poll_interval`:

```python
# projects/server/src/skipflow/execution/trigger_polling_policy.py
FREE_POLL_INTERVAL_SECONDS = 900  # 15 minutes for Free plan
PAID_POLL_INTERVAL_SECONDS = 60   # 1 minute for paid plans
```

The **only inbound webhook route in the whole server is Stripe billing**
(`skipflow/api/routes/billing/stripe_webhook_route.py`). There is no provider
webhook ingress; even Gmail polls. This matters for Unipile, which is
webhook-first — see [Triggers](#triggers).

---

## Part 2 — Unipile API research

Every page below is from Unipile's official developer site.
**Every page requested was reachable**; sources are listed at the end.

### What Unipile is

A unified API in front of messaging, email, calendar and social platforms. Your
application calls Unipile; Unipile authenticates with and drives the provider on
behalf of a connected account. Unipile's own framing is worth quoting because it
is the thing that makes it attractive and the thing that makes it risky:

> Provider integrations do not all rely on stable, public APIs. Some interfaces
> are private, undocumented, partially documented, or subject to change without
> notice. […] temporary disconnections, service interruptions, failed API
> Methods, and pauses in provider-derived realtime events are **expected failure
> modes**.
> — [Fundamentals](https://developer.unipile.com/v2.0/docs/fundamentals)

Unipile takes responsibility for monitoring and repairing connectors; the
application is responsible for reacting to status changes. That division is
fine for a backend service. It is a real design question for a workflow builder
— see [Part 3](#part-3--things-that-will-bite-the-implementer).

### Object model

Four nouns, and they are consistent across every network, which is the whole
point of the product:

| Object | What it is | Id example |
| --- | --- | --- |
| **Account** | One connected identity — a LinkedIn profile, a WhatsApp number, a mailbox. The unit of billing and of rate limiting. | `dfXlh46vQYCsMbVarumWlg` |
| **Chat** | A conversation, 1:1 or group, on any messaging network. | `R8J-xM9WX7eoHLp6gSVtWQ` |
| **Attendee** | A participant in a chat, as Unipile has synced them. | `C8zaRZTlVcmfnke_Vai4Gg` |
| **User / profile** | A person on the provider, addressed by **provider internal id** (`ACoAAAcDMMQ…`) or **provider public id** (`satyanadella`). | both accepted |

`GET /api/v1/accounts` returns `{id, name, type, created_at, sources[], …}`,
where `type` is one of `MOBILE`, `MAIL`, `GOOGLE_OAUTH`, `ICLOUD`, `OUTLOOK`,
`GOOGLE_CALENDAR`, `WHATSAPP`, `LINKEDIN`, `SLACK`, `TWITTER`, `EXCHANGE`,
`TELEGRAM`, `INSTAGRAM`, `MESSENGER`. That is exactly the shape a
`CacheSourceSpec` fetcher wants: `value = id`, `label = f"{name} ({type})"`.

Each account's `sources[].status` is one of `OK`, `STOPPED`, `ERROR`,
`CREDENTIALS`, `PERMISSIONS`, `CONNECTING`. `CREDENTIALS` is the one that
matters: it means the customer must reconnect that account by hand before any
step against it will work again.

### Supported networks

From the official [List of provider features][feat] matrix:

| Surface | Networks |
| --- | --- |
| **Messaging** (send, reply, list chats/messages/attendees, attachments, reactions, read receipts) | WhatsApp, LinkedIn, Instagram, Telegram |
| **LinkedIn outreach** (invitations, InMail, relations, accepted-invite detection, endorsements) | LinkedIn |
| **Posts & comments** (create, read, comment, react, list) | LinkedIn, Instagram |
| **LinkedIn inboxes** | Classic, Sales Navigator, Recruiter & Recruiter Lite, Company Page |
| **LinkedIn search** (people, companies, posts, jobs — by URL or by parameters) | LinkedIn (Classic / Sales Navigator / Recruiter) |
| **Job postings & applicants** | LinkedIn |
| **Email** (send, list, drafts, delete, move, folders) | Google, Microsoft, IMAP |
| **Calendar** (list calendars, CRUD events) | Google, Microsoft |

**X (Twitter) and Facebook Messenger are deprecated.** The Hosted Auth page
lists both as "no longer maintained", and neither appears in the feature matrix
above, even though both still have guide pages and `TWITTER`/`MESSENGER` account
types in the schema. Treat them as unavailable.

### Authentication

`X-API-KEY: <access token>` on every request. That is the whole scheme — no
OAuth dance, no token refresh, no expiry to manage. Our `api_key` kind covers
it directly and the credential adapter is a dozen lines.

The wrinkle is the **base URL**, and it differs between versions:

| | v1 | v2 |
| --- | --- | --- |
| Base URL | `https://{YOUR_DSN}/api/v1` | `https://api.unipile.com/v2` |
| DSN | per-customer, e.g. `api8.unipile.com:13424` | none |
| Non-standard port | **yes** | no |
| Credentials to collect | API key **+ DSN** | API key only |

On v1 the DSN is copied out of the customer's dashboard and includes a
customer-specific host *and port*. Unipile documents a workaround for
environments that block outbound traffic on non-standard ports:

> If custom port are blocked in your environment, you can use port as query
> parameter to stay on standard 443,
> `https://apiX.unipile.com/api/v1/accounts?port=XXXXX`
> — [API Usage](https://developer.unipile.com/docs/api-usage)

**Whether our egress policy permits arbitrary high ports is an infra question
worth answering before writing code.** If it does not, the `?port=` form is the
fallback and the client should just always use it.

### v1 or v2 — the one real decision

| | **v1** | **v2** |
| --- | --- | --- |
| Status | stable, in production | **beta**, "Unipile may introduce breaking changes" |
| Endpoints | **94** (counted from the embedded OpenAPI on all 94 reference pages) | ~179 (184 reference entries less 5 non-endpoint pages) |
| Base URL | per-customer DSN + port | fixed `https://api.unipile.com/v2` |
| Pagination | opaque `cursor` | `offset` + `limit` |
| Rate limiting | none of its own; provider limits are the customer's problem | **Unipile rejects requests before they reach the provider** |
| Caching | not documented | `Cache-Control` request directives, cached responses don't count toward limits |
| Multi-tenancy | none | **Scopes** — one Application, one scoped API key per customer |
| LinkedIn surface | one `/linkedin/*` namespace | split into Classic / Recruiter / Sales Navigator namespaces, plus lead/account lists |
| Account | existing | **a new account must be created at `dashboardv2.unipile.com`** even if you have v1 |
| Python SDK | none | official, but **beta, v2-only, not on PyPI, 0 stars** |

**Recommendation: build against v1, and structure the client so the base URL and
path prefix are one constant.**

The reasoning:

- v1 is stable and its documentation is complete enough that the entire
  94-endpoint surface was reconstructed from public pages during this research.
  v2 explicitly warns of breaking changes; a provider that ships to customers
  should not be riding that.
- The v2 features that are genuinely attractive — the built-in rate limiter and
  the response cache — are the *safety* argument for v2, not a capability
  argument. They mitigate exactly the LinkedIn-ban risk in Part 3. That makes v2
  worth revisiting the moment it leaves beta, and worth raising with the team now.
- v2's Scopes are the mechanism we would need **if** Lodol ever wanted to run one
  Unipile account on behalf of many Lodol customers instead of bring-your-own-key.
  That is a business decision, not an engineering one, but it should be made with
  the knowledge that the mechanism exists.
- The Python SDK is not usable either way: beta, v2-only, unpublished on PyPI,
  zero stars. Use `requests` against the documented REST surface, like the other
  585 providers do.

### Rate limits — two layers, and the second one is the dangerous one

**Layer 1 — Unipile's own API.** On v1, Unipile documents no request quota of
its own, and pricing confirms it: "Unlimited usage. Only provider limits apply."
On v2 there is a real rate limiter with `x-ratelimit-limit` /
`x-ratelimit-remaining` / `x-ratelimit-reset` / `retry-after` headers, applied
per-method, per-sensitive-method and per-account, with values configured in the
customer's dashboard.

**Layer 2 — the provider's limits, enforced against the customer's real
account.** This is the one that matters. From
[Provider Limits and Restrictions][limits]:

| Action | Unipile's recommendation |
| --- | --- |
| LinkedIn connection invitations | 80–100/day, ~200/week on a paid account. **~5/month with a note on a free account.** |
| LinkedIn profile retrievals | ~100/day/account |
| LinkedIn search results | 1,000/day (Classic) or 2,500/day (Sales Navigator/Recruiter) fetched rows |
| LinkedIn InMail | 30–50/day to maximise the monthly allocation |
| **Every other LinkedIn route** | **100/day/account** |
| Instagram | 100 actions/day, ≤10/hour |
| WhatsApp new chats | keep low; wait ~24h after connecting before any outreach |
| Gmail sending | 50–100/day (150–300 for Workspace) |

Unipile is blunt about what happens when these are exceeded:

> Exceeding LinkedIn's limits will result in an HTTP 429 or 500 error. Ensure
> your system handles this error effectively **to avoid warnings related to
> automation on your user account**.

And on polling specifically:

> We do not recommend polling [relations or the invitation list] every hour or
> at fixed times, such as 8:00 AM daily, as this pattern can be easily flagged
> as automation.

There is one important exception, and it is what makes a trigger possible:

> We manage messaging inbox synchronization on the server side […] This enables
> users to access and fetch their data **without limitations** via routes such
> as Messages, Chats, and Attendees.

So reading chats and messages hits Unipile's own synced store, not LinkedIn.
Reading profiles, relations, invitations and search hits LinkedIn live. **That
line runs straight through the middle of the action set and has to be drawn in
the UI, not just in a doc.**

### Pricing — who pays

From [unipile.com/pricing-api](https://www.unipile.com/pricing-api/):

- **€49/month** minimum, covering up to 10 linked accounts (~$55 USD).
- Then **€5.00/account/month** (11–50), stepping down through €4.00 (51–1,000)
  and €3.50 (1,001–5,000) to **€3.00** above 5,000.
- "1 account = 1 linked identity" — one LinkedIn profile, one WhatsApp number
  and one mailbox is three accounts.
- **Unlimited API calls** at every tier. No per-message or per-call charge.
- Post-paid, billed on the **peak** number of accounts live in each 30-day period.
- 7-day free trial, no card required.

For a bring-your-own-key provider this costs Lodol nothing and the customer
brings their own subscription — the same arrangement as every other `api_key`
provider we ship. It does mean **the integration is gated behind a €49/month
floor**, which is higher than most providers in the library and worth saying out
loud on the integration card.

### Endpoint inventory — v1, all 94

Reconstructed from the OpenAPI definition embedded in each of the 94 official
reference pages.

**Accounts (11)** — `GET /accounts`, `POST /accounts`,
`POST /accounts/checkpoint`, `POST /accounts/checkpoint/resend`,
`GET /accounts/{account_id}/sync`, `GET|PATCH|POST|DELETE /accounts/{id}`,
`POST /accounts/{id}/restart`, `POST /hosted/accounts/link`

**Chats (9)** — `GET|POST /chats`, `GET|PATCH|DELETE /chats/{chat_id}`,
`GET /chats/{chat_id}/attendees`, `GET|POST /chats/{chat_id}/messages`,
`GET /chats/{chat_id}/sync`

**Messages (7)** — `GET /messages`, `GET|PATCH|DELETE /messages/{message_id}`,
`GET /messages/{message_id}/attachments/{attachment_id}`,
`POST /messages/{message_id}/forward`, `POST /messages/{message_id}/reaction`

**Attendees (6)** — `GET /chat_attendees`, `GET /chat_attendees/{id}`,
`GET /chat_attendees/{id}/picture`, `GET /chat_attendees/{attendee_id}/chats`,
`GET /chat_attendees/{attendee_id}/sync`,
`GET /chat_attendees/{sender_id}/messages`

**Users / relations (14)** — `GET /users/{identifier}`, `GET /users/me`,
`PATCH /users/me/edit`, `GET /users/relations`, `GET /users/followers`,
`GET /users/following`, `POST /users/invite`, `GET /users/invite/sent`,
`GET /users/invite/received`, `POST /users/invite/received/{invitation_id}`,
`DELETE /users/invite/sent/{invitation_id}`, `GET /users/{identifier}/posts`,
`GET /users/{identifier}/comments`, `GET /users/{identifier}/reactions`

**Posts (6)** — `POST /posts`, `GET /posts/{post_id}`,
`GET|POST /posts/{post_id}/comments`, `GET /posts/{post_id}/reactions`,
`POST /posts/reaction`

**LinkedIn-specific (21)** — `POST /linkedin` (the "magic route" — proxies any
LinkedIn endpoint), `POST /linkedin/search`, `GET /linkedin/search/parameters`,
`GET /linkedin/company/{identifier}`, `GET /linkedin/inmail_balance`,
`GET /linkedin/contracts`, `POST /linkedin/contracts/{id}/select`,
`POST /linkedin/profile/endorse`, `POST /linkedin/user/{user_id}`,
`GET /linkedin/projects`, `GET /linkedin/projects/{id}`,
`GET|POST /linkedin/jobs`, `GET|PATCH /linkedin/jobs/{job_id}`,
`POST /linkedin/jobs/{draft_id}/publish`,
`POST /linkedin/jobs/{draft_id}/checkpoint`, `POST /linkedin/jobs/{id}/close`,
`GET /linkedin/jobs/{id}/applicants`,
`GET /linkedin/jobs/applicants/{applicant_id}`,
`GET /linkedin/jobs/applicants/{applicant_id}/resume`

**Email (10)** — `GET|POST /emails`, `GET /emails/contacts`,
`GET|PUT|DELETE /emails/{email_id}`,
`GET /emails/{email_id}/attachments/{attachment_id}`, `POST /drafts`,
`GET /folders`, `GET /folders/{folder_id}`

**Calendar (7)** — `GET /calendars`, `GET /calendars/{calendar_id}`,
`GET|POST /calendars/{calendar_id}/events`,
`GET|PATCH|DELETE /calendars/{calendar_id}/events/{event_id}`

**Webhooks (3)** — `GET|POST /webhooks`, `DELETE /webhooks/{id}`

### Pagination and filtering

Every list endpoint paginates with an opaque `cursor`; a null cursor means no
more results. The list endpoints that matter for a trigger all take `after` and
`before` timestamps plus `limit`:

| Endpoint | Useful query params |
| --- | --- |
| `GET /chats` | `account_id`, `account_type`, `unread`, `after`, `before`, `limit`, `cursor` |
| `GET /messages` | `account_id`, `sender_id`, `after`, `before`, `limit`, `cursor` |
| `GET /emails` | `account_id` (**required**), `folder`, `from`, `to`, `search`, `after`, `before`, `meta_only`, `limit`, `cursor` |
| `GET /chat_attendees` | `account_id`, `limit`, `cursor` |
| `GET /users/relations` | `account_id` (**required**), `filter`, `limit`, `cursor` |

---

## Part 3 — Things that will bite the implementer

### 1. Account connection cannot happen inside Lodol, and that is fine

Connecting a LinkedIn or WhatsApp account is an interactive wizard: QR code
scanning, username/password, 2FA by SMS or authenticator app, in-app validation,
OTP, and LinkedIn captchas. Unipile offers two ways to drive it — a **Hosted
Auth Wizard** (one API call returns a short-lived URL you redirect the user to)
and **Custom Auth** (you build the whole checkpoint state machine yourself).

Neither fits a workflow step:

- Hosted Auth needs an HTTPS redirect out of our app and back, a `notify_url`
  callback endpoint, and a success/failure landing page. We have no provider
  redirect infrastructure and one inbound webhook route in the entire server.
- Custom Auth means implementing QR polling, 2FA prompts and captcha handling
  inside a workflow builder's install dialog. That is a product, not a field.
- The links are deliberately short-lived: "All links expire upon daily restart,
  regardless of their stated expiration date. A new link must be generated each
  time a user clicks."

**The right answer is to not build it.** The customer connects their accounts on
Unipile's own Accounts dashboard page — which Unipile's getting-started guide
presents as the normal path — and our `setup_instructions` say so in one step.
Our provider then reads `GET /api/v1/accounts` into an `accounts` cache source,
and every action's `account_id` is a dropdown of accounts the customer has
already connected. That is a better install flow than most `api_key` providers
get, because the dropdown labels are real human names.

The eight account-lifecycle endpoints (`POST /accounts`, the two checkpoint
routes, reconnect, restart, delete, patch-proxy, hosted link) should be
**deliberately out of scope** for the same reason we don't expose schema
migrations on Attio.

### 2. `multipart/form-data`, not JSON, on the send paths

`POST /chats` and `POST /chats/{chat_id}/messages` are documented with
`content-type: multipart/form-data`, and LinkedIn options are nested with
bracket notation as *form fields*:

```
--form account_id=Yk08cDzzdsqs9_8ds \
--form 'text=Hello world !' \
--form attendees_ids=ACoAAAcDMMQBODyLwZrRcgYhrkCafURGqva0U4E \
--form linkedin[api]=classic \
--form linkedin[inmail]=true
```

Meanwhile `POST /linkedin/search` and most other writes are JSON. The client
dataclass needs both paths from day one, and the multipart one needs repeated
keys for `attendees_ids` and bracketed keys for the `linkedin` options. This is
the single most likely place to lose an afternoon.

Attachments ride the same multipart request (standard max 15 MB, PDF/image/video),
which lines up with `ParameterSpec(accepts_file_upload=True,
accepts_variable_reference=True)` on an array parameter.

### 3. Two identifiers for the same person, and only one of them is in the payload

A LinkedIn user has a **provider internal id** (`ACoAAAcDMMQ…`) and a **provider
public id** (`satyanadella`, the last path segment of their profile URL).
`GET /users/{identifier}` accepts either. But:

> For now, public identifiers are not present in Attendees, so you can use the
> `GET /users/{provider_id}` Method […] to find it

So a workflow that reads a chat, gets an attendee, and wants to look up that
person's profile must spend a second call to resolve the id — and **that second
call is one of the ~100/day profile retrievals**. Two mitigations worth building
in:

- Accept a pasted `linkedin.com/in/…` URL anywhere an identifier is taken, and
  strip it down to the public id. Attio does the equivalent for `app.attio.com`
  URLs and it is the right instinct: the URL is what is on screen when someone
  goes looking.
- Surface `provider_id` **and** `public_identifier` at the top level of every
  action's result, so a chained step never has to spend a call rediscovering one.

### 4. A step will fail because a session died, and that is normal operation

Unipile is explicit that disconnections are an expected failure mode, and that
the application must "pause workflows that depend on an unavailable account and
resume them when connectivity returns." We have no such machinery: a step that
gets a `CREDENTIALS` error just fails the run.

The minimum honest behaviour is a **clear, actionable error**: when a call comes
back with an auth/credentials failure, the handler should say *which* connected
account needs reconnecting and *where* (the Unipile dashboard), not surface a
raw 401. `list_accounts` should report each account's `sources[].status` for the
same reason — it makes "is my LinkedIn still connected?" a thing a workflow can
check before it starts a 200-step outreach loop.

### 5. The rate limits are the customer's LinkedIn account, not a quota

This is the difference between this provider and every other one in the library.
Exceeding a SmartSuite quota gets you throttled. Exceeding LinkedIn's gets the
customer's *real professional identity* flagged, restricted, or banned — and
Unipile's own guidance is that even the pattern matters ("space out all calls
rather than chaining them at regular intervals", "use random values").

A workflow builder is a machine for chaining calls at regular intervals. Three
concrete mitigations, in rough order of value:

1. **Put the numbers where the user is.** `description` text on the
   rate-limited actions (`send_invitation`, `get_profile`, `search`) that names
   the per-day recommendation, not just a link. The builder shows descriptions;
   nobody reads `docs_url`.
2. **Ship the loop guidance in the QA workflow and the setup instructions.**
   Our `skipflow_delay` provider already exists; the canonical Unipile outreach
   example should use it, with a randomised delay, rather than a bare loop.
3. **Revisit v2 for its rate limiter.** v2 rejects a request *before* it reaches
   LinkedIn and returns a distinguishable `api/too_many_requests` vs
   `provider/too_many_requests`. That is a genuine safety feature for our use
   case and is the strongest argument for v2 once it is out of beta.

### 6. Search is a two-step, parameterised API — don't try to flatten it

`POST /linkedin/search` accepts either a pasted LinkedIn search URL (Classic,
Sales Navigator saved searches, lead lists) **or** a structured body. The
structured body wants **numeric LinkedIn ids**, not text — `location:
[102277331, 102448103]`, `industry: {include: ["4"]}` — which you obtain from
`GET /linkedin/search/parameters?type=LOCATION&keywords=los+angeles`.

The workable v1 shape is: expose **URL-paste search** as the primary action
(`url` parameter, plus `api` and `category` selects), and expose
`get_search_parameters` as a separate lookup action for anyone building the
structured form by hand. Trying to render LinkedIn's full filter grammar as
`ParameterSpec`s is a project of its own and would still be incomplete.

### 7. `POST /linkedin` is a loaded gun

The "magic route" proxies **any** LinkedIn endpoint the caller names, using the
connected account's session. It is how Unipile documents following a user and
getting your own profile viewers, because those have no first-class route. It is
also unversioned, undocumented per-endpoint, and breaks whenever LinkedIn moves.

Recommendation: **do not expose it in v1.** If it goes in later, it should be a
clearly-labelled advanced action, not a general escape hatch.

---

## Part 4 — Proposed v1 action set

**12 actions.** For calibration: Telegram ships 6, Slack 19, Attio 20, and
Basecamp — our largest work-management provider — 19.

| # | Action | Endpoint | Networks | Notes |
| --- | --- | --- | --- | --- |
| 1 | `list_accounts` | `GET /accounts` | all | Also backs the `accounts` cache source. Reports `sources[].status` so a workflow can check connectivity first. |
| 2 | `list_chats` | `GET /chats` | LI, WA, IG, TG | `account_id` dropdown, `unread` toggle, `after`/`before`. Served from Unipile's synced store. |
| 3 | `list_chat_messages` | `GET /chats/{chat_id}/messages` | LI, WA, IG, TG | Chat id free-text + `dynamic_source_allows_custom`; chats are too numerous to enumerate. |
| 4 | `send_message` | `POST /chats/{chat_id}/messages` | LI, WA, IG, TG | Multipart. Optional attachments. |
| 5 | `start_chat` | `POST /chats` | LI, WA, IG, TG | Sends to a person rather than a chat; creates the chat if needed. Carries the `linkedin[inmail]` / `linkedin[api]` options as selects. |
| 6 | `list_chat_attendees` | `GET /chats/{chat_id}/attendees` | LI, WA, IG, TG | Resolves who is in a conversation. |
| 7 | `get_profile` | `GET /users/{identifier}` | LI, WA, IG, TG | Accepts a public id, a provider id, or a pasted profile URL. **Rate-limited — say so in the description.** |
| 8 | `send_invitation` | `POST /users/invite` | LI | **The most rate-limited action in the set.** Description must carry the 80–100/day and free-account numbers. |
| 9 | `list_relations` | `GET /users/relations` | LI | Description must carry Unipile's "do not poll this" warning. |
| 10 | `search` | `POST /linkedin/search` | LI | URL-paste primary; `api` and `category` as selects. |
| 11 | `create_post` | `POST /posts` | LI, IG | |
| 12 | `comment_on_post` | `POST /posts/{post_id}/comments` | LI, IG | |

**Provider metadata:**

```python
id = "unipile"
kind = "api_key"
display_name = "Unipile"
categories = (Category.MESSAGING, Category.SOCIAL_MEDIA, Category.CONTACTS)
badge = "API Key"
search_keywords = ("LinkedIn", "WhatsApp", "Instagram", "Telegram",
                   "Messaging", "Outreach", "InMail", "Sales Navigator",
                   "Recruiter", "Unified Inbox")
docs_url = "https://developer.unipile.com/docs/getting-started"
secret_fields = (apiKey: PASSWORD, dsn: TEXT)      # v1; dsn drops on v2
cache_sources = {"accounts": CacheSourceSpec(key="accounts",
                                             fetch=_fetch_accounts,
                                             eager=True)}
```

`search_keywords` matters more than usual here: the provider is called
"Unipile", and **nobody searching our integration list is going to type that.**
They will type "LinkedIn" or "WhatsApp". Per the note in `core/types.py`, name
and keywords are the only facets the frontend's `matchesProviderSearch` uses —
action names deliberately don't match — so the keyword list is the only thing
that makes this provider findable at all.

### Deliberately out of v1

- **Everything in account lifecycle** (connect, reconnect, checkpoints, restart,
  delete, proxy, hosted link) — [Part 3](#1-account-connection-cannot-happen-inside-lodol-and-that-is-fine).
- **Webhook CRUD** — we have no ingress to point them at.
- **`POST /linkedin`**, the magic route — [Part 3](#7-post-linkedin-is-a-loaded-gun).
- **Email and calendar** — real, and buildable, but they overlap our existing
  `gmail` (14 actions), `microsoft_outlook`, `google_calendar` and
  `microsoft_onedrive` providers, and those are already the better path for a
  customer who only needs Gmail. Unipile's email is worth adding for the **IMAP**
  case (any mailbox, one shape) — in v2, not v1.
- **Recruiter, Sales Navigator and job postings** — the deepest part of the API
  and the one with the narrowest audience. v4.

---

## Part 5 — Full scope of buildable actions

Everything below is buildable against documented v1 endpoints. The tiering is a
suggestion; the point is the ceiling.

| Tier | Contents | Actions | Effort |
| --- | --- | --- | --- |
| **v1** | The table in Part 4 | 12 | Multipart client is the only novel bit. |
| **v2 — email + calendar** | `list_emails`, `get_email`, `send_email`, `create_draft`, `update_email` (move/read), `delete_email`, `list_folders`, `list_email_contacts`, `list_calendars`, `list_events`, `create_event`, `update_event`, `delete_event` | 13 | Mechanical. `send_email` has documented nested-parameter quirks. |
| **v3 — social + relationship reads** | `get_post`, `list_user_posts`, `list_post_comments`, `list_post_reactions`, `add_post_reaction`, `list_user_comments`, `list_user_reactions`, `list_invitations_sent`, `list_invitations_received`, `handle_invitation`, `cancel_invitation`, `get_company_profile`, `list_followers`, `list_following` | 14 | Mechanical; all read-shaped. |
| **v4 — messaging depth** | `get_message`, `list_messages`, `forward_message`, `add_message_reaction`, `edit_message`, `delete_message`, `delete_chat`, `patch_chat` (read/mute/invite-link), `get_message_attachment`, `get_attendee`, `list_attendee_chats`, `list_attendee_messages`, `sync_chat_history` | 13 | `get_*_attachment` needs a binary response path. |
| **v5 — Recruiter / Sales Navigator / jobs** | `get_search_parameters`, `list_job_postings`, `get_job_posting`, `create_job_posting`, `edit_job_posting`, `publish_job_posting`, `close_job_posting`, `list_job_applicants`, `get_job_applicant`, `get_applicant_resume`, `list_hiring_projects`, `get_hiring_project`, `perform_member_action` (save lead / add to pipeline), `get_inmail_balance`, `list_contracts`, `select_contract`, `endorse_skill`, `edit_own_profile`, `get_own_profile` | 19 | Deepest, narrowest. Several need a Recruiter or Sales Navigator seat to test at all. |

**~71 actions is the realistic ceiling**, out of 94 v1 endpoints. The 23-endpoint
gap is the 8 account-lifecycle routes, 3 webhook routes, the magic route, the
account/attendee `sync` monitors (polling helpers, not workflow steps), the
picture download, and a handful that fold into a sibling action (`reply_to_comment`
shares an endpoint with `comment_on_post`, reconnect shares with connect).

That would make Unipile the **largest provider in the library by a wide margin**
if built out fully — which is an argument for tiering it, not for building it all.

### Not buildable

| Thing | Why |
| --- | --- |
| Connecting an account from inside Lodol | Interactive wizard: QR, 2FA, captcha, redirects. Needs product surface we don't have. |
| Real-time webhooks | No inbound provider webhook ingress in the server. |
| Anything on X (Twitter) or Messenger | Unipile lists both as "no longer maintained". |
| Facebook messaging | Not a supported Unipile provider; only appears on the limits page as guidance. |
| SMS / RCS | On Unipile's roadmap, not shipped. |

---

## Triggers

**Unlike SmartSuite, a polling trigger here is viable — for messaging only.**

The arithmetic that killed the SmartSuite trigger was quota: a 60-second poll is
~43,200 requests/month against a 5,000/month allowance. Unipile has no such
allowance. Pricing is per connected account with "unlimited usage", and the
messaging read routes are explicitly served from Unipile's own server-side
synced store "without limitations".

So a **"New message received"** trigger polling
`GET /chats?account_id=X&after=<last_seen>` at the standard 60s/900s interval
costs the customer nothing and never touches LinkedIn. That is the trigger to
build, and it would be the first trigger we have for LinkedIn or WhatsApp at all.

Three caveats:

1. **Do not build a relations or invitation-accepted trigger by polling.**
   Unipile names that pattern specifically as one LinkedIn flags as automation.
   Their answer is the `new_relation` webhook, which we cannot receive. If we
   want "when someone accepts my invitation", it has to wait for webhook ingress.
2. **On v2, a 60s poll is 1,440 requests/day/account** against a rate limiter
   whose per-account window is configured in the customer's dashboard. If we move
   to v2, the trigger must read `x-ratelimit-remaining` and back off. On v1 this
   does not arise.
3. **Unipile's own webhooks are much better than polling** — `message_received`
   arrives with the full message, sender, attendees and attachments inline, so
   there is no fetch-after-notify round trip. The moment the server grows a
   provider webhook ingress, this trigger should switch. Worth noting that this
   is now the **second** provider (after SmartSuite) where webhook ingress is the
   thing standing between us and a materially better trigger.

---

## Documentation gaps

**Nothing was unreachable.** Every documentation request during this research
returned real content: the `llms.txt` index, all 94 v1 API reference pages
(each carrying a complete OpenAPI definition for its endpoint), every v1 guide
requested, the full v2 documentation set including its 184-entry reference
index, the public pricing page, and the Python SDK repository. There were no
fetch failures, no silent 404s and no JS-only pages blocking content.

Unipile's docs are unusually agent-friendly: every page serves a `.md` variant,
and `https://developer.unipile.com/llms.txt` (and `/v2.0/llms.txt`) is a
complete machine-readable index. The full v1 endpoint inventory in
[Part 2](#endpoint-inventory--v1-all-94) was reconstructed entirely from public
pages.

Four things are account-gated rather than missing. None blocks implementation,
and **a 7-day free trial closes all four in an afternoon**:

| Gated thing | Why it matters | How to settle it |
| --- | --- | --- |
| **The aggregate OpenAPI spec** at `https://{DSN}/api-json` and `/api-yaml` | Would let us generate the client rather than hand-write it. | Needs a DSN. Mitigated: per-endpoint OpenAPI is embedded in every reference page, which is how this document's inventory was built. |
| **v2 rate-limit values** | v2's docs describe the *mechanism* (per-method, per-sensitive-method, per-account, rolling windows) but say "Check the Rate Limits section of the dashboard for detailed values and time windows." The actual numbers are not published. | One look at a trial dashboard. Only matters if we choose v2. |
| **The DSN format itself** | We know it is `apiX.unipile.com:PORT` from the docs' examples, but not the port range — which is what decides whether our egress policy needs a change or the `?port=` fallback is mandatory. | Sign up; the DSN is on the dashboard's front page. |
| **Live response shapes** | Every endpoint's schema is documented, but LinkedIn profile responses in particular are large and provider-dependent (`linkedin_sections=*` expands to experience, education, skills…). Worth seeing one real payload before writing `returns={...}`. | One authenticated GET. |

**Connectivity from our build environment is confirmed.** An unauthenticated
`GET https://api.unipile.com/v2/accounts` returns a clean RFC-7807-shaped
`401 {"object":"Error","status":401,"type":"api/missing_authorization",…}`, and
a bogus key returns `401 api/invalid_credentials` — so the v2 host is reachable
and its error envelope is well-formed. The v1 pattern host `api1.unipile.com`
answers `502` from Unipile's nginx rather than failing DNS, which is consistent
with v1 requiring the customer's specific host *and* port.

---

## Open questions for the team

1. **v1 or v2?** The recommendation above is v1 for stability, but v2's rate
   limiter is a real safety feature for a product where the failure mode is a
   customer's LinkedIn account getting restricted. Is "wait for v2 GA" an
   acceptable answer, or do we want the provider sooner on v1 and a migration later?
2. **Bring-your-own-key, or Lodol-operated?** Every `api_key` provider we ship is
   BYO-key, and that is the low-effort answer. But Unipile's v2 Scopes exist
   specifically so a platform can hold one Unipile account and issue a scoped key
   per customer. That would remove the €49/month floor from the customer's path
   and put it on ours. Product/finance call, but the mechanism exists and should
   be on the table.
3. **Non-standard outbound ports.** Does our egress policy allow arbitrary high
   ports to `*.unipile.com`? If not, v1's client must always use the `?port=`
   query-parameter form. Worth confirming before code, not during review.
4. **How hard do we guard the rate limits?** Options, increasing in cost:
   description text only; description plus a QA workflow that models the safe
   pattern; or actual client-side throttling in `actions.py`. Nothing else in the
   library throttles itself, so a per-action rate limiter would be a new pattern
   — but nothing else in the library can get a customer banned from LinkedIn.
5. **Scope of v1.** Is 12 actions the right cut, or does the integration need
   email and calendar on day one to read as "the unified inbox provider" rather
   than "the LinkedIn provider"?
6. **Is this the second vote for webhook ingress?** SmartSuite's trigger was
   dropped for the same missing capability. Unipile's messaging trigger is
   buildable by polling but would be strictly better on webhooks, and its
   *relations* trigger is not buildable at all without them. Two providers is a
   pattern worth costing.

---

## Sources

All URLs verified reachable on 2026-09-21. Every Unipile documentation page also
serves a Markdown variant by appending `.md`.

**Unipile v1 — guides**

- [Getting Started](https://developer.unipile.com/docs/getting-started)
- [API Usage](https://developer.unipile.com/docs/api-usage) (auth, DSN, the `?port=` workaround, pagination, OpenAPI schema URLs)
- [List of provider features][feat] (the capability matrix in Part 2)
- [Provider Limits and Restrictions][limits] (every rate-limit number in Part 3)
- [Connection methods](https://developer.unipile.com/docs/connect-accounts) (auth-method matrix, proxy countries, Chrome-extension cookie flow)
- [Hosted auth wizard](https://developer.unipile.com/docs/hosted-auth) (also the source for X/Messenger being unmaintained)
- [Custom authentication](https://developer.unipile.com/docs/native-auth)
- [Send Messages](https://developer.unipile.com/docs/send-messages) (multipart, `linkedin[inmail]`, attachments)
- [Retrieving messages](https://developer.unipile.com/docs/get-messages)
- [Retrieving users](https://developer.unipile.com/docs/retrieving-users) (the two-identifier problem)
- [Invite users](https://developer.unipile.com/docs/invite-users)
- [Detecting Accepted Invitations](https://developer.unipile.com/docs/detecting-accepted-invitations)
- [Perform API LinkedIn search and export result](https://developer.unipile.com/docs/linkedin-search)
- [Posts and Comments](https://developer.unipile.com/docs/posts-and-comments)
- [Email & Calendars overview](https://developer.unipile.com/docs/emails)
- [Webhooks overview](https://developer.unipile.com/docs/webhooks-2)
- [New messages webhook](https://developer.unipile.com/docs/new-messages-webhook)
- [Account status updates](https://developer.unipile.com/docs/account-lifecycle)
- [Dev Tools](https://developer.unipile.com/docs/dev-tools) (Node SDK only; no Python SDK listed for v1)
- [MCP](https://developer.unipile.com/docs/mcp)
- [X (Twitter) Guide](https://developer.unipile.com/docs/twitter-x-guide) · [Messenger Guide](https://developer.unipile.com/docs/messenger)

**Unipile v1 — API reference**

- [Reference index](https://developer.unipile.com/reference) and the documentation index at [llms.txt](https://developer.unipile.com/llms.txt)
- All 94 reference pages were fetched; the inventory in Part 2 is extracted from
  the OpenAPI definition embedded in each. Representative:
  [List all accounts](https://developer.unipile.com/reference/accountscontroller_listaccounts) ·
  [List all chats](https://developer.unipile.com/reference/chatscontroller_listallchats) ·
  [Start a new chat](https://developer.unipile.com/reference/chatscontroller_startnewchat) ·
  [Send a message in a chat](https://developer.unipile.com/reference/chatscontroller_sendmessageinchat) ·
  [Retrieve a profile](https://developer.unipile.com/reference/userscontroller_getprofilebyidentifier) ·
  [Send an invitation](https://developer.unipile.com/reference/userscontroller_adduserbyidentifier) ·
  [List all relations](https://developer.unipile.com/reference/userscontroller_getrelations) ·
  [Perform LinkedIn search](https://developer.unipile.com/reference/linkedincontroller_search) ·
  [Get raw data from any endpoint](https://developer.unipile.com/reference/linkedincontroller_getrawdata) ·
  [Send an email](https://developer.unipile.com/reference/mailscontroller_sendmail) ·
  [List all calendars](https://developer.unipile.com/reference/calendarscontroller_listcalendars) ·
  [Create a post](https://developer.unipile.com/reference/postscontroller_createpost)

**Unipile v2 (beta)**

- [Welcome](https://developer.unipile.com/v2.0/docs/welcome) (the beta notice; new account required at `dashboardv2.unipile.com`)
- [Fundamentals](https://developer.unipile.com/v2.0/docs/fundamentals) (the responsibility-boundary section quoted in Part 2)
- [Migration from v1 — Authentication & Accounts](https://developer.unipile.com/v2.0/docs/migration-auth-and-accounts)
- [Authenticate Requests / API Keys](https://developer.unipile.com/v2.0/docs/api-keys) (the three key tiers and the fixed `https://api.unipile.com/v2` base URL)
- [Scopes](https://developer.unipile.com/v2.0/docs/scopes) (multi-tenancy)
- [Rate Limits](https://developer.unipile.com/v2.0/docs/rate-limits) (the two-layer 429 model)
- [Rate limit headers](https://developer.unipile.com/v2.0/reference/rate-limit) · [Caching](https://developer.unipile.com/v2.0/reference/cache)
- [v2 documentation index](https://developer.unipile.com/v2.0/llms.txt)

**Unipile — commercial and SDKs**

- [API Pricing](https://www.unipile.com/pricing-api/)
- [unipile/unipile-node-sdk](https://github.com/unipile/unipile-node-sdk)
- [unipile/unipile-python](https://github.com/unipile/unipile-python) (beta, v2-only, not on PyPI)

**Account-gated (see [Documentation gaps](#documentation-gaps))**

- `https://{YOUR_DSN}/api-json` and `/api-yaml` — aggregate OpenAPI spec, needs a DSN
- `https://dashboard.unipile.com` / `https://dashboardv2.unipile.com` — the DSN, access tokens, and v2's rate-limit values

**Lodol codebase** (`lodolai/lodol` @ `695d91d`)

- `projects/server/src/skipflow/integrations/core/types.py` — `ProviderSpec`, `ActionSpec`, `ParameterSpec`, `CacheSourceSpec`, `SecretFieldSpec`, `Category`
- `projects/server/src/skipflow/integrations/core/registry.py` — autodiscovery and `run_action`
- `projects/server/src/skipflow/execution/trigger_polling_policy.py` — the 60s/900s poll intervals
- `projects/server/src/skipflow/api/routes/billing/stripe_webhook_route.py` — the only inbound webhook route
- `providers/telegram/` — closest existing messaging provider
- `providers/zendesk/provider.py` — multi-field `secret_fields` precedent
- `providers/attio/` — identifier-normalisation and large-action-set precedent
- `providers/hyperbrowser/PLATFORM_FEASIBILITY.md` — what LinkedIn/Instagram access costs us today
- `docs/SMARTSUITE_INTEGRATION_RESEARCH.md` — the format this document follows

[feat]: https://developer.unipile.com/docs/list-provider-features
[limits]: https://developer.unipile.com/docs/provider-limits-and-restrictions
