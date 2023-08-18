import asyncio
from playwright.async_api import async_playwright
from gologin import GoLogin

async def main():
    gl = GoLogin({
		"token": "yU0token",
		"profile_id": "yU0Pr0f1leiD",
		})

    debugger_address = gl.start()
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://"+debugger_address)
        default_context = browser.contexts[0]
        page = default_context.pages[0]
        await page.goto('https://gologin.com')
        await page.screenshot(path="gologin.png")
        await page.close()
    gl.stop()

asyncio.get_event_loop().run_until_complete(main())
