# NotebookLM Tracker — News, API & Tool Abilities

> **Last updated:** 2026-06-05  
> **Maintained by:** lookBOOK project  
> **Purpose:** Living document tracking NotebookLM capabilities, API status, pricing, and integration opportunities relevant to animation/book-to-video pipelines.

---

## TL;DR — Current State (June 2026)

| Surface | Status | Best For |
|---|---|---|
| **NotebookLM Web App** | Active — 6 major updates in 6 months | Manual research, audio overviews, slide decks |
| **NotebookLM Enterprise API** | Official Google Cloud docs available | Teams inside Google Cloud Enterprise |
| **Google Podcast API** | Deprecated — no new allowlists | Existing customers only |
| **AutoContent API** | Public REST API, active | Developers needing batch podcast/content generation |
| **lookBOOK Integration** | Planned — audio overview → shot graph | Animation pipeline enrichment |

---

## 1. Feature Changelog (2025 → 2026)

### March 2026 — Studio Expansion
- **Cinematic Video Overviews** — Documentary-quality visual narratives powered by Gemini 3 + Veo 3 (Ultra plan only)
- **Slide Revisions on Mobile** — Per-slide feedback without full regeneration
- **10 Infographic Styles** — Sketch Note, Kawaii, Professional, Scientific, Anime, Clay, Editorial, Instructional, Bento Grid, Bricks
- **EPUB Support** — Upload eBooks directly as sources
- **PPTX Export** — Download slide decks as PowerPoint
- **Improved Flashcards & Quizzes** — Progress saved, shuffle, "Got it/Missed it" tracking
- **Chat Artifact Creation** — Generate Audio/Video Overviews directly from chat

### February 2026 — Slide Editing + Export
- **Prompt-Based Slide Editing (Pencil UI)** — Target specific slides with revision instructions
- **PPTX Download** — Initial PowerPoint export launch
- **Gemini 3.1 Pro** — Engine upgrade

### January 2026 — Smarter Chat
- **Custom Chat Personas** — Set goals/voice/role per notebook (teacher, coach, game master)
- **Saved Conversation History** — Private, resumable chats
- **1M-Token Context for All Plans** — Free tier included; 6× multi-turn capacity
- **Deeper Source Insights** — Automatic multi-angle exploration

### December 2025 — Gemini 3 + Data Tables
- **Gemini 3 Engine** — Better reasoning, multimodal understanding, less hallucination
- **Data Tables** — Structured tables from documents; one-click export to Google Sheets
- **Notebook → Gemini Connection** — Use notebooks as sources inside Gemini app

### November 2025 — Deep Research + Sources
- **Deep Research Agent** — Autonomous research: plan → search → compile citation-backed report (free: 10 sessions/month)
- **Word (.docx) & Sheets as Sources** — Native upload without PDF conversion
- **Discover Sources** — Web + Drive search integration

### October 2025 — 1M Context + Goals
- **1M-Token Context Window** — Entire book-length collections in one conversation
- **Custom Goals per Notebook** — Orient AI responses toward project needs
- **Four-Tier Pricing** — Free / Plus (~$14) / Pro ($19.99) / Ultra ($249.99)
- **Mobile App Camera** — Quick image-to-source upload

---

## 2. API Landscape (June 2026)

### Official Google APIs

#### NotebookLM Enterprise API
- **Status:** Officially documented in Google Cloud
- **Access:** Requires Google Cloud Enterprise + NotebookLM Enterprise
- **Coverage:** Notebook, source, and audio overview workflows
- **Best for:** Organizations already in Google Cloud ecosystem
- **Docs:** Google Cloud official documentation

#### Google Podcast API (Standalone)
- **Status:** Deprecated — documented but not accepting new customers
- **Access:** Existing allowlisted customers only
- **Recommendation:** Do not build new integrations here

### Third-Party Alternatives

#### AutoContent API
- **Status:** Public REST API, actively maintained
- **Pricing:** Per-request pricing, API key self-serve
- **Features:** Two-host podcasts, transcripts, summaries, FAQs, study guides, timelines, videos, infographics, slide decks
- **Sources:** Websites, PDFs, YouTube, raw text, Reddit/X feeds
- **Best for:** Developers needing batch generation, webhooks, SDKs
- **Docs:** docs.autocontentapi.com

#### NotebookLM MCP (Model Context Protocol)
- **Status:** Community/emerging
- **Use case:** Agent-ready workflows (Codex, Claude Code)
- **Pattern:** Create/status orchestration for long-running jobs

---

## 3. Pricing & Limits (2026)

