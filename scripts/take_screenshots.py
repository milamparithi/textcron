"""Take screenshots of the TextCron app for the README."""
import asyncio
from playwright.async_api import async_playwright

BASE = "http://localhost:80"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 900, "height": 700})

        # Helper: type text and click the Submit button (not "Translate another")
        async def submit(text: str):
            input_box = page.locator("textarea").first
            await input_box.fill(text)
            submit_btn = page.get_by_role("button", name="Translate", exact=True)
            await submit_btn.click()

        # 1. Home page (empty state)
        await page.goto(BASE)
        await page.wait_for_load_state("networkidle")
        await page.screenshot(path="docs/screenshots/home-empty.png", full_page=False)
        print("1/4 home-empty.png")

        # 2. Translated result
        await submit("every weekday at 3pm")
        await page.wait_for_selector("text=0 15 * * 1-5", timeout=15000)
        await page.wait_for_timeout(500)
        await page.screenshot(path="docs/screenshots/home-result.png", full_page=False)
        print("2/4 home-result.png")

        # 3. Warning example — frequent schedule
        await submit("every minute")
        await page.wait_for_timeout(5000)
        await page.screenshot(path="docs/screenshots/home-warning.png", full_page=False)
        print("3/4 home-warning.png")

        # Click "Translate another" to reset
        await page.get_by_role("button", name="Translate another").click()
        await page.wait_for_timeout(500)

        # 4. Error example — unsupported concept
        await submit("every fortnight")
        await page.wait_for_timeout(5000)
        await page.screenshot(path="docs/screenshots/home-error.png", full_page=False)
        print("4/4 home-error.png")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
