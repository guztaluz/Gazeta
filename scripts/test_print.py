"""End-to-end smoke test of the renderer + driver — no real printer needed."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.printer.driver import get_driver
from src.printer.renderer import render_html_to_png


SAMPLE_HTML = """
{% extends "_base.html.j2" %}
{% block content %}
<h1>Hello Gustavo</h1>
<div class="meta">{{ date }}</div>
<hr class="rule">
<p>{{ body }}</p>
<hr class="rule">
<div class="footer">
  <div class="row"><span>BTC</span><span class="strong">$ 64,200 ▲</span></div>
  <div class="row"><span>ETH</span><span class="strong">$ 3,180 ▼</span></div>
</div>
{% endblock %}
"""


async def main() -> None:
    from datetime import date
    from jinja2 import Environment, BaseLoader, FileSystemLoader, ChoiceLoader

    project_root = Path(__file__).resolve().parent.parent
    env = Environment(
        loader=ChoiceLoader([
            FileSystemLoader(project_root / "src" / "templates"),
        ]),
    )
    html = env.from_string(SAMPLE_HTML).render(
        date=date.today().strftime("%A, %d %b %Y"),
        body=(
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
            "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. "
            "Ut enim ad minim veniam, quis nostrud exercitation ullamco."
        ),
    )

    png = await render_html_to_png(html)
    driver = get_driver()
    path = await driver.print(png)
    print(f"Wrote {path} ({len(png)} bytes)")


if __name__ == "__main__":
    asyncio.run(main())
