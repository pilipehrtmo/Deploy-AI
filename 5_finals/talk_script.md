# Finals talk script (8 minutes) and Q&A

Two presenters: **A** (story, slides 1, 2, 6) and **B** (method, slides 3, 4, 5). About 80 seconds a slide.
Every number below comes from the pipeline output; rerun `python run.py` and this file updates.

## Slide 1 · The problem and our approach (A)
"In the three months before 1 April, 41 postpaid customers in our 1-in-130 sample, about 5,330 across Formosa,
told a support agent they were cancelling, porting their number or signing with a rival. 20 of those 41 were gone within 60 days.
Nobody at Formosa reads these notes. Vivian asked who is leaving, why, and what keeps them. Her customers are already telling her."

## Slide 2 · What the data shows (A)
- Customers whose notes show leave intent: 49.3% leave within 60 days. Average: 3.7%.
- Today's renewal push (contracts ending within 4 months): 4.2%. Barely better than picking at random.
- We tested this on three past dates using only notes written before each date, so it is not hindsight.
- Roaming blasts: no extra sales against the held-back group.

## Slide 3 · Who to target, and why (B)
- R1 leaving now and R2 wavering: call the highest bills first, then LINE and SMS.
- The reason decides the offer: price or a rival → Renewal discount or Data boost; phone problem → Device credit; bill error or bad signal → fix it, no discount.
- Rivals are named 417 times; those customers left at 53%–62%. A third were already getting quotes or porting, so speed beats discount size.

## Slide 4 · The campaigns (B)
- Every message: approved offer, legal footer added by code, automatic compliance check. 89 of 240 past campaigns would have failed it.
- Worth a year at full scale: retention NT$3.7M–NT$13.1M; earn more NT$2.2M–NT$2.6M; acquisition shift NT$1.4M–NT$4.2M.
- Live demo (30 seconds): open `4_outputs/campaign_builder.html`, pick Renewal discount + SMS + "Price or a rival", show the audience size and the PASS.

## Slide 5 · The 90-day pilot (B)
- About 13,000 flagged postpaid customers; one in five held back at random.
- Expected cost NT$1.1M, at most NT$1.9M, inside NT$2.5M.
- Break-even: keep 1.3% of would-be leavers. The pilot can prove 6.2% or more.
- Day 45: if contacted customers leave as often as held-back ones, paid offers stop.

## Slide 6 · Our recommendation (A)
"Approve the pilot. Week one, we connect the weekly notes file and send the first call list.
Day 45, we check direction. Day 90, if the gap is 3.1 percentage points or more, scale it to the whole base and move roaming and broad upsell money into it."

---

## Hard questions, short answers

**What if the save rate is zero?**
Then we find out cheaply. Offers cost money only when taken; the day-45 check stops them. Worst case is roughly half the expected offer cost plus messages and creative, about NT$602K, and Formosa learns that note-based retention does not work at these offers.

**Why rules and not a machine-learning model?**
Customers the rules flag leave 13× more often than average on dates the rules never saw, a marketer can read and change them, and every customer comes with a reason that decides the offer. A model on 50,000 rows whose plan and contract fields show only the latest values would risk learning the future.

**How do you know the AI read the notes correctly?**
It labelled 403 distinct sentences, not 8,000 notes, so every label can be checked by a person. Two of us are labelling a blind sample of 100 of those sentences to measure agreement; see 3_ai_outputs/hand_check. The outcome agrees: flagged customers left at 49.3%. Any sentence it has never seen goes to a review queue as "unknown".

**Notes catch only 9% of leavers. Isn't that small?**
It is the precise part: about 1 in 2 flagged customers leave. Most leavers never call support. Next: the welcome check-in for new customers (2.6× average churn) and asking agents to log every contact.

**Why multiply by 130?**
The fact sheet says the customer files are a fair 1-in-130 sample of 6.5 million customers.

**Can you trust the past-campaign audit?**
Since July 2025 one in five chosen customers was held back at random. We compare only those campaigns, and only contacts whose 30-day tracking window had finished.

**Isn't Renewal discount expensive?**
It goes only to customers within four months of contract end who raised price or renewal. Customers who only want more data get Data boost at NT$300.

**Why can't the pilot prove the break-even?**
With 2,600 held back, chance alone moves the result by about ±2.1 percentage points, more than the 0.62%-point break-even gap. We say so up front and give a rule for each outcome instead of over-promising.
