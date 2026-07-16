# Lumina V2 Registered Capabilities & Tool schemas

Lumina declares 26 interactive capabilities. These are declared as Gemini Live `function_declarations` under `backend/tools/__init__.py` and mapped to handlers in `backend/core/tool_handlers.py` via `ToolDispatcherRegistry`.

---

## 1. Voice & State Abstractions

### `generate_cad_prototype`
- **Description**: Generates a 3D wireframe OpenSCAD model from a natural description.
- **Parameters**:
  - `prompt` (STRING, Required): Description of the object.

### `iterate_cad`
- **Description**: Refines an existing CAD STL model.
- **Parameters**:
  - `prompt` (STRING, Required): Changes to make.

---

## 2. Workspace File System CRUD

### `write_file`
- **Description**: Writes string content to a file. Overwrites if exists.
- **Parameters**:
  - `path` (STRING, Required): File path.
  - `content` (STRING, Required): Content.

### `read_file`
- **Description**: Reads file contents.
- **Parameters**:
  - `path` (STRING, Required): File path.

### `read_directory`
- **Description**: Lists files inside a folder.
- **Parameters**:
  - `path` (STRING, Required): Folder path.

---

## 3. Browser Control Systems

### `browser_control`
- **Description**: Headless browser tasks via Playwright.
- **Parameters**:
  - `intent` (STRING, Required): open_url | search_google | click_text | read_page_summary | screenshot
  - `params` (STRING, Required): JSON string of parameters.

### `local_browser_control`
- **Description**: Visible browser tasks using CDP on Brave. Enforces confirmation for dangerous button clicks (pay, post, login, submit).
- **Parameters**:
  - `action` (STRING, Required): open_url | click_text | focus_textbox | type_text | screenshot | list_tabs
  - `params` (STRING, Required): JSON string of parameters.

---

## 4. System Automation (Mark-XXX Actions)

### `cmd_control`
- **Description**: Executes terminal commands inside PowerShell or CMD.
- **Parameters**:
  - `task` (STRING): NLP request to convert to shell command.
  - `command` (STRING): Direct command line to run.
  - `visible` (BOOLEAN): Show window.

### `computer_control`
- **Description**: PyAutoGUI interface simulating mouse movements and keyboard entries.
- **Parameters**:
  - `action` (STRING, Required): click | type | screenshot | scroll | focus_window
  - `text` (STRING): Text to type.
  - `x` (INTEGER): Mouse X.
  - `y` (INTEGER): Mouse Y.

### `computer_settings`
- **Description**: Adjusts desktop volume, screen brightness, Wi-Fi toggles, or lock screen.
- **Parameters**:
  - `description` (STRING): Natural request like "mute volume".

### `open_app`
- **Description**: Launches, closes, or checks local desktop software applications.
- **Parameters**:
  - `app` (STRING, Required): Application name.
  - `action` (STRING): open | close | focus | check.

### `send_message`
- **Description**: Composes messages on WhatsApp, Telegram, or Instagram via browser automate tasks.
- **Parameters**:
  - `platform` (STRING): whatsapp | telegram | instagram.
  - `contact` (STRING, Required): Name or phone number.
  - `message` (STRING, Required): Message content.

### `web_search`
- **Description**: DuckDuckGo search queries.
- **Parameters**:
  - `query` (STRING, Required): Search query.

### `weather`
- **Description**: Local weather reports.
- **Parameters**:
  - `location` (STRING): City name.

### `system_reminder`
- **Description**: Registers one-off alarms using Windows Task Scheduler.
- **Parameters**:
  - `title` (STRING): Alert title.
  - `time` (STRING): Date/time string like "in 30 minutes".

### `screen_process`
- **Description**: OCR screen capture parsing.
- **Parameters**:
  - `action` (STRING): screenshot | camera.

### `desktop_control`
- **Description**: Minimizes, maximizes, tiles windows, and manages wallpapers.
- **Parameters**:
  - `action` (STRING): clean | organize | wallpaper.

### `browser_open`
- **Description**: Opens named sites (GitHub, YouTube) directly in Brave.
- **Parameters**:
  - `url` (STRING): Target URL.
  - `query` (STRING): Search string.

### `youtube_play`
- **Description**: Plays video immediately.
- **Parameters**:
  - `query` (STRING, Required): Video title.

### `spotify_control`
- **Description**: Play/pause/skip for local Spotify app.
- **Parameters**:
  - `action` (STRING, Required): play | pause | next | prev | search.
  - `query` (STRING): Search string.

### `code_helper`
- **Description**: Explains, compiles, or debugs code.
- **Parameters**:
  - `action` (STRING, Required): write | run | build | debug.
  - `description` (STRING): Tasks to execute.

### `file_processor`
- **Description**: Summarizes PDFs, analyzes CSV stats, or compresses images.
- **Parameters**:
  - `file_path` (STRING, Required): Input file.
  - `action` (STRING): summarize | stats.

### `dev_agent`
- **Description**: Scaffolds multi-file applications.
- **Parameters**:
  - `description` (STRING, Required): App specification.

### `flight_finder`
- **Description**: Google Flights scraper.
- **Parameters**:
  - `origin` (STRING, Required): Origin city.
  - `destination` (STRING, Required): Destination city.
  - `date` (STRING, Required): Date.

### `game_updater`
- **Description**: Schedules Steam/Epic updates.
- **Parameters**:
  - `action` (STRING): update | schedule.

### `navigate_ui`
- **Description**: Moves frontend panel focus (home, settings, events, archive).
- **Parameters**:
  - `panel` (STRING, Required): home | features | events | archive | settings.
