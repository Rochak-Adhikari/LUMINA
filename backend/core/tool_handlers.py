import asyncio
import time
import json
import uuid
from google.genai import types
from core.registry import ToolDispatcherRegistry

# --- CAD Handlers ---

@ToolDispatcherRegistry.register("generate_cad")
async def handle_generate_cad(fc, loop) -> None:
    prompt = fc.args.get("prompt", "")
    print(f"\n[LUMINA DEBUG] --------------------------------------------------")
    print(f"[LUMINA DEBUG] [TOOL] Tool Call Detected: 'generate_cad'")
    print(f"[LUMINA DEBUG] [IN] Arguments: prompt='{prompt}'")
    asyncio.create_task(loop.handle_cad_request(prompt))
    return None

@ToolDispatcherRegistry.register("iterate_cad")
async def handle_iterate_cad(fc, loop) -> dict:
    prompt = fc.args["prompt"]
    print(f"[LUMINA DEBUG] [TOOL] Tool Call: 'iterate_cad' Prompt='{prompt}'")
    if loop.on_cad_status:
        loop.on_cad_status("generating")
    cad_output_dir = str(loop.project_manager.get_current_project_path() / "cad")
    cad_data = await loop.cad_agent.iterate_prototype(prompt, output_dir=cad_output_dir)
    if cad_data:
        print(f"[LUMINA DEBUG] [OK] CadAgent iteration returned data successfully.")
        if loop.on_cad_data:
            print(f"[LUMINA DEBUG] [SEND] Dispatching iterated CAD data to frontend...")
            loop.on_cad_data(cad_data)
        loop.project_manager.save_cad_artifact("output.stl", f"Iteration: {prompt}")
        result_str = f"Successfully iterated design: {prompt}. The updated 3D model is now displayed."
    else:
        print(f"[LUMINA DEBUG] [ERR] CadAgent iteration returned None.")
        result_str = f"Failed to iterate design with prompt: {prompt}"
    return {"result": result_str}

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

@ToolDispatcherRegistry.register("create_project")
async def handle_create_project(fc, loop) -> dict:
    name = fc.args["name"]
    print(f"[LUMINA DEBUG] [TOOL] Tool Call: 'create_project' name='{name}'")
    success, msg = loop.project_manager.create_project(name)
    if success:
        loop.project_manager.switch_project(name)
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
    projects = loop.project_manager.list_projects()
    return {"result": f"Available projects: {', '.join(projects)}"}

# --- Smart Home ---

@ToolDispatcherRegistry.register("list_smart_devices")
async def handle_list_smart_devices(fc, loop) -> dict:
    print(f"[LUMINA DEBUG] [TOOL] Tool Call: 'list_smart_devices'")
    dev_summaries = []
    frontend_list = []
    for ip, d in loop.kasa_agent.devices.items():
        dev_type = "bulb" if d.is_bulb else "plug" if d.is_plug else "strip" if d.is_strip else "dimmer" if d.is_dimmer else "unknown"
        info = f"{d.alias} (IP: {ip}, Type: {dev_type}) [{'ON' if d.is_on else 'OFF'}]"
        dev_summaries.append(info)
        frontend_list.append({
            "ip": ip, "alias": d.alias, "model": d.model, "type": dev_type, "is_on": d.is_on,
            "brightness": d.brightness if d.is_bulb or d.is_dimmer else None,
            "hsv": d.hsv if d.is_bulb and d.is_color else None,
            "has_color": d.is_color if d.is_bulb else False,
            "has_brightness": d.is_dimmable if d.is_bulb or d.is_dimmer else False
        })
    result_str = "No devices found in cache." if not dev_summaries else "Found Devices (Cached):\n" + "\n".join(dev_summaries)
    if loop.on_device_update:
        loop.on_device_update(frontend_list)
    return {"result": result_str}

