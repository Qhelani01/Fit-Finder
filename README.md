# FitFindr

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first** — setup, every
> command, and what to do when something breaks.
>
> Once `python test.py` passes:
>
> ```bash
> python app.py listings --full -n 6      # read the data (Milestone 1)
> python app.py fields                    # what you can filter on
> python app.py ask 'vintage graphic tee under $30'
> ```
>
> All three tools are stubs, so that last command will do nothing useful yet.
> That's the starting position.
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     HOW TO USE THIS FILE

     This is your submission. Fill each section in as you finish the milestone
     it belongs to — don't leave it all to the end.

     Unit 3 asks for the first five sections. Unit 4 adds the five below them.
     Leave the unit 4 sections alone until then; they're here so you know
     what's coming.

     Everything is pasted as TEXT. No screenshots, no images, no video links.
     A typed block of output gets full credit; a picture of the same output
     gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 3 — THE BUILD ═══════════════════════ -->

## What This Does

<!-- Three or four sentences: what a user asks for, and what they get back. -->

FitFindr takes a plain-language thrift request like `'vintage graphic tee under $30, size M'` and searches 40 secondhand listings from Depop, thredUp and Poshmark for the best match within that size and price. It then asks a model to style the top match with pieces from the user's own wardrobe, or to give general styling advice if the wardrobe is empty. Finally it writes a short, postable "fit card" caption naming the item, its price and the platform. If nothing matches, the agent stops after the search and tells the user which part of the request to loosen.


---

## Tool Inventory

<!-- Four lines per tool. This is worth 2 points and it's the single most
     common place students lose them.

     "Returns a list" earns NOTHING. The description has to say what is IN
     the list.

     The empty case isn't optional either — it's the thing your loop branches
     on, and if you don't decide it here you'll discover it as a crash in
     Milestone 5. -->

### `search_listings`

- **What it does:** Filters `data/listings.json` by size and price ceiling, then ranks what's left by how many of the description's keywords appear in each listing (title, description, style tags, category, colors, brand), with title and style-tag hits counting double.
- **Inputs:** `description` (str) — keywords like `"vintage graphic tee"`; `size` (str or None) — `None` skips the size filter; `max_price` (float or None) — inclusive ceiling, `None` skips the price filter.
- **Returns:** A `list[dict]` of at most `config.SEARCH_RESULT_LIMIT` (10) listing dicts, best match first (ties go to the cheaper item). Each dict is the unmodified listing: `id`, `title`, `description`, `category`, `style_tags` (list), `size`, `condition`, `price` (float), `colors` (list), `brand` (str or None), `platform`.
  - **Size match rule:** case-insensitive, by whole token, not substring. The listing's size is split on `/`, spaces and parentheses, and every token of the requested size must appear among the listing's tokens. So `M` matches `S/M` and `M/L`, `8` matches `US 8`, but `S` does **not** match `US 9` and `L` does **not** match `XL` or `W30 L30`. Listings whose size starts with `One Size` match any requested size.
- **When it has nothing:** An empty list `[]` — never `None`, never an exception. That includes a description with no usable keywords, because every listing scores zero.

### `suggest_outfit`

- **What it does:** Asks the model for one or two outfits built around the new item, naming specific pieces from the user's wardrobe.
- **Inputs:** `new_item` (dict) — one listing dict, as returned by `search_listings`; `wardrobe` (dict) — `{"items": [wardrobe item dicts]}` with `name`, `category`, `colors`, `style_tags`, `notes`.
- **Returns:** A non-empty `str` of plain-text outfit suggestions, each naming the new item plus the wardrobe pieces (by their `name`) that go with it.
- **When it has nothing:** If `wardrobe["items"]` is empty or missing, it does not fail. It returns a non-empty `str` of general styling advice for the item (what kinds of pieces pair with it), with no references to an owned wardrobe.

### `create_fit_card`

- **What it does:** Asks the model for a short social-media caption about the find and the outfit.
- **Inputs:** `outfit` (str) — the string `suggest_outfit` returned; `new_item` (dict) — the same listing dict that went into `suggest_outfit`.
- **Returns:** A `str` caption of two to four sentences that mentions the item's title, price and platform once each and describes the outfit's vibe. Temperature is 0.9, so wording varies between runs.
- **When it has nothing:** If `outfit` is empty or only whitespace, it does not call the model. It returns the string `"Can't write a fit card for <title>: no outfit suggestion was provided."`

---

## Planning Loop

<!-- Your branch rule, stated as a rule — the condition AND both paths — plus
     the file and function that holds it.

     Like this:
       "If search_listings returns an empty list, put a message in the session
        and stop. Otherwise take the first result and go to suggest_outfit."
        — agent.py::run_agent

     The grader checks your code against what you claim here, so the file and
     function have to be real. -->

