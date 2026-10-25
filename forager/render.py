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
    return "\n".join(lines)
