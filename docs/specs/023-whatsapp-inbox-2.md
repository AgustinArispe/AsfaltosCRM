# CRM-023 — WhatsApp Inbox 2.0

Status: Draft
Owner: FAA CRM team
Last updated: 2026-08-13

## Goal

Redesign the FAA CRM WhatsApp workspace as a fast, familiar desktop messaging
experience, informed by the usability model of leading WhatsApp desktop/web clients
without copying their brand, while making the relevant FAA commercial context available
at the point of conversation.

CRM-018 remains the visual, interaction, accessibility, responsive, and component
foundation. This spec does not change the provider/domain rules in CRM-005 through
CRM-011.

## Dependencies

- CRM-005 — WhatsApp Core
- CRM-006 — WhatsApp Internal API
- CRM-008 — WhatsApp Media Storage
- CRM-009 — Meta Cloud API Provider
- CRM-010 — WhatsApp Inbox Frontend
- CRM-011 — WhatsApp Broadcasts
- CRM-018 — Frontend Design System
- CRM-019 — Pipeline 2.0
- CRM-020 — Opportunity Detail & Quote Flow
- CRM-022 — Notifications UI

## Scope

- A desktop-first three-panel Inbox: conversation list, active chat, and concise CRM
  context.
- Familiar, efficient message reading and composition for supported text, image, and
  PDF/document contracts.
- A seller-facing presentation of backend-owned window, delivery, unread, waiting,
  resolution, and Opportunity-linking state.
- Incremental reconciliation, responsive panel behavior, accessible keyboard
  interaction, and coherent internal navigation contracts.

## Non-goals

- Cloning WhatsApp branding or using WhatsApp green as FAA product identity.
- Changing provider, Customer, Opportunity, unread, waiting, linking, media, or
  message-state business rules.
- WebSockets, SSE, calls, audio/video, AI replies, message-body search, per-user
  unread, Customer-resolution behavior not exposed by the backend, or a separate
  mobile-native application.
- Template editing, Broadcast redesign, manual conversation ordering, or external
  `wa.me` flows.
- New backend endpoints except those recorded under Open decisions as prerequisites.

## Product and visual direction

The Inbox should be immediately legible to an experienced messaging user: people on
the left, the conversation in the center, and business context on the right. It remains
FAA software: IBM Plex Sans, calm neutral surfaces, smooth restrained geometry, and
selective warm FAA yellow for identity, primary action, focus, and selected emphasis.

Chat bubbles may use a quiet FAA-tinted outbound surface, but must retain contrast in
Light and Dark themes. They must not reproduce WhatsApp colors, logos, bubble shapes,
or visual chrome. Waiting, unread, resolution, and delivery conditions always use text,
icons, and accessible names in addition to any color.

Use the CRM-018 shared primitives and semantic tokens for all controls, surfaces,
badges, menus, tooltips, dialogs, skeletons, feedback, focus rings, and themes. No
feature-local replacements of those primitives are permitted.

## App structure and layout

The WhatsApp sidebar destination opens a single workspace with these regions:

| Region | Purpose | Desktop behavior |
| --- | --- | --- |
| Left — Inbox | Find and select conversations. | Persistent, compact list panel. |
| Center — Chat | Read, send, and act in the active conversation. | Primary flexible region with a fixed composer. |
| Right — CRM context | See and safely act on concise Customer/Opportunity context. | Persistent when room permits; independently collapsible. |

At generous available width, the Inbox has three visible panels. The left panel is
roughly 18–20rem, the right context panel roughly 18–20rem, and the center chat has a
comfortable minimum working width of roughly 28rem before adaptive behavior begins.
Those are content-space guidance, not fixed-resolution breakpoints: the App Shell
sidebar state, browser zoom, localized content, and actual CSS viewport govern layout.

The center is the priority. The header is compact and contains the conversation identity,
phone only where useful, waiting state where applicable, and a context-panel toggle.
Message history scrolls inside the chat region; the composer remains fixed to its bottom.
No document-level horizontal scrolling is allowed under supported desktop/laptop and
zoom conditions.

The context-panel preference may persist locally under the CRM-018 client-preference
rules. Restoring a collapsed panel is an obvious, labelled action; its control remains
keyboard reachable.

