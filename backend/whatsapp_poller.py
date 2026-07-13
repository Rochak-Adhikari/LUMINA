import os
import asyncio
import re
import traceback
import urllib.request
from playwright.async_api import async_playwright
import google.genai as genai
from google.genai import types

CDP_PORT = int(os.environ.get("LUMINA_CDP_PORT", "9223"))
# By default, WhatsApp gateway is disabled. Set to 'true' in .env to enable.
LUMINA_WHATSAPP_GATEWAY = os.environ.get("LUMINA_WHATSAPP_GATEWAY", "false").lower() == "true"
LUMINA_WHATSAPP_AUTO_OPEN = os.environ.get("LUMINA_WHATSAPP_AUTO_OPEN", "true").lower() == "true"

# Cache of last seen message texts per contact to avoid double-processing
_last_seen_msg = {}

def _cdp_reachable() -> bool:
    """Quick check if Lumina's dedicated CDP endpoint is responding on port CDP_PORT."""
    try:
        req = urllib.request.urlopen(f"http://127.0.0.1:{CDP_PORT}/json/version", timeout=1)
        req.close()
        return True
    except Exception:
        return False

async def run_whatsapp_gateway():
    """Background task polling WhatsApp Web in Lumina's dedicated Brave instance."""
    if not LUMINA_WHATSAPP_GATEWAY:
        print("[WHATSAPP] Gateway disabled (LUMINA_WHATSAPP_GATEWAY=false).")
        return

    print("[WHATSAPP] Gateway background task starting...")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("[WHATSAPP] API key not found. Gateway disabled.")
        return

    client = genai.Client(http_options={"api_version": "v1beta"}, api_key=api_key)
    
    while True:
        try:
            if not _cdp_reachable():
                # Browser is not running at all, wait and check again
                await asyncio.sleep(8)
                continue

            async with async_playwright() as p:
                try:
                    browser = await p.chromium.connect_over_cdp(f"http://127.0.0.1:{CDP_PORT}")
                    contexts = browser.contexts
                    if not contexts:
                        await browser.close()
                        await asyncio.sleep(5)
                        continue
                    
                    context = contexts[0]
                    pages = context.pages
                    
                    # Find WhatsApp tab
                    wa_page = None
                    for page in pages:
                        if "web.whatsapp.com" in page.url:
                            wa_page = page
                            break
                    
                    if not wa_page and LUMINA_WHATSAPP_AUTO_OPEN:
                        # Auto-open WhatsApp Web in a new background tab if enabled
                        print("[WHATSAPP] WhatsApp Web tab not found. Launching WhatsApp Web...")
                        wa_page = await context.new_page()
                        await wa_page.goto("https://web.whatsapp.com")
                        # Give it time to load the login page / QR code
                        await asyncio.sleep(12)
                    
                    if wa_page:
                        # We are on the WhatsApp page, check and process unread messages
                        await poll_unread_messages(wa_page, client)
                        
                    await browser.close()
                except Exception as inner_e:
                    print(f"[WHATSAPP] Exception in Playwright session: {inner_e}")
            
        except Exception as e:
            print(f"[WHATSAPP] Exception in gateway loop: {e}")
            
        # Poll every 6 seconds to keep response time fast but avoid resource hogging
        await asyncio.sleep(6)

async def poll_unread_messages(page, client):
    try:
        # Check if we are logged in (look for pane-side or qr code)
        # WhatsApp Web has a canvas or element with class landing-wrapper for QR code
        qr_exists = await page.locator("canvas[aria-label*='Scan me'], div[data-ref*='qr']").count()
        if qr_exists > 0:
            # We are on the login screen, don't attempt to poll
            return

        # Locate unread badges
        # WhatsApp Web unread badges match label "unread" or class with unread properties
        badges = page.locator('span[aria-label*="unread"], span[aria-label*="Unread"], div[aria-label*="unread"]')
        count = await badges.count()
        if count == 0:
            return

        print(f"[WHATSAPP] Found {count} unread chat badges.")
        for i in range(count):
            try:
                badge = badges.nth(i)
                # Click the badge to open the chat window
                await badge.click()
                await asyncio.sleep(1.5) # Wait for conversation thread to populate

                # Get contact/sender name from the active chat header
                header_name_el = page.locator('header span[dir="auto"], div#main header span[dir="auto"]').first
                contact_name = await header_name_el.text_content() if await header_name_el.count() > 0 else "Unknown"
                contact_name = contact_name.strip()

                # Get the message elements in the open conversation
                # Incoming messages belong to div.message-in
                incoming_messages = page.locator('div.message-in')
                msg_count = await incoming_messages.count()
                if msg_count == 0:
                    continue

                # Read last incoming message text
                last_msg = incoming_messages.last
                text_el = last_msg.locator('span.selectable-text, div.copyable-text').first
                if await text_el.count() == 0:
                    continue
                msg_text = await text_el.text_content()
                msg_text = msg_text.strip() if msg_text else ""

                if not msg_text:
                    continue

                # Deduplicate and check if we have already replied
                if _last_seen_msg.get(contact_name) == msg_text:
                    continue

                print(f"[WHATSAPP] New message from '{contact_name}': {msg_text}")
                _last_seen_msg[contact_name] = msg_text

                # Generate dynamic reply from Lumina
                reply = await generate_lumina_reply(msg_text, contact_name, client)
                print(f"[WHATSAPP] Replying: {reply}")

                # Locate input box: div[contenteditable="true"][role="textbox"] (in div#main footer)
                input_field = page.locator('div[contenteditable="true"]').first
                # If there are multiple, look for textbox role
                textbox_input = page.locator('div[contenteditable="true"][role="textbox"]').first
                target_input = textbox_input if await textbox_input.count() > 0 else input_field

                if await target_input.count() > 0:
                    await target_input.focus()
                    await target_input.fill(reply)
                    await asyncio.sleep(0.5)
                    await target_input.press("Enter")
                    await asyncio.sleep(1.0)
                
            except Exception as inner_e:
                print(f"[WHATSAPP] Error parsing unread message {i}: {inner_e}")
                
    except Exception as e:
        print(f"[WHATSAPP] Error in poll_unread_messages: {e}")

async def generate_lumina_reply(text: str, sender: str, client) -> str:
    # Get system instruction
    from lumina import config
    system_instruction = getattr(config, "system_instruction", "")
    
    prompt = (
        f"{system_instruction}\n\n"
        f"[WHATSAPP MODE] You are chatting with Scepter (Rochak Adhikari) via WhatsApp text. "
        f"Generate a casual, warm, witty Gen-Z Neplish text reply (urban Nepali/English mix) matching your best friend persona. "
        f"Keep the reply concise (1-2 sentences max), without any markdown or code formatting since this is a real WhatsApp message.\n\n"
        f"Message from Scepter: {text}"
    )

    try:
        from lumina import MODEL
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=MODEL,
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        print(f"[WHATSAPP] Gemini generation error: {e}")
        return "Hey bro, reply garna milena k vo k vo... 😅"
