
from harness.tools.registry import register_tool

@register_tool(
    name="browser_fetch",
    description="Fetch page content via Playwright (headless browser).",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "selector": {"type": "string", "default": "body"},
        },
        "required": ["url"],
    },
)
def browser_fetch(url: str, selector: str = "body") -> str:
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=30000)
            element = page.query_selector(selector)
            text = element.inner_text() if element else page.content()
            browser.close()
            return text[:5000]
    except Exception as e:
        return f"Browser error: {e}"
