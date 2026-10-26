"""Render a digest as Markdown: the quick brief links each citation to its full item."""


def _cites(cites):
    return " ".join(f"[{c}](#{c})" for c in cites or [])


def _reason(reason: dict, labels: dict) -> str:
    if reason.get("kind") == "breadth":
        return f"Breadth: {reason.get('text', '')}"
    label = labels.get(reason.get("interest_id"), reason.get("interest_id") or "interest")
    return f"Interest match ({label}): {reason.get('text', '')}"


def to_markdown(digest: dict, profile: dict | None = None) -> str:
    labels = {i["id"]: i["label"] for i in (profile or {}).get("interests", [])}
    brief = digest.get("brief", {})
    lines = [f"# Forager digest · {digest.get('date', '')}", "", "## Quick brief", ""]
    fields = {}
    for point in brief.get("points", []):
        fields.setdefault(point.get("field", "Other"), []).append(point)
    for field, points in fields.items():
        lines += [f"### {field}", ""]
        lines += [f"- {p['text']} {_cites(p.get('cites'))}" for p in points]
        lines.append("")
    if brief.get("connections"):
        lines += ["### Cross-field connections", ""]
        lines += [f"- {c['text']} {_cites(c.get('cites'))}" for c in brief["connections"]]
        lines.append("")
    if brief.get("changes"):
        lines += ["### Changes since last time", ""]
        lines += [f"- {c['text']} {_cites(c.get('cites'))}".rstrip() for c in brief["changes"]]
        lines.append("")
    lines += ["## Full items", ""]
    for item in digest.get("items", []):
        lines += [f'<a id="{item["id"]}"></a>', f"### {item['id']} · {item['title']}", "",
                  item.get("summary", ""), "",
                  f"- Source: [{item['url']}]({item['url']}) · {item.get('published', '')}",
                  f"- Why you see this: {_reason(item.get('reason', {}), labels)}", ""]
    if digest.get("checks"):
        lines += _checks(digest["checks"])
    return "\n".join(lines)


def _checks(checks: dict) -> list[str]:
    """How the digest was checked: code rules, uncovered interests and the Critic's review."""
    rules = "passed" if checks.get("rules_passed") else "not all passed"
    scope = "structure and citations" if checks.get("mode") == "single" else \
        "structure, citations, topic share, coverage and source mix"
    lines = ["## How this digest was checked", "", f"- Code rules ({scope}): {rules}."]
    lines += [f"- Not covered: {warning}" for warning in checks.get("warnings") or []]
    critic = checks.get("critic")
    if critic is None:
        return lines + [""]
    if critic.get("errors"):
        lines.append("- Critic: no usable review this time; the digest passed the code rules.")
    elif critic.get("verdict") == "PASS":
        lines.append("- Critic: no problems found.")
    else:
        outcome = ("the writer revised the digest once" if critic.get("revised") else
                   "the revision broke a code rule, so the checked draft is shown")
        lines.append(f"- Critic: {len(critic['issues'])} issue(s); {outcome}.")
        lines += [f"  - {issue['type'].replace('_', ' ')} ({', '.join(issue['refs'])}): {issue['explanation']}"
                  for issue in critic["issues"]]
    return lines + [""]
