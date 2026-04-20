"""
Lumina tool declarations — Gemini Live function_declarations registry.

This package also contains submodules:
  - tools.browser_control: Phase T1 Browser Controller (headless)
  - tools.local_browser_control: Phase T2 Local Brave Controller (CDP, visible)
"""

generate_cad_prototype_tool = {
    "name": "generate_cad_prototype",
    "description": "Generates a 3D wireframe prototype based on a user's description. Use this when the user asks to 'visualize', 'prototype', 'create a wireframe', or 'design' something in 3D.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "prompt": {
                "type": "STRING",
                "description": "The user's description of the object to prototype."
            }
        },
        "required": ["prompt"]
    }
}




write_file_tool = {
    "name": "write_file",
    "description": "Writes content to a file at the specified path. Overwrites if exists.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "path": {
                "type": "STRING",
                "description": "The path of the file to write to."
            },
            "content": {
                "type": "STRING",
                "description": "The content to write to the file."
            }
        },
        "required": ["path", "content"]
    }
}

read_directory_tool = {
    "name": "read_directory",
    "description": "Lists the contents of a directory.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "path": {
                "type": "STRING",
                "description": "The path of the directory to list."
            }
        },
        "required": ["path"]
    }
}

read_file_tool = {
    "name": "read_file",
    "description": "Reads the content of a file.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "path": {
                "type": "STRING",
                "description": "The path of the file to read."
            }
        },
        "required": ["path"]
    }
}

# Phase T1: Browser control — single high-level tool for safe browser interaction
browser_control_tool = {
    "name": "browser_control",
    "description": "Controls a browser to perform web actions. Use when the user asks to open a website, search the web, read a page, take a screenshot, or interact with web content. Supported intents: open_url, search_google, click_text, type_into_focused, send_keys, read_page_summary, screenshot, login_flow_placeholder.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "intent": {
                "type": "STRING",
                "description": "The high-level action intent. One of: open_url, search_google, click_text, type_into_focused, send_keys, read_page_summary, screenshot, login_flow_placeholder."
            },
            "params": {
                "type": "STRING",
                "description": "JSON-encoded parameters for the intent. Examples: {\"url\": \"https://example.com\"} for open_url, {\"query\": \"weather today\"} for search_google, {\"text\": \"Submit\"} for click_text, {\"keys\": \"Enter\"} for send_keys, {\"site\": \"github.com\"} for login_flow_placeholder."
            }
        },
        "required": ["intent", "params"]
    }
}