## Conversation inbox

### Rows and ordering

Each compact row prioritizes, in this order:

1. Customer name or safe provider display identity;
2. optional company as supporting identity;
3. latest-message preview when the authoritative summary contract supplies one;
4. latest activity time;
5. unread state and waiting-for-response state.

The row must not become a miniature CRM record: no quoted products, kg, long status
history, or general Customer fields. Display identity never fabricates a Customer for a
`NEEDS_REVIEW` conversation. When a resolved Customer name is unavailable, use the safe
provider display name; when that is unavailable, use the normalized external phone.

The backend list ordering is authoritative and is never duplicated or made manually
sortable in React: waiting for response first, then unread, then recent activity, then
the stable backend tie-break. Selection does not disappear simply because a refresh or
filter would otherwise move the selected row. While the composer holds an unsent draft,
the selected row may defer its visual repositioning until send, discard, blur, or the
next non-disruptive reconciliation; its data state still updates immediately.

CRM-006 summaries currently contain activity timestamps and states but no latest message
body/preview. The UI must not load messages for every row to synthesize that preview;
until the Open-decision contract is resolved, use a concise, seller-facing activity
label as the honest fallback.

### Search and filters

Keep the toolbar compact and visually secondary. It includes a debounced search and
two independently operable compact filters, `Espera respuesta` and `No leídas`.
Filters combine with AND semantics because that is the existing API contract. The
active state and a one-action reset are always visible without turning the panel into a
filter wall.

Search is restricted to the existing supported server fields: Customer/name, company,
normalized phone, and provider display name. It must not imply full message-body search.
Filtering reloads the bounded, cursor-paginated server result and does not alter a
Conversation's business state. Load-more preserves server page order and counts are not
invented when the API has not supplied a total.

### Selection and read state

Selecting a row opens its chat and CRM context, preserves the selection through polling,
and marks the conversation read only through the existing idempotent global-read API
after the detail is successfully displayed. The list and any navigation badge reconcile
to the returned authoritative unread count. This is global acknowledgement state, not a
per-device or per-user read model.

## Active conversation

### History and message presentation

Load the newest useful message context first through the existing detail/history
contracts, in chronological display order. Load older history progressively using the
opaque before-cursor. Retain the viewport anchor when prepending older messages.

Message identity is stable by server ID. Incremental updates upsert the changed message
and delivery evidence rather than replacing the full history. If the seller is at the
bottom, valid new messages may follow naturally; if they are reading older history,
retain their position and show one restrained, labelled `Nuevos mensajes` affordance
that returns to the newest message. Routine polling never scrolls the seller away from
what they are reading.

Inbound and outbound bubbles have familiar opposing alignment, clear accessible labels,
subtle timestamps, and quiet sender context where relevant. Do not expose `ACCEPTED` or
other dispatch implementation terms. Translate the available backend evidence as:

| Backend evidence | Seller-facing presentation |
| --- | --- |
| local pending/in progress | `Enviando` |
| accepted or provider sent | `Enviado` |
| provider delivered | `Entregado` |
| provider read | `Leído` |
| definitive failure | `No se envió`, with a safe useful reason when available |
| unknown acceptance | `Entrega sin confirmar`, with an explanation that it may already have been delivered |

The status is not color-only. `UNKNOWN` is never automatically retried. When approved
backend behavior permits an explicit resend, it creates a distinct new message attempt,
preserves the original history, and first presents a clear duplicate-delivery warning.
An interrupted local request may instead retry the same idempotency key only while it is
the same unsent intent. No UI silently converts either condition into a resend.

### Composer, window policy, templates, and media

The composer is fast and focused. It supports only the current contracts:

- text;
- image in the server-accepted formats;
- PDF/document;
- optional caption/body only where the existing message contract supports it.

`Enter` sends normal text when a valid sendable message is focused; `Shift+Enter` adds a
newline. IME composition is respected. `Escape` closes a transient attachment/template
surface when safe; it does not discard a message draft. Disabled, pending, offline, and
backend-blocked states state why sending is unavailable. Send creates one client UUID,
disables duplicate submission while pending, and keeps a failed local intent available
for an explicit retry or discard decision.