@ToolDispatcherRegistry.register("control_light")
async def handle_control_light(fc, loop) -> dict:
    target = fc.args["target"]
    action = fc.args["action"]
    brightness = fc.args.get("brightness")
    color = fc.args.get("color")
    print(f"[LUMINA DEBUG] [TOOL] Tool Call: 'control_light' Target='{target}' Action='{action}'")
    result_msg = f"Action '{action}' on '{target}' failed."
    success = False
    if action == "turn_on":
        success = await loop.kasa_agent.turn_on(target)
        if success: result_msg = f"Turned ON '{target}'."
    elif action == "turn_off":
        success = await loop.kasa_agent.turn_off(target)
        if success: result_msg = f"Turned OFF '{target}'."
    elif action == "set":
        success = True
        result_msg = f"Updated '{target}':"
    if success or action == "set":
        if brightness is not None:
            sb = await loop.kasa_agent.set_brightness(target, brightness)
            if sb: result_msg += f" Set brightness to {brightness}."
        if color is not None:
            sc = await loop.kasa_agent.set_color(target, color)
            if sc: result_msg += f" Set color to {color}."
    if success:
        updated_list = []
        for ip, dev in loop.kasa_agent.devices.items():
            dev_type = "bulb" if dev.is_bulb else "plug" if dev.is_plug else "strip" if dev.is_strip else "dimmer" if dev.is_dimmer else "unknown"
            updated_list.append({
                "ip": ip, "alias": dev.alias, "model": dev.model, "type": dev_type, "is_on": dev.is_on,
                "brightness": dev.brightness if dev.is_bulb or dev.is_dimmer else None,
                "hsv": dev.hsv if dev.is_bulb and dev.is_color else None,
                "has_color": dev.is_color if dev.is_bulb else False,
                "has_brightness": dev.is_dimmable if dev.is_bulb or dev.is_dimmer else False
            })
        if loop.on_device_update:
            loop.on_device_update(updated_list)
    else:
        if loop.on_error:
            loop.on_error(result_msg)
    return {"result": result_msg}

# --- Printer Handlers ---

@ToolDispatcherRegistry.register("discover_printers")
async def handle_discover_printers(fc, loop) -> dict:
    print(f"[LUMINA DEBUG] [TOOL] Tool Call: 'discover_printers'")
    printers = await loop.printer_agent.discover_printers()
    if printers:
        printer_list = [f"{p['name']} ({p['host']}:{p['port']}, type: {p['printer_type']})" for p in printers]
        result_str = "Found Printers:\n" + "\n".join(printer_list)
    else:
        result_str = "No printers found on network. Ensure printers are on and OctoPrint/Moonraker is running."
    return {"result": result_str}

@ToolDispatcherRegistry.register("print_stl")
async def handle_print_stl(fc, loop) -> dict:
    stl_path = fc.args["stl_path"]
    printer = fc.args["printer"]
    profile = fc.args.get("profile")
    print(f"[LUMINA DEBUG] [TOOL] Tool Call: 'print_stl' STL='{stl_path}' Printer='{printer}'")
    if stl_path.lower() == "current":
        stl_path = "output.stl"
    project_path = str(loop.project_manager.get_current_project_path())
    result = await loop.printer_agent.print_stl(stl_path, printer, profile, root_path=project_path)
    return {"result": result.get("message", "Unknown result")}

@ToolDispatcherRegistry.register("get_print_status")
async def handle_get_print_status(fc, loop) -> dict:
    printer = fc.args["printer"]
    print(f"[LUMINA DEBUG] [TOOL] Tool Call: 'get_print_status' Printer='{printer}'")
    status = await loop.printer_agent.get_print_status(printer)
    if status:
        result_str = (
            f"Printer: {status.printer}\nState: {status.state}\n"
            f"Progress: {status.progress_percent:.1f}%\n"
        )
        if status.time_remaining:
            result_str += f"Time Remaining: {status.time_remaining}\n"
        if status.time_elapsed:
            result_str += f"Time Elapsed: {status.time_elapsed}\n"
        if status.filename:
            result_str += f"File: {status.filename}\n"
        if status.temperatures:
            temps = status.temperatures
            if "hotend" in temps:
                result_str += f"Hotend: {temps['hotend']['current']:.0f}°C / {temps['hotend']['target']:.0f}°C\n"
            if "bed" in temps:
                result_str += f"Bed: {temps['bed']['current']:.0f}°C / {temps['bed']['target']:.0f}°C"
    else:
        result_str = f"Could not get status for printer '{printer}'. Ensure it is discovered first."
    return {"result": result_str}

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