# Phase T2+: Local browser control — CDP-based visible Brave browser
local_browser_control_tool = {
    "name": "local_browser_control",
    "description": (
        "Controls Lumina's dedicated Brave browser via CDP for on-page DOM interaction. "
        "Use ONLY when the user explicitly asks to interact with the current browser tab: "
        "clicking elements, filling forms, reading live page content, inspecting browser state, "
        "analyzing the current browser screen, or scrolling/navigating within a loaded page.\n"
        "Do NOT use this for: opening websites, searching Google, opening YouTube, "
        "opening Spotify, playing music, or any task that can be handled by browser_open, "
        "youtube_control, or open_app.\n"
        "Do NOT call this alongside other tools for a single request.\n"
        "DECISION ORDER for clicking: 1) click_text, 2) click_best, 3) get_clickables, "
        "4) screenshot, 5) click_at.\n"
        "Actions:\n"
        "  open_url — navigate ({\"url\": \"https://...\"})\n"
        "  new_tab — open a new tab, optionally with URL\n"
        "  click_text — click by visible text ({\"text\": \"Messages\"})\n"
        "  click_best — strict click with tag/area preference "
        "({\"query\": \"Submit\", \"prefer\": [\"button\",\"a\"], \"area\": \"bottom\"})\n"
        "  get_clickables — list visible interactive elements ({})\n"
        "  analyze_screen — structured DOM state: clickables, inputs, headings, errors ({})\n"
        "  focus_textbox — find and focus a text input ({\"hint\": \"search\"} or {})\n"
        "  type_text — type into focused element ({\"text\": \"lo-fi\", \"mode\": \"replace\"})\n"
        "  press_keys — send keys like Enter, Tab, Ctrl+L ({\"keys\": \"Enter\"})\n"
        "  scroll — scroll page ({\"direction\": \"down\", \"amount\": 500})\n"
        "  wait_for_text — wait for text to appear ({\"text\": \"Results\"})\n"
        "  get_active_state — tab index, url, title, loading, viewport ({})\n"
        "  list_tabs, switch_tab, close_tab — tab management\n"
        "  screenshot — capture current tab ({})\n"
        "  play_pause — toggle media playback in the CURRENTLY OPEN controlled browser tab ({})\n"
        "  click_at — click at coordinates, last resort ({\"x\": 500, \"y\": 300})\n"
        "  go_back, go_forward, reload, get_state — navigation.\n"
        "SAFETY: Clicking dangerous-text buttons (send, post, submit, delete, pay, login) "
        "always requires confirmation."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": (
                    "The action to perform. One of: open_url, new_tab, click_text, click_best, "
                    "get_clickables, analyze_screen, focus_textbox, type_text, press_keys, scroll, "
                    "wait_for_text, get_active_state, list_tabs, switch_tab, close_tab, screenshot, "
                    "play_pause, click_at, click_selector, go_back, go_forward, reload, get_state."
                )
            },
            "params": {
                "type": "STRING",
                "description": (
                    "JSON-encoded parameters. Examples: "
                    "{\"url\": \"https://youtube.com\"} for open_url/new_tab, "
                    "{\"text\": \"Messages\"} for click_text, "
                    "{\"query\": \"Submit\", \"prefer\": [\"button\"], \"area\": \"bottom\"} for click_best, "
                    "{\"hint\": \"search\"} for focus_textbox, "
                    "{\"text\": \"hello\", \"mode\": \"append\"} for type_text, "
                    "{\"keys\": \"Enter\"} for press_keys, "
                    "{\"direction\": \"down\", \"amount\": 500} for scroll, "
                    "{\"text\": \"Results\", \"timeout_ms\": 5000} for wait_for_text, "
                    "{\"index\": 1} for switch_tab/close_tab, "
                    "{} for get_clickables/analyze_screen/screenshot/list_tabs/get_active_state/play_pause."
                )
            }
        },
        "required": ["action", "params"]
    }
}


# ── Phase M: Mark-XXX Integrated Action Tools ──────────────────────────────────

cmd_control_tool = {
    "name": "cmd_control",
    "description": (
        "Execute a shell/CMD task or command on the user's computer. "
        "Use for system info (IP, disk space, memory), running programs, installing packages, "
        "checking processes, or any terminal command. Can take a natural language description "
        "and generate the command via AI, or run a direct command."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "task":    {"type": "STRING", "description": "Natural language description of what to do (Gemini generates the command)."},
            "command": {"type": "STRING", "description": "Optional: Direct shell command to run instead of generating one."},
            "visible": {"type": "BOOLEAN", "description": "If true (default), opens a visible terminal. If false, runs silently."},
        },
        "required": []
    }
}

file_controller_tool = {
    "name": "file_controller",
    "description": (
        "Manage files and folders on the user's computer. "
        "Supports: list (show files), create_file, create_folder, delete, move, copy, "
        "rename, read (read file content), write, find (search files), "
        "largest (biggest files), disk_usage, info (file details). "
        "Paths support shortcuts: desktop, downloads, documents, pictures, home."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action":      {"type": "STRING", "description": "Action: list|create_file|create_folder|delete|move|copy|rename|read|write|find|largest|disk_usage|info"},
            "path":        {"type": "STRING", "description": "Target path or shortcut (desktop, downloads, documents, home, pictures)."},
            "name":        {"type": "STRING", "description": "File or folder name."},
            "content":     {"type": "STRING", "description": "File content for write/create_file."},
            "destination": {"type": "STRING", "description": "Target path for move/copy."},
            "new_name":    {"type": "STRING", "description": "New name for rename."},
            "extension":   {"type": "STRING", "description": "File extension filter for find (e.g. '.pdf')."},
            "max_results": {"type": "INTEGER", "description": "Max results for find (default 20)."},
            "append":      {"type": "BOOLEAN", "description": "If true, append to existing file instead of overwriting."},
        },
        "required": ["action"]
    }
}

