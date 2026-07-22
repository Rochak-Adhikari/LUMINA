const { app, BrowserWindow, ipcMain, BrowserView, session } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

// Use ANGLE D3D11 backend - more stable on Windows while keeping WebGL working
// This fixes "GPU state invalid after WaitForGetOffsetInRange" error
app.commandLine.appendSwitch('use-angle', 'd3d11');
app.commandLine.appendSwitch('enable-features', 'Vulkan');
app.commandLine.appendSwitch('ignore-gpu-blocklist');
// Electron's own renderer debug port. MUST NOT be 9223 — that port is reserved
// for Lumina's dedicated Brave instance (backend browser tools connect_over_cdp
// to 9223). Sharing it let the backend's browser_open "reuse active tab" grab
// the Electron renderer and navigate the whole app to the opened site, killing
// the React tree + Socket.IO connection. Use a distinct port to keep the two
// CDP surfaces isolated.
app.commandLine.appendSwitch('remote-debugging-port', '9444');

let mainWindow;
let pythonProcess;
let backendPort = 8000; // Dynamically discovered backend port

let browserViews = {}; // tabId -> BrowserView
let activeTabId = null;
let currentBrowserBounds = { x: 0, y: 0, width: 0, height: 0, visible: false };

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1920,
        height: 1080,
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false, // For simple IPC/Socket.IO usage
        },
        backgroundColor: '#000000',
        frame: false, // Frameless for custom UI
        titleBarStyle: 'hidden',
        show: false, // Don't show until ready
    });

    // Native Download Manager wiring
    mainWindow.webContents.session.on('will-download', (event, item, webContents) => {
        const downloadId = Date.now().toString();
        const fileName = item.getFilename();
        const totalBytes = item.getTotalBytes();

        mainWindow.webContents.send('download-event-start', {
            id: downloadId,
            name: fileName,
            totalBytes,
        });

        item.on('updated', (event, state) => {
            if (state === 'interrupted') {
                mainWindow.webContents.send('download-event-update', {
                    id: downloadId,
                    state: 'interrupted',
                });
            } else if (state === 'progressing') {
                if (item.isPaused()) {
                    mainWindow.webContents.send('download-event-update', {
                        id: downloadId,
                        state: 'paused',
                    });
                } else {
                    mainWindow.webContents.send('download-event-update', {
                        id: downloadId,
                        state: 'progressing',
                        receivedBytes: item.getReceivedBytes(),
                    });
                }
            }
        });

        item.once('done', (event, state) => {
            mainWindow.webContents.send('download-event-done', {
                id: downloadId,
                state, // 'completed' | 'cancelled' | 'interrupted'
                filePath: item.getSavePath(),
            });
        });
    });

    // In dev, load Vite server. In prod, load the built HTML.
    // Target the NEW modular frontend (frontend.html → /frontend/main.jsx),
    // not the legacy entry (index.html → /src/main.jsx). Dev: Vite serves any
    // root HTML entry by path. Prod: the new frontend builds to dist-fe/.
    const isDev = process.env.NODE_ENV !== 'production';

    const loadFrontend = (retries = 3) => {
        const url = isDev ? 'http://localhost:5173/frontend.html' : null;
        const loadPromise = isDev
            ? mainWindow.loadURL(url)
            : mainWindow.loadFile(path.join(__dirname, '../dist-fe/frontend.html'));

        loadPromise
            .then(() => {
                console.log('Frontend loaded successfully!');
                windowWasShown = true;
                mainWindow.show();
                if (isDev) {
                    mainWindow.webContents.openDevTools();
                }
            })
            .catch((err) => {
                console.error(`Failed to load frontend: ${err.message}`);
                if (retries > 0) {
                    console.log(`Retrying in 1 second... (${retries} retries left)`);
                    setTimeout(() => loadFrontend(retries - 1), 1000);
                } else {
                    console.error('Failed to load frontend after all retries. Keeping window open.');
                    windowWasShown = true;
                    mainWindow.show(); // Show anyway so user sees something
                }
            });
    };

    loadFrontend();

    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}

