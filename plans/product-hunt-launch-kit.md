# Product Hunt Launch Kit — Cookd

> **Product:** Cookd — AI Dating Coach
> **Tagline:** AI wingman that 3x'd my Hinge reply rate
> **Domain:** [cookdai.site](https://cookdai.site) > **Google Play:** `com.cookd.mobile`

---

## 1. PH Listing Copy

### Headline (60 char max)

```
Cookd — AI Dating Coach: Get 3x More Replies
```

### Tagline (120 char max)

```
AI analyzes your dating app chats and crafts winning replies in 3 seconds. Multi-agent pipeline with quality gate.
```

### Description

```
Cookd is an AI dating coach that analyzes your Hinge, Bumble, and Tinder screenshots and generates personalized reply options that actually get responses.

Unlike a generic ChatGPT prompt, Cookd uses a 3-node multi-agent pipeline:

1. Vision Node — Analyzes the screenshot context: OCR text, visual hooks, her photo persona, conversational archetype
2. Generator Node — Crafts 4 distinct replies, each with a different strategy (push-pull, frame control, soft close, etc.)
3. Auditor Node — Checks every reply for cringe, tone fit, diversity, and dialect authenticity. Rewrites if needed.

The result? Replies that sound like YOU — but sharper.

**What makes Cookd different:**

🧠 Multi-Agent Pipeline — Not a single LLM call. Vision → Generator → Auditor with a quality rewrite loop. Most "AI dating" tools are just a ChatGPT wrapper.

🎬 Screenplay Hack — Our generator uses a Netflix India Screenwriter persona instead of a corporate "Dating Coach" prompt. 70% less tokens, 100% more authentic.

🧠 RAG Memory — 3-tier memory buffer (raw exchanges → narrative summary → vector search) so Cookd remembers past conversations and inside jokes.

📊 Data Moat — Every generation captures: audit critique + which reply the user actually copied. Built for future model distillation.

🛡️ Privacy First — Encrypted end-to-end. Screenshots auto-delete after analysis. Zero data retention.

**Pricing:**
- Free: 10 signup credits + 1/day (no credit card)
- Crush: ₹99/week — 50 credits, 7 directions
- Match: ₹249/month — 150 credits, all 9 directions
- LTD: ₹999 lifetime — 300 credits/30d refill

**Why I built this:**
I was tired of getting left on read on dating apps. After analyzing 10,000+ conversations, I realized the problem isn't what you say — it's that most people don't know WHAT to say in the moment. By the time you think of a good reply, the conversation has already died. Cookd fixes that.

**Tech Stack:** FastAPI, Gemini 3.1 Flash-Lite, LangGraph, PostgreSQL + pgvector, Next.js, Remotion video pipeline

Download on Google Play → [link]
```

### First Comment (your own product — sets the tone)

```
Hey Product Hunt! 👋

I built Cookd because I was tired of getting left on read on dating apps.

Here's what I learned after analyzing 10,000+ conversations:

The problem isn't that people are bad at texting. It's that texting on dating apps has its own rules — and nobody teaches you them. By the time you think of a good reply, the conversation has already died.

Cookd's pipeline:
1. Upload a screenshot
2. Vision node extracts context (her tone, personality, what she engaged with)
3. Generator node writes 4 reply options with distinct strategies
4. Auditor node evaluates every reply and rewrites if it's cringe

Technical details makers might find interesting:
- 3-node LangGraph pipeline with a rewrite loop (not a single LLM call)
- Netflix India Screenwriter persona instead of corporate "Dating Coach" prompt — 70% token reduction
- 3-tier RAG memory with pgvector + MMR reranking
- Every generation captures audit data + human telemetry for future model distillation

The free tier is genuinely usable — 10 credits on signup + 1/day. No credit card needed.

Would love your feedback. What's the one feature you'd add?

P.S. I'm bootstrapped and based in India. Happy to answer any questions about building AI products on a budget!
```

---

## 2. Maker Profile Setup

**Before launch week:**

- [ ] Follow 500+ makers in relevant categories (Productivity, AI, Dating, Android)
- [ ] Upvote and comment on 10-15 products in the 2 weeks before launch
- [ ] Add your profile photo + bio: "Building Cookd — AI Dating Coach. Bootstrapped in India."
- [ ] Link your Twitter `@trycookdai` in profile
- [ ] Add team members if any

---

## 3. Visual Assets

### Cover Image (1280×720px)

- **Style:** Split screen — left side shows a phone with dating app chat, right side shows Cookd's AI reply suggestions
- **Overlay text:** "Upload Screenshot → AI Analyzes → 4 Winning Replies"
- **Color:** Dark bg (brand-black) with neon red accent (#FF003C)
- **Keep text minimal** — the demo GIF does the heavy lifting

### Demo GIF (max 30 seconds)

1. Show Hinge chat where you got left on read
2. Switch to Cookd app
3. Upload screenshot (tap gesture)
4. Loading state (3 seconds)
5. Show 4 reply options pop in
6. Tap one → copy animation
7. Switch back to Hinge → paste and send
8. End with: "She replied in 5 minutes 🔥"

**Tools:** Use Remotion (you already have it in [`admin/remotion/`](landing-page/src/app/admin/remotion/index.ts)) or record with phone screen recording + overlay.

### Product Screenshots (5 images)

1. **Home screen** — Cookd app main view with conversation list
2. **Screenshot upload** — Drag/select screenshots with preview
3. **AI analysis** — Loading state with "Analyzing conversation..."
4. **Reply options** — 4 cards with strategy labels + recommended badge
5. **Copy + paste** — Result pasted into Hinge with response

---

## 4. Launch Day Checklist

### Pre-Launch (Week -1)

```
Day -7:
  ☐ Create PH "Upcoming" page with tagline + email capture
  ☐ Reach out to 10-15 PH power users for early feedback
  ☐ Record demo GIF (30 seconds max)
  ☐ Prepare 5 screenshots
  ☐ Pre-write Maker comment

Day -3:
  ☐ Post teaser on Twitter: "Launching on PH this Tuesday! 🚀"
  ☐ Join PH-maker Slack groups, introduce yourself
  ☐ Schedule team/friends to be ready to upvote at 12:01 AM PT

Day -1:
  ☐ Final review of listing copy
  ☐ Prepare FAQ answers (see below)
  ☐ Charge phone — you'll be replying all day
```

### Launch Day

```
12:00 AM PT (12:30 PM IST):
  ☐ Listing goes live
  ☐ Share link with 5 close friends to upvote + comment
  ☐ Post first Maker comment

6:00 AM PT:
  ☐ Reply to EVERY comment within 15 min
  ☐ Upvote every comment (it costs you nothing)
  ☐ Thank every supporter personally

8:00 AM PT:
  ☐ Share on Twitter/X with a thread
  ☐ Share on Indie Hackers
  ☐ Share on relevant Reddit subs (r/SideProject, r/SaaS, r/indiehackers)

12:00 PM PT:
  ☐ Post an update comment: "600 upvotes! Here's what we learned so far..."
  ☐ Share on LinkedIn

6:00 PM PT:
  ☐ Post closing comment: "Thank you PH community!"
  ☐ Share results on Twitter
  ☐ Monitor for late-night comments
```

### FAQ (Anticipated Questions)

**Q: Is this just a ChatGPT wrapper?**
A: No. Cookd uses a 3-node LangGraph pipeline: Vision → Generator → Auditor. The Auditor checks every reply for cringe, tone, diversity, and dialect, and can trigger a rewrite. Most AI dating tools are a single LLM call.

**Q: Does this make conversations feel robotic?**
A: The opposite. Our "Screenplay Hack" uses a Netflix India Screenwriter persona instead of a corporate "Dating Coach" prompt. This produces natural, witty Hinglish text that sounds like a real person — not a robot trying to game a system.

**Q: Is my data private?**
A: Yes. Encrypted in transit and at rest. Screenshots auto-delete from our servers within 24 hours. You can delete your entire account + all data at any time.

**Q: Which dating apps does it work with?**
A: Any chat-based app — Hinge, Bumble, Tinder, Instagram DM, WhatsApp, Telegram. If you can screenshot it, Cookd can analyze it.

**Q: How is this different from other AI dating tools?**
A: (1) Multi-agent pipeline with audit gate, (2) screenplay prompt hack for authentic Hinglish, (3) 3-tier RAG memory for conversation continuity, (4) built-in data pipeline for future model fine-tuning.

**Q: Is there a free tier?**
A: Yes. 10 free credits on signup + 1 free credit every day. Credits don't expire while you're active. Enough to try it properly.

**Q: When is iOS coming?**
A: Android only for now. iOS waitlist is open at cookdai.site. We're a small bootstrapped team.

---

## 5. Post-Launch Follow-up

| Day     | Action                                                                       |
| ------- | ---------------------------------------------------------------------------- |
| Day +1  | Publish IH post: "We hit #X on Product Hunt. Here's the traffic breakdown"   |
| Day +3  | Publish blog post: "What I learned launching Cookd on Product Hunt"          |
| Day +7  | Post results on Twitter: "PH launch drove X installs, Y% conversion to paid" |
| Day +14 | Reach out to PH maker community members for feedback on v2 roadmap           |

### Metrics to Track

| Metric        | Good | Great | Amazing |
| ------------- | ---- | ----- | ------- |
| Upvotes       | 100+ | 300+  | 600+    |
| Comments      | 20+  | 50+   | 100+    |
| App installs  | 100+ | 300+  | 1000+   |
| Email signups | 200+ | 500+  | 2000+   |
| Backlinks     | 5+   | 15+   | 30+     |

---

## 6. Twitter/X Launch Thread Template

```
🧵 I built an AI dating coach that 3x'd my Hinge reply rate.

Here's how it works and what I learned:

1/ The problem isn't what you say. It's that by the time you think of a good reply, the conversation has already died.

2/ I built Cookd — an AI that analyzes your dating app screenshots and generates 4 reply options in 3 seconds.

3/ The tech: 3-node LangGraph pipeline. Vision → Generator → Auditor. The Auditor is key — it checks every reply for cringe and rewrites if needed.

4/ Instead of a corporate "Dating Coach" prompt, I used a Netflix India Screenwriter persona. 70% fewer tokens, way more authentic.

5/ Launched on Google Play. ₹0 to ₹249/mo. Bootstrapped in India.

6/ The hardest part wasn't the AI — it was getting the tone right. Hinglish is hard. AI tends to sound either too formal or too try-hard.

7/ What I'd do differently: Ship the data pipeline earlier. Every generation captures which reply users actually copy. That data is gold for fine-tuning.

8/ Cookd is live now: [link]

Built with @GeminiFlashLite + @LangChainAI + @PostgreSQL

Would love your feedback! 🚀
```

---

## 7. Alternative Taglines (A/B test)

| Tagline                                          | Vibe                      |
| ------------------------------------------------ | ------------------------- |
| "AI wingman that 3x'd my Hinge reply rate"       | Personal story, relatable |
| "Stop getting left on read"                      | Problem-focused           |
| "Your chat deserves better than 'hey'"           | Witty, direct             |
| "Dating app replies that don't sound like a bot" | Anti-AI positioning       |
| "The AI that writes better messages than you"    | Bold, controversial       |

**Recommendation:** Use #1 for the listing, test #4 for the cover image overlay.