| Tier | Price | Notebooks | Sources | Key Limits |
|---|---|---|---|---|
| **Free** | $0 | 100 | 50 | 50 chats/day, standard video only |
| **Plus** | ~$14/mo | — | — | Higher usage limits |
| **Pro** | $19.99/mo | — | 300 | Advanced features |
| **Ultra** | $249.99/mo | — | — | Cinematic Video, watermark-free |
| **Student** | $9.99/mo | — | — | Discounted Pro tier |
| **Enterprise** | $9/license/mo | — | — | Admin controls, security |

**Audio Overview Limits:**
- 2025 cap: ~20 minutes
- 2026 cap: ~30 minutes (tier-based; Plus/Pro/Ultra get higher limits)
- Generation time: Under 5 minutes for max-duration content

---

## 4. Tool Abilities Deep Dive

### Audio Overviews
- Two-host conversational podcast from sources
- Interactive: ask questions to AI hosts during playback
- Mobile app with offline playback
- Length: up to 30 min (2026)

### Video Overviews
- **Standard:** Narrated slideshow with simple visuals (all plans)
- **Cinematic:** Documentary-quality with fluid animations (Ultra only)
- Length: typically under 5 minutes

### Data Tables
- Extract structured data from unstructured text
- Sort, filter, export to Google Sheets
- Use cases: competitive analysis, curriculum mapping, literature reviews

### Deep Research
- Autonomous agent: plan → search hundreds of sources → compile report
- Citation-backed output
- Import results as notebook sources
- Free tier: 10 sessions/month

### Studio Tools
- **Slides:** Prompt-based editing, 10 infographic styles, PPTX/PDF export
- **Flashcards:** Difficulty levels, progress tracking, missed-card reruns
- **Quizzes:** Multiple-choice, grounded in sources, good for live events
- **Timelines:** Chronological event extraction
- **FAQs:** Automatic question generation from sources

### Source Types Supported
- PDF, TXT, Markdown
- Google Docs, Google Sheets
- Microsoft Word (.docx)
- EPUB (eBooks)
- YouTube transcripts
- Web pages
- Images (via mobile camera)
- Reddit / X (Twitter) feeds (via AutoContent API)

---

## 5. Integration Opportunities for lookBOOK

### Near-Term (M6 candidate)
1. **Audio Overview → Shot Graph** — Feed comic/manga page analysis into NotebookLM, generate audio overview, transcribe, parse into scene/shot structure
2. **Deep Research → World Bible** — Use Deep Research on source material to generate comprehensive world-building documents for animation projects
3. **Data Tables → Character Sheets** — Structured character attribute extraction from narrative text

### Medium-Term
4. **NotebookLM Enterprise API Bridge** — Enterprise customers can push lookBOOK analysis JSON directly into NotebookLM notebooks for team review
5. **Video Overview → Reference Board** — Cinematic Video Overviews as visual reference for animators
6. **Chat Personas → Director AI** — Custom personas ("animation director", "storyboard artist") to refine lookBOOK outputs

### API Wishlist (Google)
- Public REST API for audio/video generation without Enterprise requirement
- Webhook callbacks for async generation completion
- Source upload via API (not just Enterprise)
- Direct PPTX/MP4 download URLs from API

---

## 6. Quick Reference: Prompts That Work

### For Audio Overviews
```
"Generate a 10-minute two-host podcast discussing the narrative arc
of these comic pages. Focus on character motivation, scene transitions,
and emotional beats."
```

### For Cinematic Video
```
"Generate a Cinematic Video Overview of these sources. Focus on
[CHARACTER NAME]'s journey. Use a documentary narrative structure:
introduce the character, present key scenes, then synthesize the
character arc. Keep it under 5 minutes."
```

### For Data Tables
```
"Extract all characters from this source material into a structured
table with columns: Name, Role, Appearance Description, First Scene,
Key Motivation. Export to Google Sheets."
```

### For Deep Research
```
"Research the visual storytelling techniques used in [GENRE] comics
from 2010–2025. Focus on panel composition, color theory, and
transition styles. Compile a citation-backed report."
```

---

## 7. Resources & Links

- [Official NotebookLM](https://notebooklm.google.com)
- [Google Workspace Updates Blog](https://workspaceupdates.googleblog.com/)
- [NotebookLM Guide — Changelog](https://notebooklm-guide.com/notebooklm-updates/)
- [AutoContent API Docs](https://docs.autocontentapi.com)
- [Jeff Su — NotebookLM 2026 Review](https://www.jeffsu.org/notebooklm-changed-completely-heres-what-matters-in-2026/)

---

## 8. Update Log

| Date | Editor | Changes |
|---|---|---|
| 2026-06-05 | lookBOOK | Initial tracker created; June 2026 baseline |

> **To update this tracker:** Edit `docs/NOTEBOOKLM_TRACKER.md` and run `lookbook export-docs` to regenerate the HTML version.