function startPythonBackend() {
    const scriptPath = path.join(__dirname, '../backend/server.py');
    console.log(`Starting Python backend: ${scriptPath}`);

    // Try to run using the correct dedicated conda environment python binary directly
    const condaPython = 'E:\\AI\\conda_envs\\lumina\\python.exe';
    const fs = require('fs');
    const pythonExe = fs.existsSync(condaPython) ? condaPython : 'python';

    const childEnv = Object.assign({}, process.env, {
        CONDA_DEFAULT_ENV: 'E:\\AI\\conda_envs\\lumina',
        PYTHONUNBUFFERED: '1'
    });

    pythonProcess = spawn(pythonExe, [scriptPath], {
        cwd: path.join(__dirname, '../backend'),
        env: childEnv
    });

    pythonProcess.stdout.on('data', (data) => {
        const str = data.toString();
        console.log(`[Python]: ${str}`);

        // Parse port if startup logs it
        const match = str.match(/\[STARTUP\] Starting Lumina backend on 0\.0\.0\.0:(\d+)/);
        if (match) {
            backendPort = parseInt(match[1], 10);
            console.log(`[Electron] Discovered spawned backend port: ${backendPort}`);
        }
    });

    pythonProcess.stderr.on('data', (data) => {
        console.error(`[Python Error]: ${data}`);
    });

    pythonProcess.on('exit', (code, signal) => {
        if (code !== 0 && code !== null) {
            console.error(`[Python Backend] Process exited with code ${code}`);
            console.error('[Python Backend] Backend startup FAILED. Check logs above.');
        } else if (signal) {
            console.log(`[Python Backend] Process killed with signal ${signal}`);
        }
        pythonProcess = null;
    });

    pythonProcess.on('error', (err) => {
        console.error(`[Python Backend] Failed to start: ${err.message}`);
        pythonProcess = null;
    });
}