For an image, show a local pre-send preview and explicit remove action. For a document,
show a filename, file type, and size. On receipt, images use authenticated CRM media
content; documents use authenticated download. Object URLs are revoked when no longer
needed. Storage keys, `media_ref` internals, provider temporary URLs, and direct object
storage URLs are never rendered, persisted, or exposed.

The backend `window_decision` is authoritative. React neither calculates a duration nor
hardcodes provider policy. When freeform is allowed, show the ordinary composer. When
it is blocked, disable freeform input and explain plainly that an approved template is
required. The template picker, parameter validation, and sender-facing preview are
defined to show only backend-confirmed usable templates; they cannot be implemented
until the human-conversation template API in Open decisions exists. Broadcast marketing
templates must not be repurposed for this flow.

There is no template editor in this workspace. Once the required contract is approved,
template parameter errors appear adjacent to the affected value, focus moves to the
first invalid parameter, and confirmation has the same duplicate-prevention semantics
as text/media sends.

## CRM context

The right panel adds commercial usefulness without recreating CRM-020. It shows only
concise, relevant context:

- Customer/company identity when resolved and available;
- current linked Opportunity and seller-facing status;
- effective Legendary state when the selected-context data supplies it;
- a small useful commercial summary when available from the selected context;
- safe actions to open, link, replace, unlink, or create an Opportunity where existing
  contracts permit.

The Inbox list never performs Customer or Opportunity enrichment requests per row.
The selected conversation detail is the bounded source for its Customer, active link,
open suggestions, and historical links. A selected-context detail fetch or a deeper
commercial request is permitted only to render information the existing contract
actually supplies, and must not block basic chat use. Opening full commercial detail
uses the centered CRM-020 Opportunity modal rather than embedding its form here.

For a resolved, available Customer, show no-link, one-current-link, and available
open-Opportunity suggestions distinctly. Link, replace, and unlink use the existing
historical linking semantics: only a Customer-owned available Opportunity may become
current; replacement preserves the old link in history; unlink closes the current link;
terminal historical Opportunities remain history and are not silently revived. Linking,
replacement, and unlinking require an explicit confirmation that names the result.

`Crear oportunidad` is shown only where the existing Customer/Opportunity API permits
creation for the resolved Customer. It creates through that existing commercial
contract, refreshes context/suggestions, and does not silently link a new Opportunity;
the seller explicitly links it afterwards if desired.

For `NEEDS_REVIEW`, show safe provider display information and a clear resolution-needed
state without fabricating Customer identity. Commercial actions and sending remain
restricted according to the backend. No Customer-resolution workflow is shown unless a
current approved API exposes it; its absence is safe and is recorded as a capability
gap, not solved by frontend inference.

## Waiting and unread

Waiting for response is a quiet but clear operational condition in the inbox row and,
where useful, the active header. It uses a label/icon plus restrained semantic emphasis,
not a flashing alarm. The frontend does not recompute it: a valid backend-accepted human
response clears it according to CRM-005, whereas pending, failed, unknown, and Broadcast
messages do not.

Unread is likewise global backend state. It is communicated with count/label and
non-color emphasis, reconciles after an opened conversation is marked read, and shares
the same definition as the CRM-018 sidebar `NotificationBadge`/CRM-022 attention
surfaces where applicable. It must not become a second notification system.

## Polling and reconciliation

Retain the cursor-based incremental model from CRM-006 and CRM-010. The WhatsApp
feature hook/service owns selection, list/message cursors, reconciliation, aborts, and
network/visibility lifecycle; presentational components do not poll or own business
state. API ownership remains the existing WhatsApp API client. No global state library
is introduced.

1. Load the selected bounded conversation page and retain its returned sync cursor.
2. Poll the conversation changes endpoint at a bounded cadence only when the tab is
   visible and the client is online; never overlap requests.
3. Upsert changed summaries by stable ID, reconcile the selected detail when it changes,
   and advance cursors page by page.
4. Poll only the selected conversation's message changes cursor, upsert by message ID,
   and preserve history scroll rules.
5. On focus, visibility/network recovery, or invalid/expired cursor, perform the
   existing full resync/reload path, then resume from its new cursor.