**Branch rule:** If `search_listings` returns an empty list, put a message in `session["error"]` that names what was searched for and which filter to loosen (raise the price, drop the size, use fewer or different words), then return the session without calling `suggest_outfit` or `create_fit_card`. Otherwise, put the first result in `session["selected_item"]`, call `suggest_outfit` with it, then call `create_fit_card`.

**Where it lives:** `agent.py::run_agent`

**How the query is parsed:** Regex, no model call. A price ceiling comes from phrases like `under $30`, `below 30`, `max $30`, `< $30` or `$30 or less`. A size comes from `size <X>` (e.g. `size M`, `size 8`, `size W30`). Whatever is left, minus filler words like "looking for", becomes the description.

**What moves through the session:** `query` → `parsed` (`description`, `size`, `max_price`) → `search_results` → `selected_item` (read back out of the session for both later calls) → `outfit_input_item` (a record of exactly what `suggest_outfit` received, so criterion 3 can compare it with `selected_item`) → `outfit_suggestion` (read back out for the fit card) → `fit_card`. `error` is set only on the early-stop path, and then `selected_item`, `outfit_suggestion` and `fit_card` stay `None`.

---

## Sample Run

<!-- Two things go here.

     1. One FULL query and its output, pasted as text.
     2. Your three per-tool terminal tests — the command and what it printed. -->

**One full query**

```
$ python app.py ask 'vintage graphic tee under $30'
  Found:    Y2K Baby Tee — Butterfly Print — $18.0 on depop

  Outfit:   Outfit 1: Pair the Y2K Baby Tee with the baggy straight-leg jeans, dark wash. Add the vintage black denim jacket and the chunky white sneakers. Accessorize with the black crossbody bag for an effortless, streetwear-inspired look. 

Outfit 2: Combine the Y2K Baby Tee with the wide-leg khaki trousers, cinched at the waist with the brown leather belt. Layer the black cropped zip hoodie on top and finish the outfit with the chunky white sneakers for a playful mix of Y2K and minimal earth tones.

  Fit card: Scored this Y2K butterfly print baby tee on Depop for just $18.00 and I'm obsessed. I paired it today with dark wash baggy straight-leg jeans, a vintage black denim jacket, and chunky white sneakers for an effortless streetwear-inspired look. Finishing it off with a black crossbody bag ties the whole fit together. 🦋✨

1 model calls this session, 1 served from cache, 240 prompt + 75 output tokens
```

**The same agent on a query that matches nothing** — it stops after the search with no model calls:

```
$ python app.py ask 'designer ballgown size XXS under $5'

  No listings matched 'designer ballgown' (size XXS, under $5). To find something, try: drop the size or try a neighbouring one (e.g. S/M, M/L); raise the price limit above $5; use fewer or more common words (e.g. 'graphic tee', 'denim jacket', 'boots').

0 model calls this session
```

**The three tools, tested one at a time**

```
$ python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
[{'id': 'lst_002', 'title': 'Y2K Baby Tee — Butterfly Print', 'description': 'Super cute early 2000s baby tee with butterfly graphic. Fitted crop length. Tag says medium but fits like a small.', 'category': 'tops', 'style_tags': ['y2k', 'vintage', 'graphic tee', 'cottagecore'], 'size': 'S/M', 'condition': 'excellent', 'price': 18.0, 'colors': ['white', 'pink', 'purple'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_033', 'title': 'Vintage Band Tee — Faded Grey', 'description': 'Faded grey band-style tee with distressed graphic. Crew neck. Fits boxy. Well-loved but no holes or major damage.', 'category': 'tops', 'style_tags': ['vintage', 'grunge', 'band tee', 'graphic tee', 'streetwear'], 'size': 'L', 'condition': 'fair', 'price': 19.0, 'colors': ['grey', 'charcoal'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_006', 'title': 'Graphic Tee — 2003 Tour Bootleg Style', 'description': 'Vintage-style bootleg tee with faded graphic. Slightly boxy fit. 100% cotton, soft and worn-in.', 'category': 'tops', 'style_tags': ['graphic tee', 'vintage', 'grunge', 'streetwear', 'band tee'], 'size': 'L', 'condition': 'good', 'price': 24.0, 'colors': ['black'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_017', 'title': 'Mesh Long-Sleeve Top — Black', 'description': 'Sheer black mesh long-sleeve. Great for layering under a graphic tee or over a bralette. Stretchy material, fits true to size.', 'category': 'tops', 'style_tags': ['y2k', 'grunge', 'goth', 'layering'], 'size': 'S/M', 'condition': 'excellent', 'price': 15.0, 'colors': ['black'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_015', 'title': 'Vintage Graphic Hoodie — Faded Black', 'description': 'Faded black pullover hoodie with barely-visible vintage graphic on the chest. Cozy interior. Some pilling but adds to the worn-in look.', 'category': 'tops', 'style_tags': ['vintage', 'grunge', 'graphic', 'streetwear'], 'size': 'L', 'condition': 'fair', 'price': 26.0, 'colors': ['black', 'charcoal'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_012', 'title': 'Oversized Crewneck Sweatshirt — Vintage Navy', 'description': 'Perfectly faded navy crewneck. Genuinely vintage — not manufactured distressed. Ribbed cuffs and hem. No graphics, clean.', 'category': 'tops', 'style_tags': ['vintage', 'basics', 'oversized', 'classic'], 'size': 'XL (fits oversized)', 'condition': 'good', 'price': 20.0, 'colors': ['navy'], 'brand': None, 'platform': 'thredUp'}, {'id': 'lst_011', 'title': 'Low-Rise Cargo Pants — Khaki', 'description': 'Y2K era low-rise cargo pants. Lots of pockets. Khaki color, slightly distressed at the hems. Great for layering with a long tee.', 'category': 'bottoms', 'style_tags': ['y2k', 'cargo', '2000s', 'streetwear'], 'size': 'W29', 'condition': 'fair', 'price': 27.0, 'colors': ['khaki', 'tan'], 'brand': None, 'platform': 'poshmark'}]
```

