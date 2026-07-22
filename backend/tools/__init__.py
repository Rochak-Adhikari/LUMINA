"""
Lumina tool declarations — Gemini Live function_declarations registry.

This package also contains submodules:
  - tools.browser_control: Phase T1 Browser Controller (headless)
  - tools.local_browser_control: Phase T2 Local Brave Controller (CDP, visible)
"""

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
        "opening Spotify, playing music, or any task that can be handled by browser_open "
        "or open_app.\n"
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
        "Do NOT call this alongside browser_open for the same request. "
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
        "Correct uses: open a URL, open a named site (GitHub, Gmail, Reddit, Instagram, Twitter, YouTube, etc.), "
        "Google search for something, open a streaming site, open YouTube or search/play YouTube videos.\n"
        "YouTube examples:\n"
        "  open YouTube home  → browser_open(action=open_url, url=https://www.youtube.com)\n"
        "  search/play on YouTube → browser_open(action=open_url, url=https://www.youtube.com/results?search_query=<query>)\n"
        "Do NOT use this for: opening desktop apps (use open_app), "
        "on-page browser interaction (use local_browser_control), "
        "or PLAYING a video on YouTube (use youtube_play for that).\n"
        "Do NOT call this alongside open_app for the same request.\n"
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


youtube_play_tool = {
    "name": "youtube_play",
    "description": (
        "Search for and automatically play a video on YouTube in Lumina's browser.\n"
        "Use this when the user wants to PLAY a specific video, song, or artist on YouTube.\n"
        "This tool automatically: (1) opens YouTube search results, (2) finds the best matching "
        "video title, (3) clicks it to start playback. No follow-up steps needed from you.\n"
        "Use browser_open instead for: just opening YouTube, browsing YouTube, or searching "
        "YouTube without immediately playing something.\n"
        "Examples:\n"
        "  'play rasputin on youtube'       -> youtube_play(query='rasputin')\n"
        "  'play lofi music on youtube'     -> youtube_play(query='lofi music')\n"
        "  'play something chill'           -> youtube_play(query='chill music')\n"
        "  'youtube play coldplay yellow'   -> youtube_play(query='coldplay yellow')\n"
        "Do NOT use for Spotify — use spotify_control for Spotify requests."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "query": {
                "type": "STRING",
                "description": "What to search and play on YouTube (song title, artist, topic, genre, etc.)"
            }
        },
        "required": ["query"]
    }
}


spotify_control_tool = {
    "name": "spotify_control",
    "description": (
        "Controls the Spotify DESKTOP APP directly. Use for ALL Spotify requests.\n"
        "NEVER use browser_open or local_browser_control for Spotify.\n"
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
        "Do NOT call this alongside browser_open or open_app for the same request."
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

# Phase 5: Imported from Jarvis-MK37
code_helper_tool = {
    "name": "code_helper",
    "description": (
        "Writes, edits, explains, runs, builds, optimizes, or debugs code files. "
        "Use when the user asks to write code, edit a file, explain code, run a script, "
        "build and test code, optimize/refactor code, or debug screen errors. "
        "The 'auto' action intelligently detects intent from the description."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "write | edit | explain | run | build | optimize | screen_debug | auto (default: auto)"},
            "description": {"type": "STRING", "description": "What the code should do or what change to make"},
            "language": {"type": "STRING", "description": "Programming language (default: python)"},
            "output_path": {"type": "STRING", "description": "Where to save the file"},
            "file_path": {"type": "STRING", "description": "Path to existing file for edit/explain/run/build/optimize"},
            "code": {"type": "STRING", "description": "Raw code string for explain/optimize"},
            "args": {"type": "STRING", "description": "CLI arguments for run/build"},
            "timeout": {"type": "INTEGER", "description": "Execution timeout in seconds (default: 30)"}
        },
        "required": ["action"]
    }
}

# Phase M.2: File Processor — AI-powered file analysis (ported from Mark-XLVI)
file_processor_tool = {
    "name": "file_processor",
    "description": (
        "Analyze, process, or convert any uploaded file using AI. "
        "Supports images (describe, OCR, resize, convert, compress), "
        "PDFs (summarize, extract text, convert to Word), "
        "documents (DOCX, TXT, MD — summarize, reformat, word count), "
        "data files (CSV, Excel — analyze, filter, sort, stats, convert), "
        "JSON (validate, format, analyze, convert), "
        "code files (explain, review, fix, run, optimize, document), "
        "audio (transcribe, trim, convert, info), "
        "video (info, trim, extract audio/frame, compress, transcribe), "
        "archives (list contents, extract), "
        "presentations (PPTX — summarize, extract text). "
        "If no action is specified, the best action is auto-detected."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "file_path":   {"type": "STRING", "description": "Path to the file to process."},
            "action":      {"type": "STRING", "description": "What to do: describe, ocr, summarize, analyze, extract_text, resize, convert, compress, info, filter, sort, stats, explain, review, fix, run, transcribe, trim, list, extract, etc. Auto-detected if omitted."},
            "instruction": {"type": "STRING", "description": "Custom instruction for AI processing (overrides default prompt)."},
            "format":      {"type": "STRING", "description": "Target format for convert actions (e.g. 'png', 'csv', 'mp3')."},
            "width":       {"type": "INTEGER", "description": "Width for image resize."},
            "height":      {"type": "INTEGER", "description": "Height for image resize."},
            "scale":       {"type": "NUMBER", "description": "Scale factor for image resize (e.g. 0.5 for half)."},
            "quality":     {"type": "INTEGER", "description": "Quality level for compress (0-100 for images, CRF for video)."},
            "column":      {"type": "STRING", "description": "Column name for data filter/sort."},
            "value":       {"type": "STRING", "description": "Filter value."},
            "condition":   {"type": "STRING", "description": "Filter condition: equals, contains, gt, lt."},
            "start":       {"type": "STRING", "description": "Start time for trim (seconds or HH:MM:SS)."},
            "end":         {"type": "STRING", "description": "End time for trim."},
            "timestamp":   {"type": "STRING", "description": "Timestamp for video frame extraction (HH:MM:SS)."},
        },
        "required": ["file_path"]
    }
}

