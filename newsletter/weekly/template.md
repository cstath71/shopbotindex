# ShopBot Index weekly email: fixed copy (use for every Monday draft)

The weekly routine drafts the email from `data/changes-latest.json` and the build output. Use these fixed lines so every issue carries the current messaging. Use only numbers from the crawl; never invent any.

- **From:** ShopBot Index <hello@shopbotindex.com> · **Reply-to:** hello@shopbotindex.com
- **Subject:** `ShopBot Index {crawl_date}: {joined} joined, {left} left` (or, if nobody joined or left: `ShopBot Index {crawl_date}: what online stores tell AI shopping agents`)
- **Preheader:** `This week's index of what online stores tell AI shopping agents: who started or stopped publishing a UCP profile.`
- **Header line (under the logo / "ShopBot Index"):** `The weekly index of what online stores tell AI shopping agents`
- **Intro (first paragraph):**
  `This week we checked {n_retailers} retailers and stores ({n_sites} websites) to see whether they publish the profile AI shopping agents read (a UCP profile). {ucp_total} do. No profile doesn't mean AI agents can't shop there.`
- **Body:** joined / left / couldn't check this time / capability changes, as today. Each store links to its `https://shopbotindex.com/store/<slug>.html` page.
- **Footer:**
  `ShopBot Index: the weekly index of what online stores tell AI shopping agents · https://shopbotindex.com · How we measure: https://shopbotindex.com/methodology.html · Follow on X: https://x.com/ShopBotIndex`
  `You're getting this because you subscribed at shopbotindex.com. Unsubscribe: {{{RESEND_UNSUBSCRIBE_URL}}} · Privacy: https://shopbotindex.com/privacy.html`

Until five-signals ships and Release 2 adds its change types, don't mention agent tools, AI rules in robots.txt, llms.txt / AI guidance files or product data.
Never say a store "supports", "officially supports" or "blocks" AI agents, or that agents can or can't buy there.
