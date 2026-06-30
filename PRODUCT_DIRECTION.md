# Canary Islands Car Hire Optimiser Product Direction

## Product Vision

Canary Islands Car Hire Optimiser helps holidaymakers answer one simple question:

What is the cheapest sensible way to hire a car during my Canary Islands holiday?

The product is not trying to become another comparison website. It intentionally compares only four trusted local providers:

- PlusCar
- AutoReisen
- Cicar
- Payless Car

That focus is the product. The value is not breadth. The value is trust, clarity, and useful discoveries that a holidaymaker would not easily find by checking each provider manually.

The application should feel like an experienced Canary Islands travel assistant. It should understand that people often know when they are on holiday, but not exactly when they need a car, how long the best-value hire might be, or whether small date changes could save meaningful money.

## Who The Product Is For

The product is for people travelling to the Canary Islands who want a hire car from a company they can trust.

The primary user is a holidaymaker, couple, or family who knows their arrival and departure dates but has some flexibility about when they collect the car or how many days they hire it.

The secondary user already knows exactly when they want the car and simply wants to compare the four trusted providers quickly.

The product should assume the user is not technical, does not care about search algorithms, and does not want to manage combinations, search budgets, provider request counts, or time grids.

## Problems It Solves

The product helps users discover:

- which trusted provider is cheapest for their holiday
- whether a different collection day saves money
- whether a different hire duration is better value
- whether keeping the car longer costs little extra
- whether hiring for 8 days is cheaper than 7
- whether collecting later or returning earlier avoids a price jump
- whether the cheapest option still matches their real holiday plans

The product should save users time, reduce anxiety, and give them confidence that they are choosing a fair and sensible car hire option.

## What The Product Is Not

The product is not:

- a broker marketplace
- a full internet-wide comparison website
- a scraper for every rental company
- a tool for exhaustive brute-force search
- a developer-facing optimiser
- a spreadsheet generator with a GUI attached
- a product where users tune technical search settings

Current features that should be challenged or removed:

- visible search-size bands such as Small, Medium, Large, Extreme
- provider-search counts shown to ordinary users
- flexible time grids
- search modes that describe engine behaviour rather than user intent
- advanced options that make the product feel like a control panel
- reports that lead with tables, filters, or raw result volume
- long-running searches that attempt thousands of combinations

These features may have technical value, but they are not automatically product value. If they remain, they should be hidden, reframed, or used internally.

## User Journeys

### Compare My Dates

For users who already know exactly when they want the car.

The user provides:

- hire start date
- hire end date
- collection time
- return time
- automatic or manual preference if they care

The app compares the four trusted providers and recommends the best option.

This journey should be simple, fast, and calm. A typical search should take around 20 to 30 seconds when live provider checks are required, and faster when recent results can be reused.

### Find My Cheapest Hire

This is the flagship journey.

For users who know their holiday dates but can be flexible about when and how long they hire a car.

The user provides:

- arrival date
- departure date
- typical collection time
- typical return time
- roughly how long they think they need the car
- automatic or manual preference if they care

The app decides what to test.

The user should not think about:

- search modes
- provider searches
- combinations
- search budgets
- time grids
- exhaustive optimisation

The product should say, in effect:

Tell me when you are in the Canary Islands. I will look for the cheapest sensible hire from trusted local companies.

## UI Philosophy

The UI should feel like travel software, not an engineering tool.

Principles:

- ask fewer questions
- use plain English
- explain decisions in holiday terms
- show confidence, not complexity
- make the primary action obvious
- keep advanced controls out of the main path
- prefer recommendations over configuration

Preferred labels:

- Compare My Dates
- Find My Cheapest Hire
- Hire dates
- Hire duration
- Automatic or manual
- Arrival date
- Departure date
- Typical collection time
- Typical return time

Avoid labels like:

- optimiser mode
- provider searches
- combinations
- search bands
- extreme search
- advanced optimisation
- flexible time grid

If an advanced setting is needed, it should be framed around the user's holiday, not the search engine.

## Search Philosophy

The goal is not exhaustive searching.

The goal is to confidently find the cheapest realistic option using intelligent search.

The optimiser should search because it has a reason, not because another permutation exists.

It should prefer:

- representative samples
- common hire lengths
- promising neighbourhoods
- provider confirmation
- early useful results
- stopping when confidence is high

It should avoid:

- searching every time
- searching every length equally
- searching every date equally
- expanding to thousands of requests by default
- treating technical completeness as product quality

The ideal optimiser behaves like a knowledgeable person checking the market carefully, not like a brute-force script.

## Search Strategy

The future flagship search should run in intelligent waves.

### Wave 1: Baseline

Check the full holiday period across all four providers.

Purpose:

- establish the cost of hiring for the whole trip
- give the user an immediately understandable reference point
- detect whether full-holiday hire is surprisingly good value

### Wave 2: Common Hire Lengths

Check common holiday hire durations first.

Suggested priority:

