"""
The FitFindr planning loop.

This is the file that makes FitFindr an agent rather than a script. It decides
which tool to run next based on what the last one returned.

If your loop calls all three tools no matter what comes back, you have a list
of function calls. A loop looks at the last result before it picks the next
step. **That branch is the graded part of this unit.**

Build and test your three tools in `tools.py` first. Then come here.

    python agent.py          runs both example paths below
"""

import re

import config  # noqa: F401
import trace
from tools import suggest_outfit, create_fit_card
from generate import ModelUnavailable
from mcp_client import call_tool, MCPError


# ── session state ─────────────────────────────────────────────────────────────

def new_session(query: str, wardrobe: dict) -> dict:
    """
    A fresh session for one user interaction.

    The session is the single source of truth for a run. Every tool result goes
    in here, and the next tool reads it back out.

    You could pass values straight from one call to the next. It would work,
    and you would not be able to test it — you can't print a variable you have
    already overwritten. Going through the session is what makes the state
    visible, and unit 4 has you write a criterion about exactly that.

    Add fields if you need them.
    """
    return {
        "query": query,              # what the user typed
        "parsed": {},                # description / size / max_price you pulled out of it
        "search_results": [],        # everything search_listings returned
        "selected_item": None,       # the one you chose — goes into suggest_outfit
        "wardrobe": wardrobe,        # the user's wardrobe
        "outfit_input_item": None,   # the item suggest_outfit actually received (criterion 3)
        "outfit_suggestion": None,   # what suggest_outfit returned
        "fit_card": None,            # what create_fit_card returned
        "error": None,               # set when the run ended early
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Run the loop once and return the finished session.

    Args:
        query:    what the user asked for, in plain language
                  (e.g. "vintage graphic tee under $30, size M").
        wardrobe: a wardrobe dict — get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py.

    Returns:
        The session dict. **Check session["error"] first** — if it isn't None,
        the run ended early and the later fields will still be None.

    ─────────────────────────────────────────────────────────────────────────
    TODO — build this, following the branch rule you wrote in Milestone 2.

      1. Start a session with new_session().

      2. Count the times round the loop, and call trace.check_iterations(count)
         on each one before you go again. It raises when the count passes
         MAX_ITERATIONS in config.py — see trace.py.

      3. Parse the query into a description, a size, and a max_price. Regex,
         string splitting, or asking the model are all fine — say which you
         chose in your README. Put the result in session["parsed"].

      4. Call search_listings() with what you parsed.
         Put the results in session["search_results"].

         ⚠️ THIS IS THE BRANCH. If nothing came back:
              - put a message in session["error"] saying what the user could
                change — "No results" is not that message
              - return the session
              - do NOT call suggest_outfit with nothing

      5. Choose an item — the first result is fine. Put it in
         session["selected_item"].

      6. Call suggest_outfit() with the selected item and the wardrobe.
         Put the result in session["outfit_suggestion"].

      7. Call create_fit_card() with the outfit and the item.
         Put the result in session["fit_card"].

      8. Return the session.

    ─────────────────────────────────────────────────────────────────────────
    IN UNIT 4 you come back and add two things:

      • Trace calls. One per step. `trace.step("search_listings", inputs=...,
        returned=...)` — see trace.py. Your README needs the output.

      • A handler for ModelUnavailable, so a bad key produces a message rather
        than a stack trace. The import is already at the top of this file.
    """
    session = new_session(query, wardrobe)
    session["parsed"] = parse_query(query)
    trace.step("parse_query", inputs=repr(query), returned=_kv(session["parsed"]))

    next_step = "search"
    count = 0
    while next_step != "done":
        count += 1
        trace.check_iterations(count)

        if next_step == "search":
            p = session["parsed"]
            args = {"description": p["description"], "size": p["size"], "max_price": p["max_price"]}
            # search_listings runs behind MCP now (mcp_server.py), not as a direct call.
            try:
                session["search_results"] = call_tool("search_listings", args)
            except MCPError as exc:
                trace.step("search_listings (via MCP)", inputs=_kv(args), returned=f"MCPError: {exc}",
                           note="branch: search server unreachable, stopping")
                session["error"] = (
                    "The listings search couldn't be reached, so nothing was searched. "
                    "Try again in a moment; if it keeps happening, run "
                    "`python mcp_client.py` to check the search server starts."
                )
                return session

            # THE BRANCH: nothing found means stop here, before suggest_outfit.
            if not session["search_results"]:
                session["error"] = _no_results_message(p)
                next_step = "done"
                note = "branch: empty → stop, suggest_outfit NOT called"
            else:
                session["selected_item"] = session["search_results"][0]
                next_step = "suggest"
                prices = [r["price"] for r in session["search_results"]]
                note = (f"branch: {len(prices)} results (prices ${min(prices):g}–${max(prices):g}) "
                        f"→ selected_item = {session['selected_item']['id']}")
            trace.step("search_listings (via MCP)", inputs=_kv(args),
                       returned=session["search_results"], note=note)

        elif next_step == "suggest":
            item = session["selected_item"]
            session["outfit_input_item"] = item
            n_owned = len((session["wardrobe"] or {}).get("items") or [])
            try:
                session["outfit_suggestion"] = suggest_outfit(item, session["wardrobe"])
            except ModelUnavailable as exc:
                return _model_down(session, "suggest_outfit", exc)
            trace.step("suggest_outfit",
                       inputs=f"new_item={item['id']} {item['title']!r} (${item['price']:g}, "
                              f"{item['platform']}), wardrobe={n_owned} items",
                       returned=session["outfit_suggestion"],
                       note="empty wardrobe → general advice" if n_owned == 0 else "")
            next_step = "fit_card"

        elif next_step == "fit_card":
            try:
                session["fit_card"] = create_fit_card(
                    session["outfit_suggestion"], session["selected_item"]
                )
            except ModelUnavailable as exc:
                return _model_down(session, "create_fit_card", exc)
            trace.step("create_fit_card",
                       inputs=f"outfit=<{len(session['outfit_suggestion'])} chars>, "
                              f"new_item={session['selected_item']['id']}",
                       returned=session["fit_card"], note="done")
            next_step = "done"

    return session


def _model_down(session: dict, tool: str, exc: Exception) -> dict:
    """
    The model couldn't be reached. Stop, keep what the search already found, and
    tell the user what broke and what to try — instead of a stack trace.
    """
    item = session["selected_item"]
    trace.step(tool, returned=f"ModelUnavailable: {exc}", note="model unreachable, stopping")
    session["error"] = (
        f"Found {item['title']} — ${item['price']:.2f} on {item['platform']}, but the styling "
        f"model couldn't be reached, so there's no outfit or fit card this time. "
        f"{exc} The search itself worked, so once that's sorted, run the same "
        f"request again."
    )
    return session


def _kv(d: dict) -> str:
    """Show a small dict in full in the trace (trace.py shortens dicts to their keys)."""
    return ", ".join(f"{k}={v!r}" for k, v in d.items())


# ── query parsing ─────────────────────────────────────────────────────────────

_PRICE_PATTERNS = [
    r"(?:under|below|less than|max|up to|<=?)\s*\$?\s*(\d+(?:\.\d+)?)",
    r"\$\s*(\d+(?:\.\d+)?)\s*(?:or less|max|and under)",
]
_SIZE_PATTERN = r"\bsize\s+([a-z0-9./]+(?:\s*/\s*[a-z0-9.]+)?)"
_FILLER = r"\b(?:i'?m|i am|looking for|i want|i need|find me|show me|something|please)\b"


def parse_query(query: str) -> dict:
    """
    Pull a description, size and max_price out of a plain-language query, by regex.

    'vintage graphic tee under $30, size M'
        → {'description': 'vintage graphic tee', 'size': 'M', 'max_price': 30.0}
    """
    text = query.lower()

    max_price = None
    for pattern in _PRICE_PATTERNS:
        match = re.search(pattern, text)
        if match:
            max_price = float(match.group(1))
            text = text[: match.start()] + " " + text[match.end():]
            break

    size = None
    match = re.search(_SIZE_PATTERN, text)
    if match:
        size = match.group(1).upper()
        text = text[: match.start()] + " " + text[match.end():]

    text = re.sub(_FILLER, " ", text)
    description = " ".join(re.sub(r"[^a-z0-9'\- ]", " ", text).split())
    return {"description": description, "size": size, "max_price": max_price}


def _no_results_message(parsed: dict) -> str:
    """Say what was searched and which part of it to loosen — not just 'No results'."""
    searched = f"'{parsed['description']}'" if parsed["description"] else "an empty description"
    filters, tips = [], []
    if parsed["size"]:
        filters.append(f"size {parsed['size']}")
        tips.append("drop the size or try a neighbouring one (e.g. S/M, M/L)")
    if parsed["max_price"] is not None:
        filters.append(f"under ${parsed['max_price']:g}")
        tips.append(f"raise the price limit above ${parsed['max_price']:g}")
    tips.append("use fewer or more common words (e.g. 'graphic tee', 'denim jacket', 'boots')")

    where = f" ({', '.join(filters)})" if filters else ""
    return (
        f"No listings matched {searched}{where}. "
        f"To find something, try: {'; '.join(tips)}."
    )


# ── running it directly ───────────────────────────────────────────────────────

def _show(session: dict) -> None:
    if session["error"]:
        print(f"  stopped: {session['error']}")
        print(f"  fit_card is {session['fit_card']!r} — it should still be None here")
        return

    item = session["selected_item"] or {}
    print(f"  found:    {item.get('title')} — ${item.get('price')} on {item.get('platform')}")
    print(f"  outfit:   {session['outfit_suggestion']}")
    print(f"  fit card: {session['fit_card']}")


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== A query the data can match ===")
    _show(run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    ))

    print("\n=== A query it can't ===")
    _show(run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    ))

    print(
        "\nThe second one should stop before the fit card. If both paths look "
        "the same,\nthe branch isn't doing anything yet."
    )
