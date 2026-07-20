import asyncio
import time
import json
import uuid
from google.genai import types
from core.registry import ToolDispatcherRegistry

# --- File Operations ---

@ToolDispatcherRegistry.register("write_file")
async def handle_write_file(fc, loop) -> dict:
    path = fc.args["path"]
    content = fc.args["content"]
    print(f"[LUMINA DEBUG] [TOOL] Tool Call: 'write_file' path='{path}'")
    asyncio.create_task(loop.handle_write_file(path, content))
    return {"result": "Writing file..."}

@ToolDispatcherRegistry.register("read_directory")
async def handle_read_directory(fc, loop) -> dict:
    path = fc.args["path"]
    print(f"[LUMINA DEBUG] [TOOL] Tool Call: 'read_directory' path='{path}'")
    asyncio.create_task(loop.handle_read_directory(path))
    return {"result": "Reading directory..."}

@ToolDispatcherRegistry.register("read_file")
async def handle_read_file(fc, loop) -> dict:
    path = fc.args["path"]
    print(f"[LUMINA DEBUG] [TOOL] Tool Call: 'read_file' path='{path}'")
    asyncio.create_task(loop.handle_read_file(path))
    return {"result": "Reading file..."}

# --- Project Management ---

def _maybe_activate_workspace(loop) -> None:
    """Phase 5.8.2 — flag-gated Workspace Activation trigger.

    After ProjectManager switches project, follow it into WorkspaceMemory via
    the RuntimeFacade (the single runtime abstraction; never WorkspaceSync
    directly). Idempotent at the facade/sync layer. Disabled by default:
    when off, this is a no-op and runtime behaviour is byte-identical.
    Failure-safe — activation must never fail a project switch.
    """
    if not loop.permissions.get("workspace_activation_enabled", False):
        return
    facade = getattr(loop, "_facade", None)
    if facade is None:
        return
    try:
        facade.activate_workspace(loop.project_manager)
    except Exception as e:
        print(f"[LUMINA DEBUG] [WORKSPACE] Activation skipped (non-fatal): {e}")

@ToolDispatcherRegistry.register("create_project")
async def handle_create_project(fc, loop) -> dict:
    name = fc.args["name"]
    print(f"[LUMINA DEBUG] [TOOL] Tool Call: 'create_project' name='{name}'")
    success, msg = loop.project_manager.create_project(name)
    if success:
        loop.project_manager.switch_project(name)
        _maybe_activate_workspace(loop)
        msg += f" Switched to '{name}'."
        if loop.on_project_update:
            loop.on_project_update(name)
    return {"result": msg}

@ToolDispatcherRegistry.register("switch_project")
async def handle_switch_project(fc, loop) -> dict:
    name = fc.args["name"]
    print(f"[LUMINA DEBUG] [TOOL] Tool Call: 'switch_project' name='{name}'")
    success, msg = loop.project_manager.switch_project(name)
    if success:
        _maybe_activate_workspace(loop)
        if loop.on_project_update:
            loop.on_project_update(name)
        context = loop.project_manager.get_project_context()
        print(f"[LUMINA DEBUG] [PROJECT] Sending project context to AI ({len(context)} chars)")
        try:
            await loop.session.send(input=f"System Notification: {msg}\n\n{context}", end_of_turn=False)
        except Exception as e:
            print(f"[LUMINA DEBUG] [ERR] Failed to send project context: {e}")
    return {"result": msg}

@ToolDispatcherRegistry.register("list_projects")
async def handle_list_projects(fc, loop) -> dict:
    print(f"[LUMINA DEBUG] [TOOL] Tool Call: 'list_projects'")
    # Phase 2.7: Resolve IWorkspaceManager via RuntimeFacade to list projects
    try:
        workspace_mgr = loop._facade.workspace_manager
        projects = workspace_mgr.list_projects()
    except Exception:
        projects = loop.project_manager.list_projects()
    return {"result": f"Available projects: {', '.join(projects)}"}

# --- UI & Browser Handlers ---

@ToolDispatcherRegistry.register("navigate_ui")
async def handle_navigate_ui(fc, loop) -> dict:
    panel = fc.args.get("panel", "home")
    print(f"[LUMINA DEBUG] [TOOL] Tool Call: 'navigate_ui' panel='{panel}'")
    if loop.on_voice_command:
        loop.on_voice_command(panel, "all")
        result_str = f"Successfully navigated interface to panel: {panel}."
    else:
        result_str = f"Navigation failed: UI callback not registered. Cannot switch to {panel}."
    return {"result": result_str}