app.whenReady().then(() => {
    // Intercept and redirect all localhost:8000/127.0.0.1:8000 traffic to the discovered backendPort
    session.defaultSession.webRequest.onBeforeRequest(
        {
            urls: [
                'http://localhost:8000/*', 'https://localhost:8000/*',
                'ws://localhost:8000/*', 'wss://localhost:8000/*',
                'http://127.0.0.1:8000/*', 'https://127.0.0.1:8000/*',
                'ws://127.0.0.1:8000/*', 'wss://127.0.0.1:8000/*'
            ]
        },
        (details, callback) => {
            const redirectUrl = details.url
                .replace('localhost:8000', `localhost:${backendPort}`)
                .replace('127.0.0.1:8000', `127.0.0.1:${backendPort}`);
            if (redirectUrl !== details.url) {
                console.log(`[TRACE] [ELECTRON PROXY] Redirecting request ${details.url} -> ${redirectUrl}`);
                callback({ redirectURL: redirectUrl });
            } else {
                callback({});
            }
        }
    );

    ipcMain.on('window-minimize', () => {
        if (mainWindow) mainWindow.minimize();
    });

    ipcMain.on('window-maximize', () => {
        if (mainWindow) {
            if (mainWindow.isMaximized()) {
                mainWindow.unmaximize();
            } else {
                mainWindow.maximize();
            }
        }
    });

    ipcMain.on('window-close', () => {
        if (mainWindow) mainWindow.close();
    });

    // ========================================
    // BROWSER WORKSPACE IPC EVENT HANDLERS
    // ========================================
    ipcMain.on('browser-create-tab', (event, { tabId, url }) => {
        if (browserViews[tabId]) return;

        const view = new BrowserView({
            webPreferences: {
                nodeIntegration: false,
                contextIsolation: true,
                sandbox: true,
            }
        });

        // Safe target handler for window opens (redirect to tabs)
        view.webContents.setWindowOpenHandler(({ url }) => {
            mainWindow.webContents.send('browser-event-new-tab', { url });
            return { action: 'deny' };
        });

        // Register loading and metadata sync listeners
        view.webContents.on('did-start-loading', () => {
            mainWindow.webContents.send('browser-event-loading', { tabId, loading: true });
        });

        view.webContents.on('did-stop-loading', () => {
            mainWindow.webContents.send('browser-event-loading', { tabId, loading: false });
        });

        view.webContents.on('page-title-updated', (e, title) => {
            mainWindow.webContents.send('browser-event-title', { tabId, title });
        });

        view.webContents.on('page-favicon-updated', (e, favicons) => {
            if (favicons && favicons.length > 0) {
                mainWindow.webContents.send('browser-event-favicon', { tabId, favicon: favicons[0] });
            }
        });

        view.webContents.on('did-navigate', (e, navUrl) => {
            mainWindow.webContents.send('browser-event-navigate', { tabId, url: navUrl });
        });

        view.webContents.on('did-navigate-in-page', (e, navUrl) => {
            mainWindow.webContents.send('browser-event-navigate', { tabId, url: navUrl });
        });

        // Stale-view recovery: if this tab's renderer crashes, tell the frontend
        // so it can recreate the tab instead of showing a dead view.
        view.webContents.on('render-process-gone', (e, details) => {
            console.warn(`[ELECTRON BROWSER] tab ${tabId} render-process-gone: ${details && details.reason}`);
            mainWindow.webContents.send('browser-event-crashed', { tabId, reason: details && details.reason });
        });

        // Set secure permissions handler
        view.webContents.session.setPermissionRequestHandler((webContents, permission, callback) => {
            const allowed = ['notifications', 'fullscreen', 'geolocation'];
            callback(allowed.includes(permission));
        });

        // WhatsApp Web auto-bot injection script (Zero Playwright background dependency)
        view.webContents.on('dom-ready', () => {
            const currentUrl = view.webContents.getURL();
            if (currentUrl.includes('web.whatsapp.com')) {
                console.log("[ELECTRON WHATSAPP] WhatsApp Web loaded. Injecting auto-reply bot script.");
                view.webContents.executeJavaScript(`
                    if (!window.luminaWhatsappPoller) {
                        console.log("[LUMINA WHATSAPP] Started message observer loop.");
                        window.luminaWhatsappPoller = setInterval(() => {
                            const badges = document.querySelectorAll('span[aria-label*="unread"], span[aria-label*="Unread"], div[aria-label*="unread"]');
                            if (badges.length > 0) {
                                // Click the first unread badge to load chat history
                                badges[0].click();
                                
                                setTimeout(() => {
                                    const messages = document.querySelectorAll('div.message-in');
                                    if (messages.length > 0) {
                                        const lastMsg = messages[messages.length - 1];
                                        const textEl = lastMsg.querySelector('span.selectable-text, div.copyable-text');
                                        if (textEl) {
                                            const text = textEl.textContent.trim();
                                            const headerEl = document.querySelector('header span[dir="auto"], div#main header span[dir="auto"]');
                                            const contact = headerEl ? headerEl.textContent.trim() : "Unknown";
                                            
                                            if (text && window.lastLuminaMsg !== text) {
                                                window.lastLuminaMsg = text;
                                                console.log("[LUMINA WHATSAPP] New message from " + contact + ": " + text);
                                                
                                                fetch('http://localhost:8000/whatsapp_reply', {
                                                    method: 'POST',
                                                    headers: { 'Content-Type': 'application/json' },
                                                    body: JSON.stringify({ text: text, sender: contact })
                                                })
                                                .then(res => res.json())
                                                .then(data => {
                                                    if (data.reply) {
                                                        const input = document.querySelector('div[contenteditable="true"][role="textbox"]');
                                                        if (input) {
                                                            input.focus();
                                                            document.execCommand('insertText', false, data.reply);
                                                            
                                                            setTimeout(() => {
                                                                const sendBtn = document.querySelector('span[data-icon="send"]');
                                                                if (sendBtn) {
                                                                    sendBtn.click();
                                                                } else {
                                                                    const enterEvent = new KeyboardEvent('keydown', {
                                                                        bubbles: true, cancelable: true, key: 'Enter', code: 'Enter', keyCode: 13
                                                                    });
                                                                    input.dispatchEvent(enterEvent);
                                                                }
                                                            }, 300);
                                                        }
                                                    }
                                                })
                                                .catch(err => console.error("[LUMINA WHATSAPP] Reply API error:", err));
                                            }
                                        }
                                    }
                                }, 1000);
                            }
                        }, 4000);
                    }
                `).catch(err => console.error("[ELECTRON WHATSAPP] Script injection failed:", err));
            }
        });

        browserViews[tabId] = view;
        view.webContents.loadURL(url || 'https://www.google.com');
    });

    ipcMain.on('browser-switch-tab', (event, { tabId }) => {
        if (activeTabId && browserViews[activeTabId]) {
            mainWindow.removeBrowserView(browserViews[activeTabId]);
        }

        activeTabId = tabId;

        if (activeTabId && browserViews[activeTabId]) {
            const view = browserViews[activeTabId];
            mainWindow.setBrowserView(view);
            if (currentBrowserBounds.visible) {
                const { screen } = require('electron');
                const winBounds = mainWindow.getBounds();
                const display = screen.getDisplayMatching(winBounds);
                const scale = display.scaleFactor || 1.0;
                const s = process.platform === 'win32' ? scale : 1.0;

                view.setBounds({
                    x: Math.round(currentBrowserBounds.x * s),
                    y: Math.round(currentBrowserBounds.y * s),
                    width: Math.round(currentBrowserBounds.width * s),
                    height: Math.round(currentBrowserBounds.height * s),
                });
            }
        }
    });

    ipcMain.on('browser-close-tab', (event, { tabId }) => {
        if (browserViews[tabId]) {
            const view = browserViews[tabId];
            if (activeTabId === tabId) {
                mainWindow.removeBrowserView(view);
                activeTabId = null;
            }
            view.webContents.close();
            delete browserViews[tabId];
        }
    });

    ipcMain.on('browser-load', (event, { tabId, url }) => {
        const targetTabId = tabId || activeTabId;
        const view = browserViews[targetTabId];
        let targetUrl = url;
        if (!/^https?:\/\//i.test(targetUrl)) {
            if (targetUrl.includes('.') && !targetUrl.includes(' ')) {
                targetUrl = 'https://' + targetUrl;
            } else {
                targetUrl = 'https://www.google.com/search?q=' + encodeURIComponent(targetUrl);
            }
        }
        // Stale-view recovery: if the view is gone/destroyed, ask the renderer
        // to recreate the tab instead of silently dropping the navigation.
        if (!view || view.webContents.isDestroyed()) {
            mainWindow.webContents.send('browser-event-stale', { tabId: targetTabId, url: targetUrl });
            return;
        }
        view.webContents.loadURL(targetUrl).catch(err => {
            mainWindow.webContents.send('browser-event-load-error', { tabId: targetTabId, url: targetUrl, error: String(err && err.message || err) });
        });
    });

    ipcMain.on('browser-go-back', (event, { tabId }) => {
        const targetTabId = tabId || activeTabId;
        if (targetTabId && browserViews[targetTabId] && browserViews[targetTabId].webContents.canGoBack()) {
            browserViews[targetTabId].webContents.goBack();
        }
    });

    ipcMain.on('browser-go-forward', (event, { tabId }) => {
        const targetTabId = tabId || activeTabId;
        if (targetTabId && browserViews[targetTabId] && browserViews[targetTabId].webContents.canGoForward()) {
            browserViews[targetTabId].webContents.goForward();
        }
    });

    ipcMain.on('browser-reload', (event, { tabId }) => {
        const targetTabId = tabId || activeTabId;
        if (targetTabId && browserViews[targetTabId]) {
            browserViews[targetTabId].webContents.reload();
        }
    });

    // ---- IPC robustness: invokable execute-JS with ack + stale-view guard ----
    // Renderer uses ipcRenderer.invoke('browser-execute-js', ...) and awaits a
    // result, so it can time out / retry rather than fire-and-forget.
    ipcMain.handle('browser-execute-js', async (event, { tabId, code }) => {
        const targetTabId = tabId || activeTabId;
        const view = browserViews[targetTabId];
        if (!view || view.webContents.isDestroyed()) {
            return { ok: false, error: 'no_live_view' };
        }
        try {
            const result = await view.webContents.executeJavaScript(code, true);
            return { ok: true, result };
        } catch (e) {
            return { ok: false, error: String(e && e.message || e) };
        }
    });

    // ---- YouTube playback automation (Task: play first result in-panel) ----
    // Navigates the active tab to a YouTube search, then polls the DOM to click
    // the first real video, waits for the <video> player, calls play(), unmutes,
    // and confirms playback. Retries past ads / unavailable / age-gated results.
    ipcMain.handle('browser-youtube-play', async (event, { tabId, query }) => {
        const targetTabId = tabId || activeTabId;
        const view = browserViews[targetTabId];
        if (!view || view.webContents.isDestroyed()) {
            return { ok: false, error: 'no_live_view' };
        }
        const wc = view.webContents;
        const searchUrl = 'https://www.youtube.com/results?search_query=' +
            encodeURIComponent(query || '');
        try {
            await wc.loadURL(searchUrl);
        } catch (e) {
            return { ok: false, error: 'load_failed: ' + String(e && e.message || e) };
        }

        // 1. Wait for results + click the first valid video link.
        const clickScript = `
        (async () => {
          const sleep = ms => new Promise(r => setTimeout(r, ms));
          // wait up to 8s for result renderers
          for (let i = 0; i < 40; i++) {
            const links = [...document.querySelectorAll('a#video-title, a.ytd-video-renderer, ytd-video-renderer a#thumbnail')]
              .filter(a => a.href && a.href.includes('/watch?v='));
            if (links.length) {
              const target = links[0];
              const href = target.href;
              target.click();
              return { clicked: true, href };
            }
            await sleep(200);
          }
          return { clicked: false };
        })();`;
        let clickRes;
        try { clickRes = await wc.executeJavaScript(clickScript, true); }
        catch (e) { return { ok: false, error: 'click_script_error: ' + String(e) }; }
        if (!clickRes || !clickRes.clicked) {
            return { ok: false, error: 'no_results' };
        }

        // 2. Wait for the player, call play(), unmute, verify — retry on ad/unavailable.
        const playScript = `
        (async () => {
          const sleep = ms => new Promise(r => setTimeout(r, ms));
          // A genuine unavailability shows a persistent error AND no usable video.
          const hardError = () => {
            const err = document.querySelector('.ytp-error, yt-playability-error-supported-renderers');
            const v = document.querySelector('video');
            return !!err && (!v || (v.readyState < 2 && !v.currentTime));
          };
          for (let attempt = 0; attempt < 3; attempt++) {
            // wait for a usable <video> up to 8s (don't bail on transient errors)
            let v = null;
            for (let i = 0; i < 40; i++) {
              v = document.querySelector('video.html5-main-video, video');
              if (v && v.readyState >= 2) break;
              await sleep(200);
            }
            if (!v) {
              // no video at all — if a hard error is showing, it's unavailable
              if (hardError()) return { playing: false, reason: 'unavailable' };
              await sleep(500); continue;
            }
            try { v.muted = false; v.volume = Math.max(v.volume, 0.5); } catch (e) {}
            try { await v.play(); } catch (e) {}
            await sleep(600);
            if (!v.paused && v.currentTime > 0) {
              const ad = !!document.querySelector('.ad-showing, .ytp-ad-player-overlay');
              return { playing: true, currentTime: v.currentTime, muted: v.muted, ad, url: location.href };
            }
            // paused (autoplay blocked or ad transition) — try again
            await sleep(700);
          }
          const v = document.querySelector('video');
          return { playing: v ? (!v.paused && v.currentTime > 0) : false, reason: 'retry_exhausted' };
        })();`;
        let playRes;
        try { playRes = await wc.executeJavaScript(playScript, true); }
        catch (e) { return { ok: false, error: 'play_script_error: ' + String(e) }; }
        return { ok: true, ...playRes };
    });

    ipcMain.on('browser-set-bounds', (event, bounds) => {
        currentBrowserBounds = bounds;
        if (activeTabId && browserViews[activeTabId]) {
            const view = browserViews[activeTabId];
            if (bounds.visible) {
                mainWindow.setBrowserView(view);

                const { screen } = require('electron');
                const winBounds = mainWindow.getBounds();
                const display = screen.getDisplayMatching(winBounds);
                const scale = display.scaleFactor || 1.0;
                const s = process.platform === 'win32' ? scale : 1.0;

                view.setBounds({
                    x: Math.round(bounds.x * s),
                    y: Math.round(bounds.y * s),
                    width: Math.round(bounds.width * s),
                    height: Math.round(bounds.height * s),
                });
            } else {
                mainWindow.removeBrowserView(view);
            }
        }
    });

    // Overlay guard: hide/show the BrowserView WITHOUT losing its geometry.
    // Native BrowserView renders above the DOM, so confirmation/alarm overlays
    // are otherwise occluded. The renderer calls this to detach the view while
    // an overlay is active, then re-attach with the last known bounds.
    ipcMain.on('browser-set-visible', (event, { visible }) => {
        if (!(activeTabId && browserViews[activeTabId])) return;
        const view = browserViews[activeTabId];
        if (!visible) {
            mainWindow.removeBrowserView(view);
            return;
        }
        if (!currentBrowserBounds.visible) return; // panel not open; nothing to show
        mainWindow.setBrowserView(view);
        const { screen } = require('electron');
        const winBounds = mainWindow.getBounds();
        const display = screen.getDisplayMatching(winBounds);
        const scale = display.scaleFactor || 1.0;
        const s = process.platform === 'win32' ? scale : 1.0;
        view.setBounds({
            x: Math.round(currentBrowserBounds.x * s),
            y: Math.round(currentBrowserBounds.y * s),
            width: Math.round(currentBrowserBounds.width * s),
            height: Math.round(currentBrowserBounds.height * s),
        });
    });

    ipcMain.on('browser-devtools', (event, { tabId }) => {
        const targetTabId = tabId || activeTabId;
        if (targetTabId && browserViews[targetTabId]) {
            browserViews[targetTabId].webContents.toggleDevTools();
        }
    });

    discoverBackendPort().then((port) => {
        if (port !== null) {
            console.log(`Backend is already running manually on port ${port}.`);
            backendPort = port;
            createWindow();
        } else {
            console.log('No manual backend found. Starting Python backend...');
            startPythonBackend();
            // Wait for backend to be ready on the discovered port
            waitForBackend().then(createWindow);
        }
    });

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) createWindow();
    });
});

