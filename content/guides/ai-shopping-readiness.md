# AI shopping readiness: what agents check on a store

In the ShopBot Index crawl of 9 November 2026, a store's readiness for AI shopping agents was not one file but several public signals. 951 of 2,225 stores we could check publish a UCP profile (42.7%). 216 of 1,305 publish an llms.txt file (16.6%). 279 of 2,075 stores whose robots.txt we could read have rules that name an AI crawler (13.4%). 161 of 271 have schema.org Product markup on a product page we fetched (59.4%). 1 of 1,270 publishes an ACP discovery file. Each of these is a declaration a store makes in public. None of them is proof that an agent can complete a purchase, and ShopBot Index does not test purchases.

## What AI shopping agents look at on a store

An AI shopping agent, or the crawler behind an AI assistant, can read a store's public files without logging in. The ShopBot Index crawler reads the same kinds of files and records what it finds:

- `/robots.txt`: which crawlers the store asks to stay out, including AI crawlers such as GPTBot.
- `/.well-known/ucp`: a UCP profile, if the store publishes one.
- `/.well-known/acp.json`: an Agentic Commerce Protocol discovery file.
- `/llms.txt` and `/agents.md`: plain notes written for AI assistants and agents.
- `/.well-known/ai-catalog.json`: an AI catalog file.
- The home page and one product page, to look for schema.org Product markup.
- When a UCP profile names an MCP endpoint, one read-only request asking that endpoint for its tools list.

Each figure below counts stores, not websites. A store counts once even when we checked several of its country sites. A store enters a share only when we got a definite answer for that signal. Refusals, errors and checks we did not reach are left out, because a refusal is not "no". That is why the denominators differ from signal to signal. We track 2,854 stores. These are the stores in our list, not a random sample of all retail.

## UCP profile