@ToolDispatcherRegistry.register("browser_control")
async def handle_browser_control(fc, loop) -> dict:
    intent = fc.args.get("intent", "")
    params_raw = fc.args.get("params", "{}")
    print(f"[LUMINA DEBUG] [TOOL] Tool Call: 'browser_control' intent='{intent}' params='{str(params_raw)[:100]}'")
    
    if isinstance(params_raw, str):
        try:
            parsed_params = json.loads(params_raw)
        except json.JSONDecodeError:
            parsed_params = {"raw": params_raw}
    elif isinstance(params_raw, dict):
        parsed_params = params_raw
    else:
        parsed_params = {}

    from tools.browser_control import execute_browser_intent as _exec_browser
    _ctx = {"tool_permissions": loop.permissions}
    result_dict = await _exec_browser(intent, parsed_params, _ctx)
    result_str = result_dict.get("message", "Unknown result")
    if result_dict.get("data"):
        data = result_dict["data"]
        if data.get("url"): result_str += f"\nURL: {data['url']}"
        if data.get("title"): result_str += f"\nTitle: {data['title']}"
        if data.get("dom_text"): result_str += f"\nPage content:\n{data['dom_text'][:2000]}"
    if result_dict.get("screenshot"):
        result_str += f"\nScreenshot saved: {result_dict['screenshot']}"
    return {"result": result_str}

@ToolDispatcherRegistry.register("local_browser_control")
async def handle_local_browser_control(fc, loop) -> dict:
    action = fc.args.get("action", "")
    params_raw = fc.args.get("params", "{}")
    _TOOL_TIMEOUT = 30
    _tool_t0 = time.time()
    print(f"[TOOL] start name=local_browser_control action={action} timeout={_TOOL_TIMEOUT}")

    if isinstance(params_raw, str):
        try:
            parsed_params = json.loads(params_raw)
        except json.JSONDecodeError:
            parsed_params = {"raw": params_raw}
    elif isinstance(params_raw, dict):
        parsed_params = params_raw
    else:
        parsed_params = {}

    from tools.local_browser_control import execute_local_browser as _exec_local
    _ctx = {
        "tool_permissions": loop.permissions,
        "confirmation_mode": loop._browser_confirmation_mode,
    }
    try:
        result_dict = await asyncio.wait_for(
            _exec_local(action, parsed_params, _ctx),
            timeout=_TOOL_TIMEOUT
        )
        print(f"[TOOL] done name=local_browser_control action={action} ms={int((time.time() - _tool_t0)*1000)}")
    except asyncio.TimeoutError:
        print(f"[TOOL] timeout name=local_browser_control action={action} ms={int((time.time() - _tool_t0)*1000)}")
        result_dict = {"ok": False, "message": f"Browser action '{action}' timed out after {_TOOL_TIMEOUT}s.", "data": {}}

    if result_dict.get("needs_confirmation"):
        if loop.on_tool_confirmation:
            _gate_id = str(uuid.uuid4())
            _gate_detail = result_dict.get("message", "")
            print(f"[LUMINA DEBUG] [GATE] Action '{action}' requires confirmation (ID: {_gate_id})")
            _gate_future = asyncio.Future()
            loop._pending_confirmations[_gate_id] = _gate_future
            loop.on_tool_confirmation({
                "id": _gate_id,
                "tool": fc.name,
                "args": {**fc.args, "_gated_action": action, "_detail": _gate_detail}
            })
            try:
                _confirmed = await _gate_future
            finally:
                loop._pending_confirmations.pop(_gate_id, None)
            print(f"[LUMINA DEBUG] [GATE] Confirmation result: {_confirmed}")
            if _confirmed:
                _ctx["confirmed"] = True
                result_dict = await _exec_local(action, parsed_params, _ctx)
            else:
                result_dict = {"ok": False, "message": f"Action '{action}' was rejected by user.", "data": {}}
        else:
            result_dict = {"ok": False, "message": f"Action '{action}' requires confirmation but no handler available.", "data": {}}

    result_str = result_dict.get("message", "Unknown result")
    if result_dict.get("data"):
        data = result_dict["data"]
        for key in ["url", "title", "media", "tabs", "matched", "closest", "focused", "focused_element", "recovery", "remaining_tabs"]:
            if key in data:
                result_str += f"\n{key.capitalize()}: {data[key]}"
        if "found" in data:
            result_str += f"\nText found: {data['found']}"
        if data.get("timed_out"):
            result_str += "\nTimed out waiting for text"
        if "active_tab_index" in data:
            result_str += f"\nActive state: tab={data.get('active_tab_index')}, loading={data.get('is_loading')}, viewport={data.get('viewport')}"
        if data.get("clicked"):
            result_str += f"\nClicked: text='{data.get('text','')[:50]}' tag={data.get('tag','')} score={data.get('score',0)} bbox={data.get('bbox',[])}"
        if data.get("clickables"):
            cl = data["clickables"][:20]
            result_str += f"\nClickable elements ({len(data['clickables'])} total, showing {len(cl)}):\n"
            for i, c in enumerate(cl):
                result_str += f"  [{i}] <{c['tag']}> \"{c.get('text','')[:50]}\" aria=\"{c.get('aria_label','')[:30]}\" conf={c.get('confidence',0)}\n"
        if data.get("inputs"):
            inp = data["inputs"][:10]
            result_str += f"\nInputs ({len(data['inputs'])} total):\n"
            for i, f_inp in enumerate(inp):
                result_str += f"  [{i}] placeholder='{f_inp.get('placeholder','')[:40]}' type={f_inp.get('type','')} bbox={f_inp.get('bbox',[])}\n"
        if data.get("headings"):
            result_str += f"\nHeadings: {data['headings'][:10]}"
        if data.get("errors"):
            result_str += f"\nErrors: {data['errors'][:5]}"

    return {"result": result_str}