```
$ python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
Outfit One: Wear the Vintage Levi's 501 Jeans with the White ribbed tank top tucked in. Add the Black cropped zip hoodie layered on top and finish with the Chunky white sneakers. Accessorize with the Black crossbody bag for an effortless, streetwear-inspired look.

Outfit Two: Pair the Vintage Levi's 501 Jeans with the Brown leather belt. Layer the Oversized grey crewneck sweatshirt over the top for a relaxed silhouette, and complete the outfit with the Black combat boots for a classic, slightly grunge edge.
```

```
$ python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
Scored these vintage Levi's 501 jeans on Depop for $38.00 and they honestly fit like a glove. The medium wash looks so effortless paired with crisp white sneakers for that classic off-duty look. Truly living in this fit from now on. 👖✨
```

---

## How I Used AI

<!-- Two specific moments. What you asked, what came back, what you changed.

     "I used Claude to help me code" is not enough.

     "I gave Claude my search_listings spec. It returned None on no match
     instead of an empty list, so I changed it" is the level we want. -->

**Moment 1**

- *What I asked for:* I pasted my five acceptance criteria into Claude and asked it to tell me how it would test each one from the sentence alone, without rewriting them.
- *What came back:* It said my reason for criterion 1 argued for 5 of 5 ("a deterministic sequence of steps") while the criterion's target was 4 of 5. It also pointed out that the path isn't deterministic, because it makes two model calls and uses a keyword search. For the fit card criterion, it said it couldn't tell what "name" meant (listing titles are long), what counted as an "invented detail", or whether emojis and hashtags counted as sentences.
- *What I changed:* I rewrote the criterion 1 reason to justify 4 of 5 (LLM calls can time out or hit the rate limit, and keyword search is sensitive to phrasing). I also tightened criterion 4: the title may be shortened only if it still identifies the item; the caption can't state a different price, platform, size, brand or item type; and emojis and standalone hashtags don't count as sentences.

**Moment 2**

- *What I asked for:* I had Claude build `create_fit_card` from my spec and run the whole agent on `'looking for a vintage graphic tee under $30'`.
- *What came back:* The caption said *"knew I had to **list** it on depop"*. The prompt only said `Platform: depop`, so the model read the platform as where the user was selling the item, not where they bought it.
- *What I changed:* I changed the prompt to say the user "just bought and are wearing" the item, and relabelled the fields `Price they paid:` and `Where they bought it:`. Later runs say "Scored this … on Depop for just $18.00", which matches criterion 4.

**Unit 4 — Moment 3**

- *What I asked for:* I worked through the unit 4 milestones together with Claude Code: registering the MCP tool, triggering the failures, choosing scenarios, and running and scoring both evals.
- *What came back:* We triggered the three failures before writing any handlers. That showed the bad-key case only *looked* handled: `run_agent` raised `ModelUnavailable`, `app.py`'s catch-all printed it, and the item the search had found was lost. While planning the scenarios, Claude also pointed out that `vintage graphic tee under $30` couldn't test criterion 5, because no matching listing costs more than $30. It would pass even with the price filter deleted.
- *What I changed:* We added `_model_down` in `run_agent`, so the agent returns a message and keeps the item. For criterion 5 we switched to `vintage jacket under $35`, where 3 keyword matches are over the limit.

**Unit 4 — Moment 4**

- *What I asked for:* Help scoring the before run against my criteria.
- *What came back:* In three criterion 3 tries, `suggest_outfit` hit a 503 before its inputs were logged. The code makes a mismatch almost impossible, so marking them PASS was tempting. Claude argued they had to be FAIL, because the run log has no evidence either way.
- *What I changed:* I kept the strict verdict, MISSED (2/5), and put both sides into the diagnosis. The logging gap went under What's Still Broken instead of being counted as a pass.

