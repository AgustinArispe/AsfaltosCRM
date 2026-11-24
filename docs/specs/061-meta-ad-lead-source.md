# CRM-061 — Meta ad attribution for WhatsApp leads

Status: Implemented
Owner: FAA CRM team
Last updated: 2026-11-24
Implementation commit: 4e49261

## Request and scope

Add the Meta commercial source for leads arriving through WhatsApp from an ad,
identified by the Anuncio context in the user's example. Ordinary WhatsApp and
web intake keep their own source. Use the signed incoming message's referral
metadata, independent of the customer's greeting or product question.

## Attribution and lifecycle

- A newly created inbound opportunity is META when its initial message has
  referral.source_type=ad. Missing optional ad ID, URL or click ID does not prevent
  attribution. Other messages create WHATSAPP opportunities.
- Persist the referral type, source ID, source URL and optional ctwa_clid on the
  message. This is attribution evidence, separate from its text or attachment.
- WHATSAPP and META share the WhatsApp intake lifecycle. Reuse one open WhatsApp
  channel opportunity per customer, preserving its original source and inquiry.
  Later messages and referrals do not relabel an existing opportunity. A message
  after closure can start a new opportunity with its own initial attribution.
- Maintain the channel uniqueness rule in creation, reopening and regression,
  with ordered customer locking and a PostgreSQL unique partial index.
- Preserve deduplication and reject conflicting replay evidence. An ambiguous or
  deleted customer still requires identity review before automatic creation.
- When identity review delays creation, use the first pending inbound inquiry
  after the previous channel case ended. Automatic and CRM chat creation both
  retain that initial inquiry's attribution once identity is resolved.
- Meta is visible in every existing source label, filter and report. Web, Manual
  and Instagram remain readable and filterable.

## Storage and rollout

Add META to lead_source_enum and nullable referral columns to whatsapp_messages.
Track whether a message was received by the referral-aware implementation so a
genuine retry of a legacy message can complete its missing evidence, retaining its
existing opportunity source. Conflicting evidence on captured messages is rejected.
Expand the WhatsApp channel unique index to include META. Existing records retain
their stored source because previous code discarded referral data. Downgrade must
protect stored attribution and commercial history.

## Acceptance criteria

- AC-01 Signed ad webhook creates META, ordinary greeting including the same text
  creates WHATSAPP, and web intake creates WEB. Ads without ctwa_clid are supported.
- AC-02 Follow-up messages reuse the case and initial attribution in either
  organic/ad order. Closure permits a new correctly attributed case.
- AC-03 Replays and concurrent mixed ad/organic delivery create one active case.
  Reopening/regression cannot introduce a second WhatsApp channel case.
- AC-04 Card, detail, customer history, WhatsApp context, source filters and metrics
  support Meta. Source counts, volumes and losses preserve their normal contracts.
- AC-05 Upgrade preserves prior data, protects index uniqueness and rejects unsafe
  downgrade. Existing quality checks, coverage and Compose health pass.

## Non-goals

Text-based campaign guessing, automatic historical reclassification, campaign
management, conversions sent to Meta and changes to customer identity matching.

## Reference

https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/reference/messages/text

## Open decisions

None.

## Verification

- Local backend gates pass with 563 tests and 93.38 percent coverage, strict typing,
  Ruff, lock reproducibility, dependency audit and Alembic model/head checks.
- Local frontend gates pass with 300 tests, production build and zero audit findings.
- Signed Meta webhook tests exercise ad and ordinary delivery through the normal
  HTTP endpoint. Referral mapping covers text, image, audio and document messages.
- Tests cover optional click IDs, unchanged initial attribution, deduplication,
  mixed concurrent delivery, identity review, closing, reopening and volume reports.
- Migration tests preserve earlier rows and enforce shared channel uniqueness.
  Canonical local Compose is healthy and vendor Meta filters return HTTP 200.
- Browser acceptance adds source selection in Pipeline, Dashboard and Ganadas.
  Publish main only after the complete GitHub Quality run passes for this tree.
