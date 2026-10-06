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

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Real output from one try**, pasted as text, naming the file and function
that produced it:

```

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

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 |  |  |  |  |
| 2 |  |  |  |  |
| 3 |  |  |  |  |
| 4 |  |  |  |  |
| 5 |  |  |  |  |

**Diagnoses**



---

## Loop Trace

<!-- One full run, printed step by step, with the MCP call visible in it.

     `python app.py ask '...' --trace` once you've added the trace.step()
     calls in Milestone 2.

     Worth pasting BOTH the happy path and the empty-search path. The empty
     one should be visibly shorter, because it stops. If your two traces are
     the same length, your branch isn't working — and this is the fastest way
     anyone will ever find that out. -->

**Happy path**

```

```

**Empty search**

```

```

**On the MCP move:** <!-- what changed in your code, and whether anything
behaved differently afterwards. If the rewire didn't work, say exactly where it
broke — the error text and the last thing that worked. That earns the point in
full. -->



---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:**

**Which failure it was meant to fix:**

### Run Log — After

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Did it help, and how do I know:**

<!-- If it made things worse, say that. Honestly reported, that earns full
     credit and is more interesting than one that worked. -->



---

## What's Still Broken

<!-- For each criterion still missed: what you'd do, and why you stopped where
     you did. "I ran out of time" is fine if it's true. Pretending nothing is
     left is not. -->



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