- 7 days
- 8 days
- 10 days
- 14 days
- 5 or 6 days
- user-suggested duration

Purpose:

- find the price shapes that matter most
- avoid treating every duration as equally likely
- discover cases where 8 days is cheaper than 7, or 10 days is better value than 9

### Wave 3: Promising Date Areas

Search around the cheapest results from earlier waves.

Examples:

- one day earlier
- one day later
- one day longer
- one day shorter
- same length on nearby start days

Purpose:

- explore where savings are likely
- avoid wasting searches far away from promising results

### Wave 4: Provider Confirmation

Recheck finalists and close alternatives across providers.

Purpose:

- confirm the recommendation is not a one-provider anomaly
- capture strong alternatives
- build confidence in the final recommendation

### Stop Conditions

The optimiser should stop when it has enough confidence.

Possible stop signals:

- the current best option remains best after nearby variants are checked
- no nearby date or duration improves the best price meaningfully
- the same provider keeps winning across comparable searches
- the saving from further exploration is unlikely to justify the waiting time
- the internal search budget is reached

The report can be honest without being technical:

We checked the most likely ways to save money and found a clear best option.

## Target Search Budgets

Search budgets should be internal product limits, not user-facing controls.

Targets:

- Compare My Dates: around 4 provider searches
- Typical Find My Cheapest Hire: 50 to 150 provider searches
- Larger flexible holiday search: 300 to 500 provider searches
- Thousands of searches: exceptional and usually a product failure

If the app thinks it needs more than 500 provider searches, it should first ask whether the search can be simplified. Better still, it should choose a smarter sample.

If the app ever proposes thousands of searches, the design should be challenged before the search is allowed to proceed.

## Report Philosophy

The report should answer five questions:

1. What should I book?
2. Why is it recommended?
3. How much could I save?
4. What interesting things did the app discover?
5. What are the best alternatives?

The report should lead with a recommendation, not a result table.

The most valuable output is insight.

Examples:

- Hiring for 8 days instead of 7 saves EUR 34.
- Collecting on Tuesday saves EUR 61.
- Keeping the car for your whole holiday only costs another EUR 12.
- AutoReisen was consistently cheapest for this travel window.
- The cheapest automatic was only EUR 18 more than the cheapest manual.

Raw results, filters, CSV, and Excel exports can remain, but they are supporting material. They should not define the product experience.

## Recommendation Principles

A recommendation should be explainable in human terms.

Good recommendation reasons:

- cheapest trusted option
- best value per day
- matches your holiday dates
- close to your preferred collection time
- automatic transmission
- enough seats
- only slightly more than a shorter hire
- strong alternative if you want the car for the whole trip

Poor recommendation reasons:

- ranked first by algorithm
- found after 1,284 provider searches
- selected from an exhaustive combination grid
- lowest normalised result object

## What Should Stay

- Four trusted providers only
- Provider-based architecture
- Normalised results
- Booking links or clear provider continuation links
- Local Windows app
- HTML report
- CSV and Excel exports as secondary outputs
- Cache as an internal speed aid
- Progress feedback during live provider checks

## What Should Change

- The optimiser should move from exhaustive generation to intelligent waves.
- The UI should move from search configuration to holiday guidance.
- The report should move from result display to recommendation and insight.
- Runtime estimates should be reframed around waiting time, not provider-search counts.
- Advanced settings should be hidden or removed unless they directly support real holiday decisions.

## What Should Disappear Or Be Hidden

- User-facing search bands
- User-facing provider-search counts
- Extreme searches as a normal option
- Time grids
- Technical cache controls
- Overly detailed progress dashboards
- Report sections that emphasise raw search volume over decisions

Some of these may remain internally for diagnostics, but they should not be part of the ordinary user journey.

## Future Roadmap

### Product Reset

- Rename user journeys to Compare My Dates and Find My Cheapest Hire.
- Simplify the main UI around holiday dates, likely hire duration, and transmission preference.
- Hide or remove technical controls.
- Rewrite progress messages as assistant-style updates.

### Intelligent Search

- Implement wave-based search.
- Introduce internal search budgets.
- Prioritise common hire lengths.
- Explore around promising results.
- Add confidence-based stopping.

### Insight Report

- Lead with a single recommendation.
- Add a "What we discovered" section.
- Compare best option against obvious alternatives.
- Explain savings in holiday terms.
- Keep full results available but secondary.

### Trust And Clarity

- Explain why only four providers are supported.
- Make hidden-charge avoidance part of the product story.
- Keep support and holiday-home sections tasteful and secondary.

### Performance

- Use cache quietly to avoid repeated checks.
- Avoid unnecessary provider visits.
- Reuse baseline searches where possible.
- Optimise for time-to-useful-answer, not total search capacity.

## Decision

The product should stop evolving as a brute-force search engine.

From this point, new work should be judged against one question:

Does this help a holidaymaker confidently choose the cheapest sensible trusted car hire option?

If the answer is no, the feature should be removed, hidden, or redesigned.