computer_control_tool = {
    "name": "computer_control",
    "description": (
        "Control the computer using mouse, keyboard, and screen automation via PyAutoGUI. "
        "Use for UI automation: clicking elements, typing text, keyboard shortcuts, "
        "scrolling, taking screenshots, dragging, finding elements on screen with AI vision. "
        "Actions: type, smart_type, click, double_click, right_click, move, drag, hotkey, "
        "press, scroll, copy, paste, screenshot, wait, clear_field, focus_window, "
        "screen_size, screen_find (AI-powered), screen_click (AI-powered), "
        "random_data, user_data."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action":      {"type": "STRING", "description": "Action to perform (type, click, hotkey, press, scroll, screenshot, etc.)"},
            "text":        {"type": "STRING", "description": "Text to type (for type/smart_type)."},
            "x":           {"type": "INTEGER", "description": "X coordinate for click/move."},
            "y":           {"type": "INTEGER", "description": "Y coordinate for click/move."},
            "keys":        {"type": "STRING", "description": "Keys for hotkey, e.g. 'ctrl+c' or 'win+d'."},
            "key":         {"type": "STRING", "description": "Single key name for press action."},
            "direction":   {"type": "STRING", "description": "Scroll direction: up|down|left|right."},
            "amount":      {"type": "INTEGER", "description": "Scroll amount (default 3)."},
            "description": {"type": "STRING", "description": "Element description for screen_find/screen_click."},
            "seconds":     {"type": "NUMBER", "description": "Seconds to wait (for wait action)."},
            "title":       {"type": "STRING", "description": "Window title for focus_window."},
            "type":        {"type": "STRING", "description": "Data type for random_data: name|email|username|password|phone|birthday|address|zip_code|city."},
            "field":       {"type": "STRING", "description": "Profile field for user_data (same values as type)."},
            "path":        {"type": "STRING", "description": "Save path for screenshot."},
        },
        "required": ["action"]
    }
}

computer_settings_tool = {
    "name": "computer_settings",
    "description": (
        "Control computer UI settings: volume (up/down/mute/set), brightness, window management "
        "(minimize/maximize/fullscreen/snap), screen sleep, dark mode, WiFi toggle, "
        "browser shortcuts (new tab/close tab/refresh/zoom/find), clipboard (copy/paste/cut/undo), "
        "file explorer, task manager, lock screen, screenshot, and more. "
        "Accepts natural language descriptions in any language."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action":      {"type": "STRING", "description": "Specific action name (e.g. volume_up, mute, close_app, full_screen). Optional if description is provided."},
            "description": {"type": "STRING", "description": "Natural language command in any language (e.g. 'turn up the volume', 'minimize this window')."},
            "value":       {"type": "STRING", "description": "Optional value: volume level (0-100), text to type, repeat count, or key name."},
        },
        "required": []
    }
}

open_app_tool = {
    "name": "open_app",
    "description": (
        "Open, close, focus, or check if an application is running on the desktop. "
        "Use ONLY when the user explicitly asks to open, close, or focus a specific desktop app. "
        "Examples: 'open Discord', 'open Spotify', 'open VS Code', 'open Telegram', 'open Notepad'. "
        "Do NOT call this alongside browser_open or youtube_control for the same request. "
        "Do NOT call this speculatively — only when the user names a specific app to open."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "app":    {"type": "STRING", "description": "Application name (e.g. 'notepad', 'spotify', 'chrome')."},
            "action": {"type": "STRING", "description": "Action: 'open' (default) | 'close' | 'focus' | 'check'."},
        },
        "required": ["app"]
    }
}

send_message_tool = {
    "name": "send_message",
    "description": (
        "Send a message via WhatsApp, Telegram, or Instagram using browser automation. "
        "Opens the web version of the messaging app and sends the message. "
        "The user must be logged in to the platform in their browser. "
        "For WhatsApp, use international phone format (+1234567890) or contact name."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "platform": {"type": "STRING", "description": "Platform: 'whatsapp' (default) | 'telegram' | 'instagram'."},
            "contact":  {"type": "STRING", "description": "Contact name, username, or phone number."},
            "message":  {"type": "STRING", "description": "Message text to send."},
        },
        "required": ["contact", "message"]
    }
}