Polling preserves existing content, selection, composer draft, and scroll position.
It does not flash the inbox, refetch every conversation, make per-message status calls,
or animate every update. Surface an unobtrusive reconnecting/stale/error indication;
an independent list or message failure must not erase already usable chat content.

## Internal navigation contract

CRM-019, CRM-020, CRM-022, and CRM-023 must share one route-facing, typed navigation
intent for `open Opportunity`, `open exact WhatsApp conversation`, and return to an
originating workspace when practical. The intent includes only stable internal entity
IDs and optional origin context; it must not encode phone numbers, external URLs, or
temporary UI state.

From Opportunity detail, the WhatsApp action opens the CRM WhatsApp workspace with the
exact existing conversation selected. From a notification or Pipeline context, opening
an Opportunity uses CRM-020's detail surface; if the Opportunity is Lost or otherwise
outside the active Kanban, resolve it through an existing safe detail route rather than
pretending it is in a column. On return, retain origin context where the router can do
so without stale state. The current router has no finalized cross-workspace selection
contract, so its stable representation is an Open decision shared with CRM-019,
CRM-020, and CRM-022.

## Responsive and zoom behavior

Use available container width, not named devices or fixed resolutions.

- At large desktop widths, show all three panels.
- At normal laptop widths and browser zoom, retain the inbox and give chat priority;
  collapse the CRM context panel by default or make it an in-workspace overlay.
- At narrower supported widths, stage Inbox, Chat, and CRM context as labelled views or
  overlays with clear Back/Close controls instead of rendering unusably thin columns.
- The conversation list may narrow only while names, preview/activity, time, and state
  remain readable. The composer and chat history remain the primary working area.

Internal regions own their scrolling. Headers and composer stay visible within their
regions where beneficial. Typography and click/touch targets remain CRM-018-comfortable;
no horizontal page overflow or mobile-native redesign is introduced.

## Accessibility and keyboard interaction

Target WCAG 2.2 AA and CRM-018 requirements.

- Conversation rows are semantic, keyboard-reachable controls with useful names that
  communicate identity, waiting, and unread without over-reading metadata; `Enter` and
  `Space` select them.
- Message history has meaningful chronological structure, labelled inbound/outbound
  messages, status text beyond color, and a restrained live region only for new messages
  relevant to the active conversation.
- Composer, attachment, template, context, confirmation, and overlay controls have
  accessible names, descriptions, errors, and logical focus order.
- `Enter`/`Shift+Enter` behavior is as specified for messaging; global `Escape`, focus
  trap, focus return, and safe confirmation behavior follow CRM-018. A dirty draft is
  never discarded by Escape or a panel transition without deliberate confirmation.
- Interactive attachments, retry controls, links, filter controls, and the context
  collapse toggle have visible focus and usable desktop target sizes.
- Reduced motion removes nonessential movement; state changes remain understandable.

## Loading, empty, and error states

Initial Inbox load uses list/chat/context skeletons matched to their regions rather
than a full-page spinner. Preserve prior list and chat during polling, filtering, and
background refresh; show compact updating/reconnecting feedback only when useful.

Distinguish an empty Inbox, a filter/search result with no matches, an unselected
conversation, an empty message history, unavailable attachment content, and a failed
list/detail/message request. Empty states are concise operational guidance, not large
illustrations. A missing or terminal commercial entity leaves its historical message and
conversation evidence readable with safe unavailable context.

## Performance and architecture

- Compose the route from the App Shell and feature-level Inbox containers; keep shared
  design-system primitives outside the feature and WhatsApp-specific API/hooks/types
  inside its feature boundary.
- Use bounded, cursor-based existing endpoints, with no full Inbox reload per poll,
  no per-conversation or per-message N+1 requests, and no client reconstruction of
  business state.
- Keep composer state isolated so incoming polling does not interrupt typing or cause
  unnecessary rerenders. Reconcile only changed rows/messages where possible.
- Lazy-load heavy image previews and fetch heavier selected commercial detail only when
  useful. Virtualize only after profiling demonstrates a concrete need and preserves
  keyboard, focus, selection, and scroll semantics.
- Do not add a global state-management framework; existing React state, feature hooks,
  services, and route composition remain the default architecture.

