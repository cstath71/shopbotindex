# Businesses in ChatGPT: what it means for online stores

OpenAI launched Businesses in ChatGPT in beta on 10 November 2026. In Business Hub, a business can claim its profile, add product feeds with pricing and availability, and see aggregated insights on mentions, website clicks and discovery topics. Eligible ecommerce and online service businesses in the United States can also build a Business Agent. OpenAI says ChatGPT has 1.2 billion weekly users, and that it does not share ChatGPT conversations or Business Agent chats with businesses.

ShopBot Index cannot see who has claimed a ChatGPT profile. Claims, feeds and mention counts are not in our crawl. From the 9 November 2026 crawl, we can show how many stores already publish the public agent-readiness signals a crawler can fetch without a claim: 951 of 2,225 stores we could check publish a UCP profile (42.7%), including 841 of 1,042 Shopify stores (80.7%) and 16 of 255 big retailers (6.3%). A published profile is a declaration, not proof that agents can buy.

## What OpenAI announced

The [10 November 2026 announcement](https://openai.com/index/introducing-businesses-chatgpt/) says any eligible business in a place where ChatGPT is available can claim its organization, then, once verified, update key details and add self-service product feeds. Discovery topics are common themes across conversations where the business's website is cited. Insights appear only when there are enough conversations to meet certain thresholds. Shopify merchants can connect from Business Hub or the Shopify admin, and eligible Shopify products are already in ChatGPT through Shopify Catalog. After a claim, eligible organizations can build, test and launch a Business Agent. OpenAI says the Business Agent conversation is clearly labeled and separate from ChatGPT's own answers.

## A claim is not a UCP profile

A Business Hub claim, a [UCP profile](https://shopbotindex.com/guides/what-a-ucp-profile-proves/) at `/.well-known/ucp`, and a Shopify Catalog listing are different channels. They can exist together, and one does not stand in for the others. We cannot see Catalog or Business Hub status, so we do not count them.

## What the 9 November 2026 crawl shows

Each figure below is store-level: a store counts once, even when we fetched several of its websites. A store enters a share only when we could check that signal. Refusals, errors and checks we did not reach are left out. These are entries in our tracked list, not a random sample of retail. The method is the same one used on our [signal pages](https://shopbotindex.com/signals.html). We track 2,854 stores. For UCP, 629 could not be checked, which is why the profile share uses 2,225.

- [UCP profile](https://shopbotindex.com/stores.html): 951 of 2,225 stores we could check publish a UCP profile (42.7%). Shopify stores: 841 of 1,042 (80.7%). Big retailers: 16 of 255 (6.3%).
- [ACP discovery file](https://shopbotindex.com/signals/acp/): 1 of 1,270 (0.1%).
- [llms.txt](https://shopbotindex.com/signals/llms-txt/): 216 of 1,305 (16.6%). [AGENTS.md](https://shopbotindex.com/signals/agents-md/): 31 of 1,248 (2.5%).
- [AI catalog](https://shopbotindex.com/signals/ai-catalog/): 3 of 1,263 (0.2%).
- [MCP](https://shopbotindex.com/signals/mcp/): 945 of 2,466 name an MCP endpoint in a UCP profile (38.3%). Naming an endpoint is a declaration, not a test that tools worked.
- [AI rules in robots.txt](https://shopbotindex.com/signals/ai-bots-robots/): 279 of 2,075 have robots.txt rules that name an AI crawler (13.4%).
- [Product data](https://shopbotindex.com/signals/product-data/): 161 of 271 have schema.org Product markup on a product page we fetched (59.4%). Of those, 141 include price, currency and availability. We could not reach a product page for 2,583 stores, so this share is not a retail-wide rate.

[1,181 of 2,429 stores we could check](https://shopbotindex.com/signals/bot-protection/) had bot protection that refused our crawler (48.6%). A refusal of our crawler says nothing about shoppers, other agents, or a ChatGPT claim, but it does help explain why some denominators are much smaller than the UCP set. OpenAI's product feeds are added in Business Hub after a claim, so we cannot see them. A Business Hub claim does not depend on our crawler reaching the site.

## What to do with both channels

If you run a store and you are eligible, claiming the business in Business Hub is how OpenAI offers to keep your ChatGPT information current and to see mentions, website clicks and discovery topics. Keep a UCP profile, an llms.txt file and product markup with price, currency and availability current too: those are still what other agents, and a public crawler, can fetch without a claim. One channel does not replace the other. ShopBot Index does not test purchases. We will not report how many stores have claimed a ChatGPT profile until we have a public way to observe it.

## Frequently asked questions

### Can ShopBot Index tell me whether a store has claimed its ChatGPT profile?

No. We cannot see Business Hub claims, product feeds, mention counts, website clicks or discovery topics. A store can claim a profile without any change we can observe.

### If my store already publishes a UCP profile, do I still need to claim it in Business Hub?

They answer different needs. A UCP profile is a public discovery document. A Business Hub claim lets you update details, add product feeds, and see aggregated insights inside ChatGPT.

### Does schema.org Product markup on my site count as a ChatGPT product feed?

No. OpenAI describes product feeds as something you add in Business Hub after you claim and verify the business. Our check only looks for public schema.org Product markup on a product page we could fetch. In the 9 November 2026 crawl, 161 of 271 stores we could check had that markup (59.4%), and 141 included price, currency and availability.
