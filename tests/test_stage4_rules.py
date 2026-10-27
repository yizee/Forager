"""Stage 4 code rules: topic share, 7-day coverage, source-type mix (no model involved)."""

from forager.checks import check_coverage, check_headings, check_rules, check_source_mix, check_topic_share, rule_errors

TODAY = "2026-10-25"


def profile():
    interest = lambda n, kind="long_term", expires=None: {
        "id": f"i{n}", "label": f"interest {n}", "type": kind, "source": "stated", "weight": 1.0, "expires": expires}
    return {"interests": [interest(1), interest(2), interest(3, "short_term", "2026-11-08")]}


def item(n, interest=None, kind="paper"):
    reason = {"kind": "interest", "interest_id": interest, "text": "match"} if interest else {"kind": "breadth", "text": "nearby"}
    return {"id": f"x{n:02d}", "type": kind, "summary": "s", "reason": reason}


def digest(items):
    return {"date": TODAY, "items": items, "brief": {
        "points": [{"text": f"Point {n}.", "field": "f", "cites": [items[n % len(items)]["id"]]} for n in range(5)],
        "connections": [], "changes": []}}


def test_topic_share_limit_is_forty_percent_per_bucket():
    at_limit = [item(1, "i1"), item(2, "i1"), item(3, "i2"), item(4), item(5, "i2")]   # i1: 2 of 5 = 40%
    assert check_topic_share(digest(at_limit)) == []
    over = at_limit + [item(6, "i1"), item(7)]                                          # i1: 3 of 7 = 43%
    assert check_topic_share(digest(over)) == ["'i1' has 3 of 7 items (43%); the limit is 40%."]
    breadth_heavy = [item(1), item(2), item(3), item(4, "i1"), item(5, "i2")]         # breadth: 3 of 5
    assert check_topic_share(digest(breadth_heavy)) == ["'breadth' has 3 of 5 items (60%); the limit is 40%."]
    assert check_topic_share(digest([item(1, "i1"), item(2, "i1")])) == []             # too few items to judge


def test_coverage_uses_the_last_seven_days_and_ignores_short_term():
    only_i1 = digest([item(1, "i1"), item(2)])
    assert check_coverage(only_i1, profile(), today=TODAY) == [
        "Long-term interest 'interest 2' (i2) has no item in the last 7 days."]
    recent = [{"date": "2026-10-19", "items": [item(9, "i2")]}]          # 6 days ago: inside the window
    stale = [{"date": "2026-10-18", "items": [item(9, "i2")]}]           # 7 days ago: outside
    assert check_coverage(only_i1, profile(), recent, TODAY) == []
    assert len(check_coverage(only_i1, profile(), stale, TODAY)) == 1


def test_source_mix_applies_only_when_several_types_are_available():
    papers = digest([item(1, "i1"), item(2, "i2")])
    assert check_source_mix(papers, ["paper"]) == []
    assert check_source_mix(papers, ["paper", "repo"]) == ["All items are of type paper; use at least two of: paper, repo."]
    assert check_source_mix(digest([item(1, "i1"), item(2, "i2", "repo")]), ["paper", "repo"]) == []


def test_an_interest_heading_needs_an_item_matched_to_that_interest():
    d = digest([item(1, "i1"), item(2), item(3, "i2")])
    d["brief"]["points"] = [
        {"text": "a", "field": "interest 1", "cites": ["x01"]},            # matched: fine
        {"text": "b", "field": "INTEREST  1", "cites": ["x02"]},           # a breadth item under i1's label
        {"text": "c", "field": "interest 2", "cites": ["x01"]},            # an item matched to another interest
        {"text": "d", "field": "interest 2", "cites": ["x02", "x03"]},     # one matching item is enough
        {"text": "e", "field": "Nearby tools", "cites": ["x02"]}]          # an area name claims no interest
    problems = check_headings(d, profile()["interests"])
    assert problems[0] == ("brief.points[1] is under the heading 'INTEREST  1', an interest's label, but none of "
                           "the items it cites matches that interest. Put the point under a short area name instead.")
    assert len(problems) == 2 and problems[1].startswith("brief.points[2] is under the heading 'interest 2'")
    malformed = {"items": "x", "brief": {"points": ["x", {"field": "interest 1", "cites": [["x01"]]}]}}
    assert len(check_headings(malformed, profile()["interests"])) == 1     # reported, not a crash


def test_check_rules_reports_by_rule():
    d = digest([item(n, "i1") for n in range(1, 6)])
    results = check_rules(d, profile(), {i["id"] for i in d["items"]}, available_types=["paper", "news"], today=TODAY)
    assert set(results) == {"structure_and_citations", "topic_share", "coverage", "source_mix"}
    assert results["structure_and_citations"] == [] and results["topic_share"] and results["coverage"]
    assert results["source_mix"] and len(rule_errors(results)) == 3
