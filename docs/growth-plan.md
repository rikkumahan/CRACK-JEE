# CRACK-JEE growth plan

Written 2026-09-18. Goal stated by the user: make this genuinely spread —
"go viral," get real students using it, not just a polished personal repo.

This is a plan, not a decision — nothing here is built yet. Each phase
lists what's already true (verified, not assumed) and what's still open.

---

## Where this actually stands right now

Checked directly before writing this, not assumed:

- **Product**: live on PyPI (`crack-jee` 0.1.1), `uvx crack-jee` works,
  auto-updates on every launch (verified — `uvx` revalidates against
  PyPI's index each run), automated release pipeline on a version tag.
- **README**: has a designed banner, a beginner Quick Start (Claude
  Desktop + Qwen Desktop), a "How it works" infographic, a feature table.
- **GitHub repo metadata**: checked via the API — **no description, no
  topics, no homepage link set.** This is free, high-leverage discoverability
  GitHub's own search and "Explore" surfacing depends on, and it's
  currently empty.
- **PyPI package metadata**: `pyproject.toml` has no `keywords`, no
  `classifiers`, no `[project.urls]` (Homepage/Repository/Issues links).
  Same problem on PyPI's own search.
- **2 stars currently** — real signal, not zero, but no path yet for a
  stranger to discover this without already having the link.
- **No demo media anywhere** — no screenshot, GIF, or video of an actual
  conversation. Nobody installs a tool sight-unseen.

## The one thing to be honest about

The realistic adoption path for this product is narrower than "every JEE
student." It's an MCP server — it only works inside a chat app that
supports MCP (Claude Desktop, Qwen Desktop). Most JEE aspirants have
never heard of MCP and don't have either app installed. "Viral" here
more realistically means: viral *within* the slice of students (and,
maybe more so, their tech-savvy parents/siblings/tutors) who already use
Claude or a similar AI chat tool — and word-of-mouth from there. That's
still a real, growing audience, just not "every student in India."

Two ways to widen it later, not now (see "Not doing yet" below):
worth knowing they exist, wrong to build before there's any usage signal
that people want them.

---

## Phase 0 — Metadata and discoverability (cheap, no content needed)

Things that cost almost nothing and are pure upside. Some I can do,
some need your GitHub/PyPI account.

- [ ] **Add a GitHub repo description + topics** (needs your account —
  Settings on the repo page, or top-right "About" gear icon). Suggested
  topics: `mcp`, `mcp-server`, `jee`, `ai-tutor`, `education`, `claude`,
  `study-planner`, `bayesian-knowledge-tracing`. Description suggestion:
  "AI study coach for JEE aspirants — MCP server that finds mistake
  patterns across tests and verifies whether your study plan worked."
- [ ] **Set the repo homepage link** to `https://pypi.org/project/crack-jee/`.
- [ ] **Add `keywords` and `classifiers` to `pyproject.toml`** — I can do
  this directly. Keywords like `jee`, `mcp`, `education`, `study-planner`,
  `knowledge-tracing`; classifiers for `Topic :: Education`, `Intended
  Audience :: Education`, dev status. Also add `[project.urls]` pointing
  at the GitHub repo, PyPI page, and issue tracker.
- [ ] **Set a GitHub social preview image** (Settings → General → Social
  preview, 1280×640) so links shared on Twitter/WhatsApp/Reddit render a
  real image card instead of a blank box. Can reuse/crop the existing
  banner. Needs your account — I can generate the crop if you want.
- [ ] **Enable GitHub Discussions** on the repo (currently off) — gives
  early users a place to ask setup questions that isn't a GitHub Issue.

## Phase 1 — Proof (the actual blocker, needs you)

This is the single highest-leverage thing and the one I can't do myself
— I have no way to record a real usage session.

- [ ] **Record one real conversation** with the actual product: describe
  a test result, ask what to study, get a real plan, come back after a
  "next test" and show the before/after verification. Doesn't need to be
  polished — a raw screen recording of the actual coaching value landing
  is worth more than any written pitch.
- [ ] Turn that into: a **GIF in the README** (short, 15-30s, the "wow"
  moment — probably the recurring-mistakes catch or the closed-loop
  verification, since those are the two things a normal coaching report
  literally cannot do), and optionally a **longer video** for social posts.
- [ ] A **before/after example** in the README: paste an example of what
  a normal per-test report looks like next to what CRACK-JEE surfaces
  from the same data. Makes the pitch concrete instead of abstract.

## Phase 2 — Distribution (where the actual audience is)

Ranked by fit for this specific audience (JEE students + AI/dev crowd
who'd actually install an MCP server), not generic "post everywhere" advice.

1. **r/JEE, r/IndianAcademia, r/developersIndia** — the most direct-fit
   audience. A genuine "I built this for my sister, here's what it does"
   post (this is a real, sympathetic story — better than a sales pitch)
   with the demo GIF does better than a link-drop.
2. **Twitter/X** — the MCP/AI-tools crowd is active there; a short thread
   with the demo GIF, tagged with #MCP, reaches people who'd actually try
   installing something like this.
3. **Product Hunt** — MCP servers and dev tools do reasonably well there;
   needs the demo media from Phase 1 first, launches poorly without it.
4. **Show HN** (news.ycombinator.com) — technical audience, appreciates
   the "why BKT not a trained model" reasoning already in the README;
   again, needs the demo first.
5. **JEE-prep Telegram/WhatsApp groups, Instagram/YouTube Shorts** —
   highest raw reach for the actual student demographic, but also the
   hardest for a technical MCP-based tool to land in without the
   zero-setup barrier being solved first (see "Not doing yet"). Lower
   priority until Phase 3's wrapper question is answered either way.

None of these should happen before Phase 1's demo media exists — an
unproven link gets one look and gets scrolled past.

## Phase 3 — Social proof and retention

- [ ] **A "Star this repo" nudge** somewhere low-key in the README (not
  pushy) — GitHub's own trending/discovery algorithm weighs stars and
  recent star velocity, so this compounds with Phase 2's launches.
- [ ] **Testimonials section** once a few real people (starting with your
  sister, if she's comfortable) have used it — a real "this caught
  something my coaching institute never showed me" quote does more than
  any feature list.
- [ ] **A CHANGELOG or visible release history** — shows the project is
  actively maintained, which matters for a stranger deciding whether to
  trust installing something.

---

## Not doing yet (explicitly deferred, not forgotten)

- **A hosted/zero-setup version** (web app, browser extension) that
  doesn't need Claude Desktop or `uv` at all. This is the real fix for
  the "non-technical student" barrier, but it's a genuinely different
  product (needs hosting, auth, multi-student data isolation — the
  Supabase cloud-sync design already deferred in
  `docs/cloud-sync-design.md` for the same reason) — not something to
  build speculatively before there's usage signal justifying it.
- **Paid promotion / ads.** Not the right growth model for a free tool
  with no monetization and no team to run campaigns.
- **A Discord/community server.** Premature before there's an actual
  user base to populate one — GitHub Discussions (Phase 0) is the right
  size for now.

---

## Suggested order

Phase 0 is unblocked and cheap — can start immediately, mostly needs 10
minutes of your time on GitHub/PyPI settings plus me updating
`pyproject.toml`. Phase 1 (the demo) is the real gate: Phase 2's
distribution push is significantly weaker without it, so it's worth
doing before any public posting, even if Phase 0 happens in parallel.