web_search_tool = {
    "name": "web_search",
    "description": (
        "Search the web and return a direct answer. Uses Gemini AI for comprehensive answers, "
        "with DuckDuckGo as fallback. Good for: current events, factual questions, news, "
        "prices, weather, historical facts, how-to questions. "
        "For most queries, prefer this over browser tools for speed."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "query":        {"type": "STRING", "description": "Search query."},
            "mode":         {"type": "STRING", "description": "Search mode: 'gemini' (default AI answer) | 'ddg' (DuckDuckGo) | 'browser' (open browser)."},
            "open_browser": {"type": "BOOLEAN", "description": "Also open results in browser alongside returning answer (default false)."},
        },
        "required": ["query"]
    }
}

weather_tool = {
    "name": "weather",
    "description": (
        "Check the weather for a location by opening weather information in the browser. "
        "Supports any city, country, zip code, or 'my location'. "
        "Sources: google (default), weather.com, wttr.in, openweather, accuweather."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "location": {"type": "STRING", "description": "City, country, or zip code (default: 'my location')."},
            "source":   {"type": "STRING", "description": "Weather source: 'google' (default) | 'weather.com' | 'wttr' | 'openweather' | 'accuweather'."},
        },
        "required": []
    }
}

system_reminder_tool = {
    "name": "system_reminder",
    "description": (
        "Set, list, or delete system-level reminders using Windows Task Scheduler. "
        "Reminders show a popup notification at the specified time. "
        "For calendar/event reminders in the app, use the events panel instead. "
        "This tool is best for one-off reminders like 'in 30 minutes' or 'tomorrow 9am'."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action":  {"type": "STRING", "description": "Action: 'set' (default) | 'delete' | 'list'."},
            "title":   {"type": "STRING", "description": "Reminder title/label."},
            "time":    {"type": "STRING", "description": "When to remind: 'in 30 minutes', 'tomorrow 9am', '3:30 PM', '2 hours'."},
            "message": {"type": "STRING", "description": "Popup message text (defaults to title)."},
        },
        "required": []
    }
}

screen_process_tool = {
    "name": "screen_process",
    "description": (
        "Analyze the current screen or camera feed using Gemini AI vision. "
        "Use 'screenshot' to describe what's on screen, answer questions about visible content, "
        "or help with UI navigation. Use 'camera' to see through the webcam. "
        "Use 'chat' for multi-turn conversation about the screen."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "Action: 'screenshot' (default) | 'camera' | 'chat' | 'reset'."},
            "prompt": {"type": "STRING", "description": "Question or instruction about what to look for on screen."},
        },
        "required": []
    }
}

desktop_control_tool = {
    "name": "desktop_control",
    "description": (
        "Manage the Windows desktop: set wallpaper, organize files by type or date, "
        "clean desktop (archive all to a folder), list desktop contents, get stats, "
        "or perform AI-powered custom desktop tasks using PyAutoGUI. "
        "Actions: wallpaper, wallpaper_url, current_wallpaper, organize, clean, list, stats, task."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "Action: wallpaper|wallpaper_url|current_wallpaper|organize|clean|list|stats|task."},
            "path":   {"type": "STRING", "description": "Image file path for 'wallpaper' action."},
            "url":    {"type": "STRING", "description": "Image URL for 'wallpaper_url' action."},
            "mode":   {"type": "STRING", "description": "Organize mode: 'by_type' (default) | 'by_date'."},
            "task":   {"type": "STRING", "description": "Natural language task description for AI-powered 'task' action."},
        },
        "required": []
    }
}

browser_open_tool = {
    "name": "browser_open",
    "description": (
        "Opens a website, URL, or named web service in Lumina's dedicated Brave browser. "
        "Use when the user asks to open a specific website or search Google. "
        "All URLs open in Lumina's isolated Brave instance — never in the user's personal browser.\n"
        "Correct uses: open a URL, open a named site (GitHub, Gmail, Reddit, Instagram, Twitter, etc.), "
        "Google search for something, open a streaming site home page.\n"
        "Do NOT use this for: opening desktop apps (use open_app), YouTube tasks (use youtube_control), "
        "or on-page browser interaction (use local_browser_control).\n"
        "Do NOT call this alongside open_app or youtube_control for the same request.\n"
        "Actions: open_url | google_search | open_site. Auto-detected if omitted."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "Action: 'open_url' | 'google_search' | 'open_site'. Auto-detected if omitted."},
            "url":    {"type": "STRING", "description": "Full URL to open (for open_url action)."},
            "query":  {"type": "STRING", "description": "Search query (for google_search action)."},
            "site":   {"type": "STRING", "description": "Site name or domain (for open_site action, e.g. 'YouTube', 'WhatsApp', 'GitHub')."},
        },
        "required": []
    }
}