<!-- ═══════════════════════ UNIT 4 — THE TEST ═══════════════════════

     Don't fill these in during unit 3.
     ═══════════════════════════════════════════════════════════════════ -->

---

## Run Log — Before

<!-- Five criteria, five tries each, in this exact format.

     Five, because your criteria are written out of five. Mark each try PASS
     or FAIL, count the passes, and read that count against your target — a
     row targeting 4 of 5 with three PASS cells is MISSED (3/5).

     `python run_eval.py --label before` runs everything and writes the table
     into results/. Paste it here and fill in the verdicts. -->

Full log: [results/run_2026-10-13_2158_before.md](results/run_2026-10-13_2158_before.md) — `python run_eval.py --label before`, 5 tries per scenario, cache off, temperature 0.9, 43 model calls.

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. Matching query completes all three tools (`vintage graphic tee under $30`) | 4 of 5 | PASS | PASS | FAIL | PASS | PASS | MET (4/5) |
| 2. Impossible query stops before tool 2 (`designer ballgown size XXS under $5`) | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. `selected_item` = item passed to `suggest_outfit` (`90s track jacket in size M`) | 5 of 5 | FAIL | FAIL | PASS | FAIL | PASS | MISSED (2/5) |
| 4. Fit card: 2–4 sentences, title, exact price, platform, nothing contradicted (`denim jacket under $50`) | 4 of 5 | PASS | PASS | FAIL | FAIL | FAIL | MISSED (2/5) |
| 5. Nothing returned over `max_price` (`vintage jacket under $35`) | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

Every early stop in this run was the same error. 14 of the 43 model calls came back `503 UNAVAILABLE — This model is currently experiencing high demand`: 7 in `suggest_outfit`, 7 in `create_fit_card`. That includes 3 of the 5 diagnostic empty-wardrobe tries, which aren't in the table.

**Real output, one try per criterion.** All runs: `run_eval.py::run_once` → `agent.py::run_agent`; search via `mcp_server.py::search_listings`; outfit by `tools.py::suggest_outfit`; card by `tools.py::create_fit_card`.

Criterion 1, try 3 (the FAIL). `agent.py::_model_down` produced the stop:
```
- stopped early: yes — Found Y2K Baby Tee — Butterfly Print — $18.00 on depop, but the styling model couldn't be reached, so there's no outfit or fit card this time. Couldn't reach the model: 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}} The search itself worked, so once that's sorted, run the same request again.
- selected_item: Y2K Baby Tee — Butterfly Print ($18.0, depop)
- search_results: 10
```

Criterion 2, try 1. `agent.py::_no_results_message` produced the stop:
```
- stopped early: yes — No listings matched 'designer ballgown' (size XXS, under $5). To find something, try: drop the size or try a neighbouring one (e.g. S/M, M/L); raise the price limit above $5; use fewer or more common words (e.g. 'graphic tee', 'denim jacket', 'boots').
- selected_item: (none)
- search_results: 0
[2] search_listings (via MCP)
      in:  description='designer ballgown', size='XXS', max_price=5.0
      out: [] (empty)
      →    branch: empty → stop, suggest_outfit NOT called
```

Criterion 3: try 3 (PASS) next to try 1 (FAIL, inputs never logged). Trace from `agent.py::run_agent`:
```
try 3
[2] search_listings (via MCP)
      →    branch: 5 results (prices $14–$75) → selected_item = lst_004
[3] suggest_outfit
      in:  new_item=lst_004 '90s Track Jacket — Navy/White Stripe' ($45, poshmark), wardrobe=10 items
[4] create_fit_card
      out: ModelUnavailable: Couldn't reach the model: 503 UNAVAILABLE. ...

try 1
[2] search_listings (via MCP)
      →    branch: 5 results (prices $14–$75) → selected_item = lst_004
[3] suggest_outfit
      out: ModelUnavailable: Couldn't reach the model: 503 UNAVAILABLE. ...
      →    model unreachable, stopping
```

Criterion 4: tries 2 (PASS) and 3 (FAIL, one sentence), from `tools.py::create_fit_card`. Listing: *Denim Jacket — Light Wash, Cropped*, $42.00, poshmark, Wrangler, size S:
```
try 2: Scored this cropped Wrangler denim jacket on Poshmark for just $42.00, and I'm obsessed with how it pulls together a double-denim streetwear look. It also brings the ideal minimal aesthetic when layered over an oversized grey crewneck and wide-leg khaki trousers.

try 3: Scored this vintage Wrangler light wash cropped denim jacket on Poshmark for $42.00, and I'm obsessed with how it looks paired with a white ribbed tank, baggy straight-leg jeans, and chunky white sneakers for a casual streetwear vibe. 👖✨
```

