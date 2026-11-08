# What a published UCP profile proves, and what it doesn't

A store that publishes a UCP profile has made a machine-readable discovery document available. That is useful evidence about what the store declares. It is not evidence that a particular shopping assistant completed a purchase there.

The distinction matters whether you run a store, build an agent or read an adoption chart. Discovery, compatibility and a completed transaction answer different questions. ShopBot Index measures public discovery signals, not purchases.

## Start with the document, not the badge

UCP means Universal Commerce Protocol. The [protocol specification](https://ucp.dev/specification/overview/) describes a business profile at `/.well-known/ucp`. It advertises services, capabilities and payment handlers. A platform still has to establish which capabilities and versions it shares with the business.

A positive result in our index means the store publishes a UCP profile under our documented crawl checks. It does not mean we have validated every requirement in the specification, tested every declared service or certified an integration.

For an integration team, the profile is a starting point for a test plan. Which capability do you need? Does the intended platform support a compatible version? What happens when the buyer needs to complete a step? Those questions need separate answers.

## Read all three result categories

Our 2 November 2026 crawl recorded 947 positive retailer/store entries among 2,224 we could check. Another 630 tracked entries were marked "couldn't check". The remaining 1,277 checkable entries had no profile found under our checks.

These are entries in our tracked list, not a random sample of retail. A retailer entry can cover several websites and counts as positive if at least one publishes a profile. Do not read the figures as a count of distinct corporate owners or as a retail-wide adoption rate.

The unknown category belongs beside the positive and negative categories. It should not disappear into either of them.

## An unchecked store is not a failed integration

"Couldn't check" describes our observation limits. A website may refuse the identified crawler, time out, fail a connection or disallow the requested path in robots.txt. Our [methodology](https://shopbotindex.com/methodology.html) explains how we aggregate those results across a retailer's websites.

That result does not establish what a shopper or a different agent sees. If you are evaluating a merchant, keep the uncertainty in your notes rather than recording "does not support agent shopping".

The reverse mistake is also possible. A server answering a request does not establish that it returned the expected discovery document. An HTML page at the requested address is not a JSON profile merely because the HTTP status is successful.

## No profile found is a narrower finding than no agent shopping

An agent may use a normal web browser. Other integrations may depend on private feeds or arrangements that our public crawl cannot see. Failing to find a UCP profile therefore does not prove that agents cannot shop at a store.

Likewise, supporting signals such as product markup or guidance files do not prove that checkout works. Keep each observation attached to the test that produced it, rather than combining them into an unsupported readiness score.

## A practical checklist for using the result

- Record the crawl date and the website or retailer entry you examined.
- Keep "profile found", "no profile found" and "couldn't check" separate.
- Check whether a retailer-level result covers several websites before comparing markets or domains.
- Treat declared capabilities as inputs to compatibility testing, not completed tests.
- If purchase completion matters, evaluate that separately with authorization and a defined test scope.
- When quoting a rate, state the checked denominator and the limits of the tracked list.

A useful report says exactly what was observed and what remains unknown. That gives the next person a testable question instead of a confidence claim the crawl cannot support.