function checkBackendPort(port) {
    return new Promise((resolve) => {
        const net = require('net');
        const server = net.createServer();
        server.once('error', (err) => {
            if (err.code === 'EADDRINUSE') {
                resolve(true);
            } else {
                resolve(false);
            }
        });
        server.once('listening', () => {
            server.close();
            resolve(false);
        });
        server.listen(port);
    });
}

function discoverBackendPort() {
    return new Promise((resolve) => {
        const http = require('http');
        let portToTry = 8000;

        const tryNext = () => {
            if (portToTry > 8009) {
                console.log('[TRACE] [ELECTRON DISCOVERY] Could not find active manual backend on ports 8000-8009.');
                resolve(null);
                return;
            }

            console.log(`[TRACE] [ELECTRON DISCOVERY] Probing http://127.0.0.1:${portToTry}/status...`);
            const req = http.get(`http://127.0.0.1:${portToTry}/status`, { timeout: 2000 }, (res) => {
                let body = '';
                res.on('data', chunk => body += chunk);
                res.on('end', () => {
                    try {
                        const parsed = JSON.parse(body);
                        if (parsed.status === 'running' && parsed.service === 'Lumina Backend') {
                            console.log(`[TRACE] [ELECTRON DISCOVERY] Found active manual backend on port ${portToTry}`);
                            resolve(portToTry);
                            return;
                        }
                    } catch (e) { }
                    portToTry++;
                    tryNext();
                });
            });
            req.on('error', (err) => {
                console.log(`[TRACE] [ELECTRON DISCOVERY] Port ${portToTry} check error: ${err.message}`);
                portToTry++;
                tryNext();
            });
            req.on('timeout', () => {
                console.log(`[TRACE] [ELECTRON DISCOVERY] Port ${portToTry} check timed out (2s)`);
                req.destroy();
                portToTry++;
                tryNext();
            });
        };

        tryNext();
    });
}

