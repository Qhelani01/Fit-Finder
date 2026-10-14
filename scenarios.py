"""
The runs your test needs. ← UNIT 4, MILESTONE 3

Each of your five criteria needs something run against it. A criterion about
the empty-search branch needs an impossible query. One about the fit card needs
the same item run more than once. Working that out is Milestone 3's first step,
and this file is where you write it down.

`run_eval.py` runs everything here five times and writes the run log — five
because your criteria are written out of five.

Three scenarios are filled in to show the shape. Add or change whatever your
own criteria need — these are a starting point, not a fixed set.
"""

SCENARIOS = [
    {
        # A query the data can match. Criterion 1.
        "name": "matching query completes",
        "query": "vintage graphic tee under $30",
        "wardrobe": "example",
        "criterion": 1,
    },
    {
        # A query nothing can match. Criterion 2 — the branch.
        "name": "impossible query stops early",
        "query": "designer ballgown size XXS under $5",
        "wardrobe": "example",
        "criterion": 2,
    },
    {
        # Criterion 3 — state. A different item from criterion 1 (lst_004, $75,
        # depop, branded), with a size filter. The trace records selected_item's
        # id/price/platform at the search step and what suggest_outfit received.
        "name": "selected item is the item passed on",
        "query": "90s track jacket in size M",
        "wardrobe": "example",
        "criterion": 3,
    },
    {
        # Criterion 4 — fit card. The same item (lst_007, Wrangler, $42,
        # poshmark) five times, so the only thing that varies is the model.
        # It has a brand, so a wrong-brand claim is checkable.
        "name": "fit card states title, price, platform",
        "query": "denim jacket under $50",
        "wardrobe": "example",
        "criterion": 4,
    },
    {
        # Criterion 5 — price ceiling. Chosen because 3 listings match the
        # keywords but cost more than $35, so the filter has something to drop.
        # "vintage graphic tee under $30" has no over-limit matches and would
        # pass even with the filter deleted.
        "name": "nothing returned over max_price",
        "query": "vintage jacket under $35",
        "wardrobe": "example",
        "criterion": 5,
    },
    {
        # A user with nothing saved. One of unit 4's three failure modes.
        "name": "empty wardrobe",
        "query": "denim jacket under $50",
        "wardrobe": "empty",
        "criterion": None,
    },
]

WARDROBES = ("example", "empty")


def validate() -> list[str]:
    """Complain about anything malformed, before a long run rather than during."""
    problems = []
    for i, scenario in enumerate(SCENARIOS, 1):
        if not scenario.get("query", "").strip():
            problems.append(f"scenario {i} has no query")
        if scenario.get("wardrobe") not in WARDROBES:
            problems.append(
                f"scenario {i} has wardrobe {scenario.get('wardrobe')!r} — "
                f"it should be one of {WARDROBES}"
            )
    return problems
