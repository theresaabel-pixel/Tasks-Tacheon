# Task 1: Product Scoping — Marketing Performance Dashboard

## What I Was Asked to Do

Scope an internal tool that helps a marketing team answer one recurring question:
"How is our marketing performing across channels right now, and where should we focus?"

The constraint: the team does not change their tools or workflows.
Whatever is built has to fit around what already exists.

---

## The Decisions I Made and Why

### 1. The primary user is the internal analyst, not the client

The problem described is an internal one. Someone on the team is manually pulling
data and stitching together an answer. That is the pain to fix first.

Building for clients at the same time would mean designing for two different levels
of trust, polish, and access control simultaneously. That is how v1 becomes unfocused.
Client-facing is a natural v2 once the internal version is trusted and stable.

### 2. The tool is a dashboard, not a report generator or digest

A dashboard is always-on. No one has to remember to run it or request it.
It makes the answer consistent — same numbers, same format, every time someone looks.
It removes the dependency on any one person having the context to pull it together.

These three properties directly address every pain point in the brief.

### 3. The core question is about underperformance, not just performance

"How are we doing" is too vague to act on.
"Which channels are off target and by how much" gives the analyst something to do
with the answer.

This means the tool needs two things: actual data and target data.
Targets are set by the team, not inferred by the tool.
The tool surfaces deviation. Humans set expectation. That boundary matters.

### 4. v1 covers paid ads and web traffic only

Google Ads, Meta Ads, and Google Analytics.
These are the most common tools in a marketing stack and directly answer the question.

Email, SEO, and organic channels are out of scope for v1.
Not because they are unimportant, but because expanding the data surface before the
core pipeline is stable and trusted is how tools accumulate technical debt fast.

### 5. No AI layer in v1

The question is specific enough that a well-designed dashboard answers it without
a chat interface or generated recommendations.

AI adds complexity and requires the tool to already be trusted before its output
can be acted on. Build the trust first. Add intelligence on top of it in v2.

---

## What Is In Scope for v1

- Dashboard showing actual vs target per metric per channel
- Channels: Google Ads, Meta Ads, Google Analytics
- Metrics: spend, clicks, conversions, CPC, sessions, goal completions
- Visual flags for underperforming and overperforming metrics
- Data refresh on a daily cadence
- Targets set manually by the analyst in a config file or spreadsheet
- Data source label and last-refresh timestamp on every view

---

## What Is Explicitly Out of Scope for v1

| Feature | Reason excluded |
|---|---|
| Client-facing view | Different trust and polish requirements. Internal first. |
| AI recommendations | Requires trust before advice. Trust comes first. |
| Attribution modelling | Technically complex, not needed for the core question |
| Email / SEO / organic | Expand after paid + web pipeline is stable |
| Alerting / notifications | Useful in v2 once the dashboard habit has formed |
| Historical trend analysis | v1 answers right now. Trends are v2. |

---

## What the Tool Needs to Work

1. A data pipeline pulling from ad platforms and GA on a schedule
2. A targets layer — a spreadsheet or config file the team controls
3. A display layer — a BI tool they already have, or a lightweight internal view
4. A human owner — someone who maintains targets and notices when data looks wrong

Without the owner, the tool goes stale and gets ignored.
That is not a product problem. It is an organisational one to solve alongside the build.

---

## What I Would Revisit With More Time

- **Talk to the analysts who do this manually today.** One real conversation would
  sharpen the metric definitions and the meaning of "underperforming" more than
  any amount of scoping from the outside.

- **Understand what BI tooling the team already has.** Looker, Metabase, Notion,
  a simple web app — the display layer decision should follow what already exists,
  not introduce something new.

- **Define the targets-setting process before building the comparison logic.**
  The tool is only as useful as the targets it compares against. If there is no
  agreed process for setting them, that needs to be solved first.

- **Validate the data sources.** I assumed Google Ads and GA because they are
  the most common. If the team uses different platforms the structure holds
  but the connectors change.

---

## Files in This Folder

| File | What it is |
|---|---|
| `product-brief.md` | Full written spec: problem, user, scope, trust, data sources, decisions |
| `flow-diagram.md` | End-to-end flow from data source to analyst, including edge cases |
| `README.md` | This file — decisions, reasoning, and what I would revisit |