function waitForBackend() {
    return new Promise((resolve) => {
        const check = () => {
            const http = require('http');
            console.log(`Waiting for backend on port ${backendPort}...`);
            http.get(`http://127.0.0.1:${backendPort}/status`, (res) => {
                if (res.statusCode === 200) {
                    console.log('Backend is ready!');
                    resolve();
                } else {
                    console.log('Backend not ready, retrying...');
                    setTimeout(check, 1000);
                }
            }).on('error', (err) => {
                console.log('Waiting for backend...');
                setTimeout(check, 1000);
            });
        };
        check();
    });
}

let windowWasShown = false;

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin' && windowWasShown) {
        app.quit();
    } else if (!windowWasShown) {
        console.log('Window was never shown - keeping app alive to allow retries');
    }
});

app.on('will-quit', () => {
    console.log('App closing... Killing Python backend.');
    if (pythonProcess && pythonProcess.pid) {
        if (process.platform === 'win32') {
            try {
                const { execSync } = require('child_process');
                try {
                    execSync(`tasklist /FI "PID eq ${pythonProcess.pid}" 2>nul | find "${pythonProcess.pid}" >nul`);
                    execSync(`taskkill /pid ${pythonProcess.pid} /f /t`);
                    console.log(`Killed Python process ${pythonProcess.pid}`);
                } catch (checkError) {
                    console.log(`Python process ${pythonProcess.pid} already terminated`);
                }
            } catch (e) {
                console.error('Failed to kill python process:', e.message);
            }
        } else {
            try {
                pythonProcess.kill('SIGKILL');
            } catch (e) {
                console.log('Python process already terminated');
            }
        }
        pythonProcess = null;
    }
});