Criterion 5, try 1. Search step from `agent.py::run_agent` (the prices come from every returned listing, not just the first):
```
[2] search_listings (via MCP)
      in:  description='vintage jacket', size=None, max_price=35.0
      out: 10 items: Leather Belt — Brown, Braided, Bucket Hat — Reversible, Brown Plaid, Henley Long Sleeve — Washed Burgundy … +7 more
      →    branch: 10 results (prices $12–$24) → selected_item = lst_014
```

---

## Verdicts and Diagnoses

<!-- MET or MISSED per criterion against LAST UNIT's target, plus a sentence on
     how you decided.

     Then, for every miss: which of the four places it happened — a tool, the
     loop's branch, the session, or the model's output — AND the mechanism.

     Not a diagnosis:  "The fit card was bad."
     A diagnosis:      "The fit card criterion missed on 2 of 5 items. Both had
                        an empty brand field. My prompt puts the brand in the
                        first sentence, so the card opened with a blank and read
                        like a fragment. The tool worked; the prompt assumed a
                        field that isn't always there."

     Look for a pattern. Three misses on the same tool is one problem, not
     three. -->

Verdicts are against the targets in `criteria.md` as written in unit 3. None were revised.

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 | Matching query completes all three tools | 4 of 5 | **MET (4/5)** | PASS = `selected_item`, `outfit_suggestion` and `fit_card` all populated and `error` is None. Try 3 stopped in `suggest_outfit` with no outfit or card. 4 passes against a target of 4. |
| 2 | Impossible query stops before tool 2 | 5 of 5 | **MET (5/5)** | PASS = 0 search results, `error` says what to change, and the trace has no `suggest_outfit`/`create_fit_card` step. All five matched. |
| 3 | `selected_item` matches the item passed to `suggest_outfit` | 5 of 5 | **MISSED (2/5)** | PASS = the trace shows `suggest_outfit` received the same id, price and platform as `selected_item`. Tries 3 and 5 show `lst_004 ($45, poshmark)` on both sides. In tries 1, 2 and 4, `suggest_outfit` raised a 503 before its inputs were logged, so the run log can't show a match. Unverified isn't a pass. |
| 4 | Fit card: 2–4 sentences, title, exact price, platform, nothing contradicted | 4 of 5 | **MISSED (2/5)** | Read each card against the listing. Tries 1 and 2 pass: 3 and 2 sentences, "Wrangler … denim jacket", "$42.00", "Poshmark", and nothing contradicted (Wrangler is the listing's real brand, "vintage" is one of its style tags). Try 3 has every fact right but is a single sentence; the criterion says 2–4. Tries 4 and 5 produced no card (503). |
| 5 | Nothing returned over `max_price` | 5 of 5 | **MET (5/5)** | PASS = the most expensive of all returned listings ≤ $35. The trace computes min/max over every result: $12–$24 in all five tries. The query was chosen because 3 keyword matches cost more than $35, so the filter really had something to drop. |

**Diagnoses**

**The pattern: two misses, and one shared mechanism behind most of them.** Of the 8 FAIL cells, 7 are the same thing. The provider returned `503 UNAVAILABLE` ("high demand"), and `generate.py::generate` treated it as fatal. Its retry loop only retries a 429. Any other error, including a 503 that the message itself calls "usually temporary", goes straight to `raise ModelUnavailable`. The handler I added in Milestone 2 (`agent.py::_model_down`) then did its job and stopped the run politely. So the run didn't crash; it ended without trying again. **Place: the model call (the adapter around the tools), not a tool's logic, the branch, or the session.** The failures land on whichever tool happened to make the call: 7 in `suggest_outfit`, 7 in `create_fit_card`.

- **Criterion 3 — MISSED, 2/5. Place: the model call, plus a gap in what my trace records.** Nothing in the run shows the session handing over the wrong item. Every try's search step chose `lst_004`, and both tries that logged `suggest_outfit`'s input show `lst_004 ($45, poshmark)`. The three failures are tries where `suggest_outfit` raised a 503. On that path `_model_down` logs the error but not the `new_item` that went in, so there is no evidence to score. Two mechanisms together: the 503 isn't retried, and my error-path trace step drops the inputs. To be honest about the target: in the code, `outfit_input_item` and the argument to `suggest_outfit` are the same variable, so this criterion can only catch a future regression. The target was easy, and missing it says more about my logging than about my session.
- **Criterion 4 — MISSED, 2/5. Two places.** Tries 4 and 5: the model call again (503 in `create_fit_card`, so no card). Try 3: **the model's output.** The prompt in `tools.py::create_fit_card` says "2 to 4 sentences of prose", and the model wrote one long run-on sentence joined with ", and I'm obsessed with how it looks paired with…", then an emoji. My criterion says emojis don't count as sentences, so it's one. The tool passed the right facts; the prompt asks for a sentence count without checking it. Even without any 503s, this would have been 4/5. That just meets the target, and that's the only reason criterion 4 isn't purely a reliability problem.
- **Criterion 1 — MET, but only just, and for the same reason.** The one FAIL (try 3) is a 503 in `suggest_outfit`. 4/5 meets the target. I wrote the 1-in-5 allowance for exactly this kind of API error, which held, but with no slack left.

**Found while testing, not covered by any criterion:** criterion 5's query `vintage jacket under $35` selects a **Leather Belt** (`lst_014`) as the best match. So did `leather boots under $60` while I was triggering failures. `tools.py::search_listings` scores each wanted keyword independently, and ties go to the cheaper item. Every listing with "jacket" in its title costs more than $35. The only jacket under the limit, *Shacket — Olive Canvas* ($33), mentions "jacket" only in its description (1 point). The belt has `vintage` as a style tag (2 points), so the belt wins. Criterion 5 passes because it only checks price. No criterion checks that the selected item is the right *kind* of thing, which is the criterion I'd add next.



---

## Loop Trace

<!-- One full run, printed step by step, with the MCP call visible in it.

     `python app.py ask '...' --trace` once you've added the trace.step()
     calls in Milestone 2.

     Worth pasting BOTH the happy path and the empty-search path. The empty
     one should be visibly shorter, because it stops. If your two traces are
     the same length, your branch isn't working — and this is the fastest way
     anyone will ever find that out. -->

Trace calls are in `agent.py::run_agent`, one `trace.step()` per step. Step 2 is the MCP call: `run_agent` → `mcp_client.call_tool("search_listings", …)` → `mcp_server.py::search_listings`.

**Happy path.** From the before run, criterion 1, try 1 (`results/run_2026-10-13_2158_before.md`):

```
[1] parse_query
      in:  'vintage graphic tee under $30'
      out: description='vintage graphic tee', size=None, max_price=30.0
[2] search_listings (via MCP)
      in:  description='vintage graphic tee', size=None, max_price=30.0
      out: 10 items: Y2K Baby Tee — Butterfly Print, Vintage Band Tee — Faded Grey, Graphic Tee — 2003 Tour Bootleg Style … +7 more
      →    branch: 10 results (prices $12–$26) → selected_item = lst_002
[3] suggest_outfit
      in:  new_item=lst_002 'Y2K Baby Tee — Butterfly Print' ($18, depop), wardrobe=10 items
      out: Outfit 1: Pair the Y2K Baby Tee with the baggy straight-leg jeans, dark wash for a classic 2000s streetwear si…
[4] create_fit_card
      in:  outfit=<587 chars>, new_item=lst_002
      out: scored this butterfly print Y2K baby tee on depop for just $18.00 and I'm obsessed. paired it with baggy dark …
      →    done
```

**Empty search.** Two steps instead of four, because the branch stops it:

```
$ python app.py ask 'designer ballgown size XXS under $5' --trace
[1] parse_query
      in:  'designer ballgown size XXS under $5'
      out: description='designer ballgown', size='XXS', max_price=5.0
[2] search_listings (via MCP)
      in:  description='designer ballgown', size='XXS', max_price=5.0
      out: [] (empty)
      →    branch: empty → stop, suggest_outfit NOT called

  No listings matched 'designer ballgown' (size XXS, under $5). To find something, try: drop the size or try a neighbouring one (e.g. S/M, M/L); raise the price limit above $5; use fewer or more common words (e.g. 'graphic tee', 'denim jacket', 'boots').

0 model calls this session
```

**Failure modes, triggered on purpose (Milestone 2)**

| Failure | How I triggered it | What happened first | Handler now |
|---|---|---|---|
| Empty search | `python app.py ask 'designer ballgown size XXS under $5'` | Already handled in unit 3: stops after search, names each filter to loosen | unchanged, `agent.py::_no_results_message` |
| Empty wardrobe | `python app.py ask 'denim jacket under $50' --empty-wardrobe` | Already handled: `suggest_outfit` returns general advice ("layer the cropped light wash denim jacket over an oversized graphic black hoodie…"), card still written | unchanged, `tools.py::suggest_outfit` empty branch |
| Model unavailable | one character of the key changed, query not asked before (`leather boots under $60`) | **Not handled by the agent.** `run_agent` raised `ModelUnavailable` and never returned. The only reason the user saw `ModelUnavailable: The model rejected your API key…` instead of a traceback was `app.py`'s catch-all. The item the search found was thrown away, and `run_eval.py` would have logged a crash. | `agent.py::_model_down`, see below |

Model unavailable, after the handler:

```
[2] search_listings (via MCP)
      in:  description='leather boots', size=None, max_price=60.0
      out: 4 items: Leather Belt — Brown, Braided, Mini Shoulder Bag — Tan Leather, Suede Chelsea Boots — Tan … +1 more
      →    branch: 4 results → selected_item = first result
[3] suggest_outfit
      out: ModelUnavailable: The model rejected your API key. Check GEMINI_API_KEY in your .env file, or create a fresh k…
      →    model unreachable, stopping

  Found Leather Belt — Brown, Braided — $12.00 on thredUp, but the styling model couldn't be reached, so there's no outfit or fit card this time. The model rejected your API key. Check GEMINI_API_KEY in your .env file, or create a fresh key at aistudio.google.com. The search itself worked, so once that's sorted, run the same request again.
```

I also added a handler for a failure the MCP move introduced: the search server not starting. I forced it by pointing `mcp_client.SERVER` at a file that doesn't exist. Output: `The listings search couldn't be reached, so nothing was searched. Try again in a moment; if it keeps happening, run 'python mcp_client.py' to check the search server starts.`

The model-unavailable handler then fired for real, without me forcing it. The provider was overloaded during testing and returned `503 UNAVAILABLE`, and every one of those 14 calls in the before run ended in this message instead of a crash. That's also where the diagnosis above comes from.

**On the MCP move:** `search_listings` is registered in `mcp_server.py` with `@mcp.tool()`, with typed inputs (`description: str`, `size: str | None`, `max_price: float | None`) and a description written for an agent that can't see the code: units (US dollars, inclusive), the size-matching rule, every field returned, and the empty case (`[]`, never null or an error). In `agent.py::run_agent`, the direct `search_listings(...)` call became `call_tool("search_listings", {...})`, and the direct import was removed. **Nothing behaved differently:** `call_tool(...) == search_listings(...)` returned `True` for `vintage graphic tee` under $30, the impossible query still came back as `[]`, and the full query gave the same item and output as the unit 3 Sample Run. The only visible change is speed. Every call starts a server process, so search went from 0.5 ms (direct) to 539 ms (over MCP), measured on the same query.



---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:** One thing, in `generate.py::generate`, the single function both model-calling tools go through. A `503 UNAVAILABLE` / "overloaded" error is now treated as temporary, the same way a 429 already was: wait with exponential backoff (1, 2, 4, 8 s) and retry, up to `MAX_RETRIES` (5) attempts. If the last attempt still gets a 503, it raises `ModelUnavailable` as before, so the Milestone 2 handler still catches it. Every retry prints `[model overloaded (503)] … Waiting Ns`, so retries show up in the run output and can be counted. A bad key (401/400) still fails on the first attempt. I checked: the bad-key run still returns its message in 1.3 s.

**Which failure it was meant to fix:** The one the diagnosis found behind 7 of the 8 FAIL cells. A single 503 from an overloaded model ended the run, because the adapter never retried it. I picked it over rewriting the fit-card prompt because it accounted for 7 misses instead of 1, across three criteria.

### Run Log — After

Full log: [results/run_2026-10-13_2227_after.md](results/run_2026-10-13_2227_after.md) — `python run_eval.py --label after`, same scenarios, same 5 tries, cache off, temperature 0.9. Nothing else changed between the two runs.

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. Matching query completes all three tools | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. Impossible query stops before tool 2 | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. `selected_item` = item passed to `suggest_outfit` | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. Fit card: 2–4 sentences, title, exact price, platform, nothing contradicted | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 5. Nothing returned over `max_price` | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

**Before and after, side by side**

| Criterion | Target | Before | After |
|---|---|---|---|
| 1 | 4 of 5 | MET (4/5) | MET (5/5) |
| 2 | 5 of 5 | MET (5/5) | MET (5/5) |
| 3 | 5 of 5 | **MISSED (2/5)** | MET (5/5) |
| 4 | 4 of 5 | **MISSED (2/5)** | MET (5/5) |
| 5 | 5 of 5 | MET (5/5) | MET (5/5) |
| Tries that ended on a 503 (all scenarios) | — | 14 of 30 | 0 of 30 |

Real output from the after run, criterion 3 try 1 (the evidence that was missing before). Trace from `agent.py::run_agent`:
```
[2] search_listings (via MCP)
      →    branch: 5 results (prices $14–$75) → selected_item = lst_004
[3] suggest_outfit
      in:  new_item=lst_004 '90s Track Jacket — Navy/White Stripe' ($45, poshmark), wardrobe=10 items
```

Criterion 4, try 2, from `tools.py::create_fit_card`, 3 sentences:
```
Scored this Wrangler denim jacket on Poshmark for $42.00 and I'm already obsessed with the cropped fit. I love how it anchors a balanced double-denim streetwear look with a white ribbed tank and dark wash jeans, but it also works layered over an oversized grey crewneck and khaki trousers for a relaxed, minimal vibe. Finished both outfits with chunky white sneakers and my go-to black crossbody bag.
```

**Did it help, and how do I know:** Yes, for the failure it targeted. Tries ending on a 503 went from 14 of 30 to 0 of 30, and both misses became MET. The obvious objection is that the model was just less busy the second time. It wasn't: the after run printed **29** `[model overloaded (503)]` retries over 79 call attempts (37%), against 14 fatal 503s in 43 calls (33%) before. The load was about the same, and the retry absorbed every one.

Three honest limits on that result:
- **Criterion 4 is partly luck.** The fix removed the two 503 failures. The third failure, a one-sentence card, is a prompt problem the fix doesn't touch. It didn't happen in these five tries, but it happened **twice** in the diagnostic empty-wardrobe scenario of the same after run (tries 1 and 3, e.g. *"Scored this vintage Wrangler light-wash denim jacket on Poshmark for just $42.00, and it instantly pulled together my high-waisted black cargo pants, fitted white ribbed tank, and chunky sneakers for the ultimate effortless streetwear vibe. 👖✨"*). Across all 25 cards the after run produced, 2 were one sentence.
- **Criterion 3 passing is still indirect.** It passes now because `suggest_outfit` stopped failing, so its inputs got logged. The error path in `_model_down` still doesn't log `new_item`, so a run that gives up after 5 attempts would be unverifiable again.
- **It costs time and calls.** The after run used 79 call attempts against 43, and a busy model now makes a user wait up to ~15 s instead of getting an error at once. That's the right trade for a request that would otherwise fail, but it is a trade.

---

## What's Still Broken

Every criterion is MET in the after run, so nothing below is a *missed criterion*. These are the problems the test exposed that the targets don't catch, which is where I'd go next. Two of my targets were also easy: criteria 3 and 5 test deterministic code and can only catch a regression. The one I'd tighten is criterion 4, from "4 of 5" to "5 of 5 across all fit cards in the run log, including the diagnostic scenario", which would have caught the one-sentence cards above.

- **One-sentence fit cards (criterion 4's prompt problem).** 1 of 3 cards in the before run's criterion-4 scenario and 2 of 25 in the after run broke the 2–4 sentence rule. What I'd do: count sentences in `create_fit_card` after the call and regenerate once if there are fewer than 2, rather than just asking for it in the prompt. I stopped because the brief allows one change per unit, and the 503 retry fixed seven times as many failures.
- **Search ranks the wrong kind of item first.** `vintage jacket under $35` and `leather boots under $60` both select a *Leather Belt*. Per-keyword scoring lets a strong match on an adjective ("vintage", "leather") beat a weak match on the noun the user actually wants. What I'd do: add a criterion ("the selected item's category or title contains the noun in the query, 5 of 5") and weight the last keyword of the description higher in `tools.py::search_listings`. I stopped because no criterion of mine measures it, so I found it but couldn't score a fix.
- **The error path loses the evidence.** `agent.py::_model_down` doesn't log the `new_item` that went into the failed tool, so a run that still fails after 5 retries can't be scored on criterion 3. It's a one-line fix (pass `inputs=` to that `trace.step`). I left it because it would be a second change.
- **The model-down message shows the provider's raw JSON** (`{'error': {'code': 503, ...}}`) to the user, because `generate.py::_explain` has no friendly case for a 503. The user still knows what broke and what to do, but the JSON is noise. I'd add a 503 branch to `_explain` ("the model is busy right now, try again in a minute").
- **MCP adds about half a second per search**, because `mcp_client.call_tool` starts a fresh server process every call. That's fine for one search per run, but I'd hold one connection open if the agent ever searched more than once.



<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 3

       [ ] criteria.md has five numbered criteria, each with a target
       [ ] Each criterion has a reason underneath it
       [ ] All five unit 3 sections above have real content
       [ ] Tool Inventory: all three tools, inputs WITH TYPES, a specific
           return value, and the empty case
       [ ] Planning Loop names the branch rule and agent.py::run_agent
       [ ] Sample Run: one full query plus the three per-tool tests, as text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN, you submit the same one
           next unit

     SUBMISSION CHECKLIST — unit 4

       [ ] mcp_server.py exists with one tool registered
           (or a written record of exactly where the rewire broke)
       [ ] Run Log — Before, five criteria, five tries each
       [ ] Real output pasted underneath, naming file and function
       [ ] A verdict on every criterion
       [ ] A diagnosis for every miss, naming a place AND a mechanism
       [ ] Loop Trace, with the MCP call visible in it
       [ ] All three failure modes triggered and handled
       [ ] One improvement, with Run Log — After in the same format
       [ ] What's Still Broken
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository. Your commit history is what
     shows your criteria existed before your results did.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