## Acceptance criteria

- AC-01: The WhatsApp workspace follows CRM-018 and presents Inbox, active Chat, and
  independently collapsible CRM context as a usable three-panel desktop layout.
- AC-02: Conversation rows are compact and show safe identity, latest activity,
  waiting, unread, and an authoritative preview or the documented honest fallback.
- AC-03: Backend ordering and bounded search/waiting/unread filters remain
  authoritative; no manual order or unsupported message-body search exists.
- AC-04: Selecting a conversation updates chat and context, then applies existing
  global-read semantics without destabilizing selection during polling.
- AC-05: Chat loads newest context, progressively loads older messages with preserved
  scroll anchoring, upserts changes, and does not interrupt reading history.
- AC-06: Text, image, and PDF/document composition support the existing contracts,
  local pre-send media feedback, authenticated received-media access, safe errors, and
  duplicate-submission prevention.
- AC-07: Enter sends a valid normal message, Shift+Enter adds a newline, and Escape or
  panel changes never silently discard a draft.
- AC-08: Freeform availability follows only the backend window decision; blocked state
  clearly requires a template and human templates are not improvised from Broadcasts.
- AC-09: Seller-facing message states distinguish sending, sent, delivered, read,
  definitive failure, and delivery uncertainty; UNKNOWN is never automatically retried.
- AC-10: CRM context safely represents resolved, unresolved, linked, unlinked,
  replacement, historical-terminal, and suggested-Opportunity cases without automatic
  frontend linking or a duplicated Opportunity detail form.
- AC-11: `NEEDS_REVIEW` never fabricates a Customer and exposes only backend-permitted
  messaging and commercial actions.
- AC-12: Waiting and unread presentation uses authoritative global state and is not
  communicated by color alone.
- AC-13: Incremental cursor polling/upsert, visibility/network recovery, and stale/error
  feedback preserve existing content, active selection, composer state, and history
  position without flashing or routine full reloads.
- AC-14: Large, laptop/zoom, and narrower supported layouts prioritize chat and adapt
  panels/overlays without page horizontal overflow or a mobile-native redesign.
- AC-15: Pipeline, Opportunity detail, Notifications, and Inbox use one approved
  internal deep-link/navigation contract for exact conversation and Opportunity context.
- AC-16: Keyboard, focus, names, live-region restraint, non-color state communication,
  dialog behavior, contrast, targets, and reduced-motion behavior satisfy CRM-018/WCAG
  requirements.
- AC-17: The Inbox avoids per-row CRM enrichment, full-list polling reloads,
  per-message status requests, unnecessary typing-time rerenders, and unmeasured
  virtualization or state-library complexity.
- AC-18: Light, Dark, and System themes use CRM-018 semantic tokens, IBM Plex Sans,
  FAA neutral surfaces, selective warm yellow, and no WhatsApp visual cloning.

## Open decisions

1. **Human conversation templates are not exposed by CRM-006.** The Meta provider can
   list and send templates internally, but the authenticated CRM API has no endpoint
   to list usable human-conversation templates or submit a typed template send;
   CRM-011's available endpoint is explicitly marketing Broadcast-only. Before a
   blocked-window template picker can be implemented, approve a contract covering
   eligible template variants, safe content/parameter preview, validation, message
   persistence identity, and idempotent send behavior.
2. **Conversation summary lacks a latest-message preview.** `GET /conversations` and
   its changes projection currently omit a safe preview field. Add an authoritative,
   privacy-reviewed summary projection (or explicitly remove this product requirement)
   before Inbox rows can display previews without forbidden per-conversation message
   requests.
3. **Cross-workspace deep-link representation is not finalized.** The current frontend
   router has no stable route/query/state contract to select an exact conversation from
   CRM-019/CRM-020 or to return safely to its origin. Approve one typed, route-facing
   internal navigation representation shared with CRM-019, CRM-020, and CRM-022 before
   implementing those handoffs.

## Follow-up / future specs

- An approved human-template API/UI contract after Open decision 1 is resolved.
- Customer-resolution workflow only if a backend contract is explicitly approved.
- Message search, realtime transport, audio/video, or other messaging capabilities only
  through separately approved specs.
