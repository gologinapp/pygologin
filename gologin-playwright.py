import asyncio
from playwright.async_api import async_playwright
from gologin import GoLogin

async def main():
    gl = GoLogin({
		"token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2MzczNmY5N2YxZjBhMjBjNjI5NTVlYzIiLCJ0eXBlIjoiZGV2Iiwiand0aWQiOiI2NTJkNjAyOGRhNWUwOGYwZTI5NDUxMWYifQ.-8xBO_pxa84gBkDyp-wd-MOyPkw2lJ2wR5CCWkJaULE",
		"profile_id": "678f74573efa0d1f4444602f",
		})

    debugger_address = gl.start()
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://"+debugger_address)
        # default_context = browser.contexts[0]
        # page = default_context.pages[0]
        # await page.goto('https://gologin.com')
        # await page.screenshot(path="gologin.png")
        # await page.close()
    gl.stop()

asyncio.get_event_loop().run_until_complete(main())