# Phase M.3: Dev Agent — Multi-file project builder (ported from Mark-XLVI)
dev_agent_tool = {
    "name": "dev_agent",
    "description": (
        "Build a complete multi-file software project from a description. "
        "Plans the file structure, writes every file with proper imports and "
        "cross-references, installs dependencies, opens VS Code, runs the project, "
        "and auto-fixes errors up to 5 times. "
        "Use this when the user wants to build a full application, tool, game, "
        "website, API, or any multi-file project — NOT for single code snippets "
        "(use code_helper for those). "
        "Supports Python, JavaScript, TypeScript, and any language Gemini can generate. "
        "Projects are saved to ~/Desktop/LuminaProjects/."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "description":  {"type": "STRING",  "description": "What the project should do. Be specific about features, UI, and behavior."},
            "language":     {"type": "STRING",  "description": "Programming language (default: python). Examples: python, javascript, typescript, html, java, go, rust."},
            "project_name": {"type": "STRING",  "description": "Name for the project folder (auto-generated from description if omitted)."},
            "timeout":      {"type": "INTEGER", "description": "Run timeout in seconds per attempt (default: 30). Use higher values for servers or GUI apps."},
        },
        "required": ["description"]
    }
}


# Phase M.4: Flight Finder — Find flight options using Google Flights
flight_finder_tool = {
    "name": "flight_finder",
    "description": (
        "Search and analyze flight options from an origin to a destination airport/city on Google Flights. "
        "Can optionally schedule return flights, configure cabin class (economy, premium, business, first), "
        "specify passenger count, and save/export results to a text file on the Desktop."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "origin":      {"type": "STRING",  "description": "Departure airport code or city name (e.g. 'NYC', 'London', 'LAX')."},
            "destination": {"type": "STRING",  "description": "Arrival airport code or city name (e.g. 'IST', 'SFO', 'London')."},
            "date":        {"type": "STRING",  "description": "Departure date in YYYY-MM-DD format or natural language (e.g. 'tomorrow', 'next Monday', 'June 15')."},
            "return_date": {"type": "STRING",  "description": "Optional return date in YYYY-MM-DD format or natural language."},
            "passengers":  {"type": "INTEGER", "description": "Number of passengers (default: 1)."},
            "cabin":       {"type": "STRING",  "description": "Cabin class: economy | premium | business | first (default: economy)."},
            "save":        {"type": "BOOLEAN", "description": "If true, saves search results to a text file on the Desktop."}
        },
        "required": ["origin", "destination", "date"]
    }
}

# Phase M.5: Game Updater — Manage Steam & Epic Games installations/updates
game_updater_tool = {
    "name": "game_updater",
    "description": (
        "Install, update, list, and monitor downloads for Steam and Epic Games. "
        "Allows scheduling daily updates, cancelling schedules, querying schedule status, "
        "checking active download progress, and optionally shutting down the computer when downloads finish."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action":             {"type": "STRING",  "description": "Action to perform: update (check/trigger updates) | install (install a new game) | list (list installed games) | download_status (check download progress) | schedule (schedule daily update) | cancel_schedule | schedule_status (default: update)."},
            "platform":           {"type": "STRING",  "description": "Target game store platform: steam | epic | both (default: both)."},
            "game_name":          {"type": "STRING",  "description": "Name of the game (optional for update/list, required for install)."},
            "app_id":             {"type": "STRING",  "description": "Steam AppID of the game (optional, used as fallback for install)."},
            "hour":               {"type": "INTEGER", "description": "Hour for daily update schedule (0-23, default: 3)."},
            "minute":             {"type": "INTEGER", "description": "Minute for daily update schedule (0-59, default: 0)."},
            "shutdown_when_done": {"type": "BOOLEAN", "description": "Auto-shutdown computer when active downloads finish (default: false)."}
        },
        "required": []
    }
}

# Navigation UI — programmatically switch panels
navigate_ui_tool = {
    "name": "navigate_ui",
    "description": "Navigates Lumina's screen interface to a specific panel or view. Use this when the user asks to open settings, show the archive, view features, go to the calendar/events, or return home.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "panel": {
                "type": "STRING",
                "description": "Target panel name: 'home' | 'features' | 'events' | 'archive' | 'settings'."
            }
        },
        "required": ["panel"]
    }
}

tools_list = [{"function_declarations": [
    write_file_tool,
    read_directory_tool,
    read_file_tool,
    browser_control_tool,
    local_browser_control_tool,
    navigate_ui_tool,
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
    youtube_play_tool,
    spotify_control_tool,
    code_helper_tool,
    file_processor_tool,
    dev_agent_tool,
    flight_finder_tool,
    game_updater_tool,
]}]