A Universal Commerce Protocol (UCP) profile is a JSON file at `/.well-known/ucp` that lists the services, capabilities and payment handlers a store declares. In the 9 November 2026 crawl, 951 of 2,225 stores we could check publish a UCP profile (42.7%). That includes 841 of 1,042 Shopify stores (80.7%) and 16 of 255 big retailers (6.3%). 947 of the 951 declare checkout. A profile is a declaration, not proof that checkout works. See [what a UCP profile is](https://shopbotindex.com/guides/what-is-a-ucp-profile/) and [which stores declare UCP checkout](https://shopbotindex.com/which-stores-declare-ucp-checkout/).

## ACP discovery file

The Agentic Commerce Protocol (ACP) is the protocol OpenAI has described for merchants sharing catalogs for product discovery in ChatGPT. Our crawler looks for a discovery file at `/.well-known/acp.json`. In the 9 November 2026 crawl, 1 of 1,270 stores we could check publishes one (0.1%): alphonsomango.in. 1,584 stores were left out, 1,139 of them because the request was refused. ACP can also run through channels a public crawler cannot see, so a missing file does not mean a store has no ACP integration. [ACP signal page](https://shopbotindex.com/signals/acp/).

## llms.txt and AGENTS.md

llms.txt is a proposed Markdown file at `/llms.txt` with notes for AI assistants about the site. In the 9 November 2026 crawl, 216 of 1,305 stores we could check publish one (16.6%), including 46 big retailers such as Etsy, Target Corporation, Zalando and Shein. AGENTS.md, a similar file for agents, was found at 31 of 1,248 stores (2.5%). An AI catalog file at `/.well-known/ai-catalog.json` was found at 3 of 1,263 stores (0.2%). [llms.txt signal page](https://shopbotindex.com/signals/llms-txt/).

## MCP endpoints

MCP (Model Context Protocol) lets an agent ask a server which tools it offers, such as product search or checkout. We only look for an MCP endpoint named in a store's UCP profile. In the 9 November 2026 crawl, 945 of 2,466 stores we could check name an MCP endpoint in their UCP profile (38.3%). Only 8 of those 945 endpoints returned a tools list when we asked. 924 answered with HTTP 422 and no tools list, 11 refused, and 2 gave other errors. Seven of the eight that returned tools are Wix endpoints, and the tools listed include catalog search, product lookup and checkout steps. Naming an endpoint is a declaration. A tools list shows the endpoint answered, not that a purchase works. [MCP signal page](https://shopbotindex.com/signals/mcp/).

## robots.txt rules for AI crawlers

robots.txt is where a store states which crawlers it wants to keep out. In the 9 November 2026 crawl, 279 of 2,075 stores whose robots.txt we could read have rules that name an AI crawler (13.4%). 100 of the 2,075 disallow the whole site for GPTBot (4.8%), counting 4 that allow some paths back. Other crawlers asked to stay out of the whole site: ClaudeBot at 87 stores, Google-Extended at 77, ChatGPT-User at 12 and PerplexityBot at 10. 7 stores have a wildcard rule that disallows the whole site for every crawler, and 75 publish a Content-Signal line (3.6%).

How three large marketplaces treat AI crawlers, in the robots.txt we could read:

- **Amazon** asks GPTBot, ChatGPT-User, OAI-SearchBot, ClaudeBot, Claude-User, Claude-SearchBot, PerplexityBot, Perplexity-User and Google-Extended to stay out of the whole site.
- **eBay** disallows the whole site for GPTBot, ClaudeBot and PerplexityBot except some paths, and disallows some paths for ChatGPT-User, OAI-SearchBot, Claude-User and Claude-SearchBot.
- **Walmart**'s robots.txt does not name GPTBot or any of the other AI crawler tokens we record.

A robots.txt rule is the site's stated wish. It is not a technical block we tested. [AI crawler rules signal page](https://shopbotindex.com/signals/ai-bots-robots/).

## Product data

Agents need prices, currency and stock to compare products. Our crawl does not see product feeds a store sends privately to an AI assistant. It checks one thing in public: schema.org Product markup on one product page. In the 9 November 2026 crawl, 161 of 271 stores we could check have Product markup on the product page we fetched (59.4%), and 141 of them include price, currency and availability. We could not reach a product page for 2,583 stores, so this is not a rate for all retail. [Product data signal page](https://shopbotindex.com/signals/product-data/).

## Payment handlers

A UCP profile can list payment handlers, the ways an agent could pay. Of the 951 stores that publish a UCP profile, 270 declare Google Pay, 263 declare Shop Pay, 263 declare the Shopify card handler and 1 declares Klarna. 270 declare at least one handler and 681 declare none. A declared handler is a line in the profile, not proof that an agent can pay. [Payment handlers](https://shopbotindex.com/payment-handlers/).

## Businesses in ChatGPT

OpenAI launched Businesses in ChatGPT in beta on 10 November 2026. A business can claim its profile in Business Hub, add product feeds and see insights on mentions and website clicks. A claim is private to the business and OpenAI, so ShopBot Index cannot see who has claimed a profile, and claims are not in our crawl. A claim and the public files above are separate channels, and one does not replace the other. Read [Businesses in ChatGPT: what it means for online stores](https://shopbotindex.com/guides/businesses-in-chatgpt/).

## Bot protection and why some shares are small

1,181 of 2,429 stores we could check had bot protection that refused our crawler (48.6%). A refusal of our crawler says nothing about whether shoppers or AI agents can use the site, but it explains why the llms.txt, ACP and product data shares rest on fewer stores than the UCP share. [Bot protection signal page](https://shopbotindex.com/signals/bot-protection/).

## How to check your store

1. Look up your domain on [Check your store](https://shopbotindex.com/check.html). It reads our latest weekly crawl, not your live site, and the store page lists every signal above.
2. Open `https://your-domain/.well-known/ucp`. A JSON document means you publish a UCP profile. Check which capabilities and payment handlers it declares.
3. Open `https://your-domain/robots.txt` and search for GPTBot, OAI-SearchBot, ChatGPT-User, ClaudeBot and PerplexityBot. Make sure the rules say what you intend.
4. Open `https://your-domain/llms.txt` and `https://your-domain/.well-known/acp.json` to see whether you publish them.
5. View the source of a product page and look for `"@type": "Product"` with an Offer that has price, priceCurrency and availability.
6. If you are eligible, consider claiming your business in ChatGPT Business Hub. That is a separate step from everything above.

## Frequently asked questions

### Is ShopBot Index only about UCP?

No. UCP is one signal. In the crawl of 9 November 2026 we also recorded ACP discovery files, llms.txt, AGENTS.md, MCP endpoints, robots.txt rules for AI crawlers, Product markup, payment handlers and bot protection for 2,854 tracked stores.

### How many stores block GPTBot in robots.txt?

In the ShopBot Index crawl of 9 November 2026, 100 of 2,075 stores whose robots.txt we could read disallow the whole site for GPTBot (4.8%). Amazon asks GPTBot to stay out of the whole site. eBay disallows the whole site for GPTBot except some paths. Walmart's robots.txt does not name GPTBot. A robots.txt rule is a stated wish, not a technical block we tested.

### How many online stores have an llms.txt file?

In the ShopBot Index crawl of 9 November 2026, 216 of 1,305 stores we could check publish an llms.txt file (16.6%). Stores that refused our request are left out of the share, because a refusal is not "no".

### How many stores have a working MCP server for AI agents?

In the ShopBot Index crawl of 9 November 2026, 945 of 2,466 stores we could check name an MCP endpoint in their UCP profile (38.3%). Only 8 of those endpoints returned a tools list when we asked. A tools list shows the endpoint answered, not that a purchase works.

### Does publishing a UCP profile mean AI agents can buy from my store?

No. A UCP profile is a declaration the store publishes. It is not proof that checkout works. In the crawl of 9 November 2026, 951 of 2,225 stores we could check publish a UCP profile (42.7%), and 947 of them declare checkout. ShopBot Index does not test purchases.

### Does ShopBot Index see product feeds or ChatGPT Business Hub claims?

No. We cannot see product feeds sent privately to AI assistants or claims made in ChatGPT Business Hub. We only check public schema.org Product markup on one product page. In the crawl of 9 November 2026, 161 of 271 stores we could check had that markup (59.4%).

