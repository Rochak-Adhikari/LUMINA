const { app, BrowserWindow, ipcMain, BrowserView, session } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

// Use ANGLE D3D11 backend - more stable on Windows while keeping WebGL working
// This fixes "GPU state invalid after WaitForGetOffsetInRange" error
app.commandLine.appendSwitch('use-angle', 'd3d11');
app.commandLine.appendSwitch('enable-features', 'Vulkan');
app.commandLine.appendSwitch('ignore-gpu-blocklist');
// Expose CDP port 9223 so that backend Playwright can connect directly to internal tabs
app.commandLine.appendSwitch('remote-debugging-port', '9223');

let mainWindow;
let pythonProcess;

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

    // In dev, load Vite server. In prod, load index.html
    const isDev = process.env.NODE_ENV !== 'production';

    const loadFrontend = (retries = 3) => {
        const url = isDev ? 'http://localhost:5173' : null;
        const loadPromise = isDev
            ? mainWindow.loadURL(url)
            : mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));

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
        CONDA_DEFAULT_ENV: 'E:\\AI\\conda_envs\\lumina'
    });

    pythonProcess = spawn(pythonExe, [scriptPath], {
        cwd: path.join(__dirname, '../backend'),
        env: childEnv
    });

    pythonProcess.stdout.on('data', (data) => {
        console.log(`[Python]: ${data}`);
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
        if (targetTabId && browserViews[targetTabId]) {
            let targetUrl = url;
            if (!/^https?:\/\//i.test(targetUrl)) {
                if (targetUrl.includes('.') && !targetUrl.includes(' ')) {
                    targetUrl = 'https://' + targetUrl;
                } else {
                    targetUrl = 'https://www.google.com/search?q=' + encodeURIComponent(targetUrl);
                }
            }
            browserViews[targetTabId].webContents.loadURL(targetUrl);
        }
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

    ipcMain.on('browser-devtools', (event, { tabId }) => {
        const targetTabId = tabId || activeTabId;
        if (targetTabId && browserViews[targetTabId]) {
            browserViews[targetTabId].webContents.toggleDevTools();
        }
    });

    checkBackendPort(8000).then((isTaken) => {
        if (isTaken) {
            console.log('Port 8000 is taken. Assuming backend is already running manually.');
            waitForBackend().then(createWindow);
        } else {
            startPythonBackend();
            setTimeout(() => {
                waitForBackend().then(createWindow);
            }, 1000);
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

function waitForBackend() {
    return new Promise((resolve) => {
        const check = () => {
            const http = require('http');
            http.get('http://127.0.0.1:8000/status', (res) => {
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