youtube_control_tool = {
    "name": "youtube_control",
    "description": (
        "Handles YouTube tasks: open YouTube home, search, play a video/song, open a channel, "
        "trending, shorts, music, subscriptions, library, history.\n"
        "Use when the user asks for any YouTube-specific action.\n"
        "Do NOT use local_browser_control or browser_open for YouTube tasks.\n"
        "Do NOT call this alongside browser_open or open_app for the same request.\n"
        "Do NOT use this for Spotify requests — use spotify_control instead.\n"
        "Actions: open_home | search | play_first | open_channel | trending | shorts | music | "
        "subscriptions | library | history | open_url."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action":  {"type": "STRING", "description": "Action to perform (see description). Default: 'open_home'."},
            "query":   {"type": "STRING", "description": "Search term or song/video name (for search, play_first, music)."},
            "channel": {"type": "STRING", "description": "Channel name or @handle (for open_channel)."},
            "url":     {"type": "STRING", "description": "Specific YouTube URL or video ID (for open_url)."},
        },
        "required": []
    }
}

spotify_control_tool = {
    "name": "spotify_control",
    "description": (
        "Controls the Spotify DESKTOP APP directly. Use for ALL Spotify requests.\n"
        "NEVER use browser_open, youtube_control, or local_browser_control for Spotify.\n"
        "NEVER route Spotify playback/search to YouTube — always use this tool.\n"
        "Supported actions:\n"
        "  open         — launch or focus Spotify desktop app\n"
        "  focus        — bring Spotify window to front\n"
        "  play         — resume playback in Spotify desktop\n"
        "  pause        — pause playback in Spotify desktop\n"
        "  resume       — resume playback (alias for play)\n"
        "  next         — skip to next track\n"
        "  previous     — go to previous track\n"
        "  shuffle      — toggle shuffle\n"
        "  repeat       — toggle repeat\n"
        "  search       — search Spotify for a query (requires query parameter)\n"
        "  play_query   — search and attempt to play first result (requires query parameter)\n"
        "  open_liked   — navigate to Liked Songs in Spotify desktop\n"
        "  open_library — navigate to Your Library in Spotify desktop\n"
        "Examples:\n"
        "  'open Spotify' → spotify_control action=open\n"
        "  'play music on Spotify' → spotify_control action=play\n"
        "  'pause Spotify' → spotify_control action=pause\n"
        "  'next song on Spotify' → spotify_control action=next\n"
        "  'previous song on Spotify' → spotify_control action=previous\n"
        "  'search Spotify for soft music' → spotify_control action=search query=soft music\n"
        "  'play mana ka kura on Spotify' → spotify_control action=play_query query=mana ka kura\n"
        "  'open liked songs on Spotify' → spotify_control action=open_liked\n"
        "  'open my library on Spotify' → spotify_control action=open_library\n"
        "Do NOT call this alongside browser_open, youtube_control, or open_app for the same request."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "Action to perform. One of: open | focus | play | pause | resume | next | previous | shuffle | repeat | search | play_query | open_liked | open_library. Default: open."},
            "query":  {"type": "STRING", "description": "Search term, song name, or artist name. Required for: search, play_query."},
        },
        "required": []
    }
}

tools_list = [{"function_declarations": [
    generate_cad_prototype_tool,
    write_file_tool,
    read_directory_tool,
    read_file_tool,
    browser_control_tool,
    local_browser_control_tool,
    # Phase M: Mark-XXX Integrated Action Tools
    cmd_control_tool,
    file_controller_tool,
    computer_control_tool,
    computer_settings_tool,
    open_app_tool,
    send_message_tool,
    web_search_tool,
    weather_tool,
    system_reminder_tool,
    screen_process_tool,
    desktop_control_tool,
    browser_open_tool,
    youtube_control_tool,
    spotify_control_tool,
]}]
