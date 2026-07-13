import React, { useState } from 'react';
import {
    Sparkles, Mic, Brain, Globe, FileText, Code2, Monitor,
    Smartphone, Gamepad2, PlaneTakeoff, Music, Search, Bell,
    Camera, FolderOpen, Terminal, Mail, Settings, Cpu, Video,
    ChevronDown, ChevronUp, Zap, Shield, Layers
} from 'lucide-react';

// ─── Feature Data ────────────────────────────────────────────────────────────

const CATEGORIES = ['All', 'Voice & AI', 'Actions', 'System', 'Creative', 'Remote'];

const FEATURES = [
    // ── Voice & AI ──
    {
        id: 'voice',
        category: 'Voice & AI',
        icon: Mic,
        color: 'cyan',
        title: 'Real-Time Voice Conversation',
        subtitle: 'Gemini Live API · VAD · Streaming TTS',
        description:
            'Talk to Lumina naturally using your microphone. Voice Activity Detection (VAD) automatically detects when you start and stop speaking — no push-to-talk needed. Lumina responds in real-time with a synthesized voice.',
        usage: [
            'Click the mic button or press the hotkey to unmute.',
            'Speak naturally — Lumina listens and responds immediately.',
            'Lumina interrupts herself if you start talking mid-reply.',
        ],
        badge: 'Always On',
    },
    {
        id: 'memory',
        category: 'Voice & AI',
        icon: Brain,
        color: 'violet',
        title: 'Hybrid Long-Term Memory',
        subtitle: 'SQLite · FAISS · FTS5 · RRF Fusion',
        description:
            'Lumina remembers facts, preferences, and session summaries across restarts. Memory uses a three-layer retrieval engine: exact keyword search (FTS5), semantic vector search (FAISS), and a Reciprocal Rank Fusion (RRF) combiner to surface the most relevant context.',
        usage: [
            'Say "remember that I prefer dark mode" — Lumina stores it automatically.',
            'Ask "what do you know about me?" to hear recalled memories.',
            'Memory is reviewed at each startup so Lumina never forgets who you are.',
        ],
        badge: 'Persistent',
    },
    {
        id: 'persona',
        category: 'Voice & AI',
        icon: Sparkles,
        color: 'fuchsia',
        title: 'Persona & Emotional Engine',
        subtitle: 'Emotion · Idle Mind · Debate · Jealousy',
        description:
            'Lumina has a living personality. She can tease, debate, feel jealous, and proactively break the silence when she is idle. Persona modes range from "playful best friend" to "professional assistant". The intensity of each trait is configurable.',
        usage: [
            'Adjust persona mode in Settings → Persona.',
            'Set teasing intensity from 0 (off) to 3 (maximum chaos).',
            'Enable idle mind to have Lumina start conversations on her own.',
        ],
        badge: 'Configurable',
    },
    {
        id: 'face_auth',
        category: 'Voice & AI',
        icon: Camera,
        color: 'amber',
        title: 'Face Authentication',
        subtitle: 'MediaPipe · Face Landmarks · Privacy Gate',
        description:
            'Lumina uses your webcam to verify your face before allowing access. Uses Google MediaPipe face landmark detection — runs entirely locally, no cloud processing. Can be disabled for shared machines.',
        usage: [
            'Enable in Settings → Face Auth.',
            'Register your face by holding a reference photo named reference.jpg in the backend folder.',
            'Disable if you share your machine with others.',
        ],
        badge: 'Optional',
    },

    // ── Actions ──
    {
        id: 'web_search',
        category: 'Actions',
        icon: Search,
        color: 'cyan',
        title: 'Web Search',
        subtitle: 'Real-time internet lookup',
        description:
            'Lumina can search the web and summarise results for you in plain language. Ask any factual question and she will retrieve up-to-date answers instead of relying on training data alone.',
        usage: [
            '"Lumina, search for the latest news about AI."',
            '"What is the current price of Bitcoin?"',
            '"Find me a good chicken tikka masala recipe."',
        ],
        badge: 'Built-in',
    },
    {
        id: 'browser',
        category: 'Actions',
        icon: Globe,
        color: 'sky',
        title: 'Browser Control',
        subtitle: 'Headless Playwright · CDP Brave · Local Browser',
        description:
            'Two browser backends: a headless Playwright instance for silent automation, and a CDP-connected Brave profile for interacting with your real browser session. Lumina can navigate, click, fill forms, read pages, and screenshot.',
        usage: [
            '"Open YouTube and play lo-fi music."',
            '"Go to github.com and search for React."',
            '"Read the main article on that page."',
        ],
        badge: 'Dual Mode',
    },
    {
        id: 'file_processor',
        category: 'Actions',
        icon: FileText,
        color: 'emerald',
        title: 'File Processor (AI Analysis)',
        subtitle: 'PDF · Image · CSV · Audio · Video',
        description:
            'Drop a file and ask Lumina to analyse it. Supported formats include PDFs (text extraction + summarisation), images (description + OCR), CSV data (statistics + insights), audio (transcription), and video (scene description).',
        usage: [
            '"Analyse this PDF and give me the key points."',
            '"What is in this image?"',
            '"Summarise this CSV — what are the trends?"',
            'Upload via the mobile dashboard file-drop or the desktop UI.',
        ],
        badge: 'Multi-format',
    },
    {
        id: 'file_controller',
        category: 'Actions',
        icon: FolderOpen,
        color: 'orange',
        title: 'File Controller',
        subtitle: 'Create · Read · Move · Delete · List',
        description:
            'Full CRUD file-system operations. Lumina can create, read, rename, move, copy, and delete files and folders on your machine. Destructive operations go through the confirmation gate.',
        usage: [
            '"Create a new folder called Projects on my Desktop."',
            '"Move all .txt files in Downloads to Documents."',
            '"List the contents of my Documents folder."',
        ],
        badge: 'Confirmed',
    },
    {
        id: 'dev_agent',
        category: 'Actions',
        icon: Code2,
        color: 'violet',
        title: 'Dev Agent',
        subtitle: 'Multi-file scaffolding · Dependency install · Auto-fix',
        description:
            'Give Lumina a project description and she will plan, write every file, install dependencies, open VS Code, run the code, and auto-fix errors — all hands-free. Built on top of the code_helper module for single-snippet tasks.',
        usage: [
            '"Build me a Flask REST API with a /hello endpoint."',
            '"Create a React dashboard that shows my GitHub repos."',
            '"Write a Python script that scrapes product prices and saves them to CSV."',
        ],
        badge: 'Autonomous',
    },
    {
        id: 'flight_finder',
        category: 'Actions',
        icon: PlaneTakeoff,
        color: 'sky',
        title: 'Flight Finder',
        subtitle: 'Google Flights · Web Scraping · Price Parsing',
        description:
            'Search for flights between any two cities. Lumina opens Google Flights in the background, parses available options, and presents the cheapest and most convenient routes.',
        usage: [
            '"Find me flights from Kathmandu to Dubai next Friday."',
            '"What is the cheapest flight from London to Tokyo in August?"',
        ],
        badge: 'Live Data',
    },
    {
        id: 'game_updater',
        category: 'Actions',
        icon: Gamepad2,
        color: 'fuchsia',
        title: 'Game Updater',
        subtitle: 'Steam · Epic Games · Install & Update',
        description:
            'Control Steam and Epic Games from voice. Lumina can detect installed games, trigger updates, install new titles, and check download status — no clicking required.',
        usage: [
            '"Update all my Steam games."',
            '"Install Fortnite from Epic Games."',
            '"Check if Cyberpunk 2077 has any pending updates."',
        ],
        badge: 'PC Gaming',
    },
    {
        id: 'send_message',
        category: 'Actions',
        icon: Mail,
        color: 'cyan',
        title: 'Send Messages',
        subtitle: 'WhatsApp · Discord · Email · SMS',
        description:
            'Send messages to your contacts on various platforms without touching your phone or keyboard. Lumina opens the messaging app, composes the message, and sends it.',
        usage: [
            '"Send a WhatsApp to mom saying I\'ll be home late."',
            '"Message Rahul on Discord: GG well played."',
            '"Email my boss the Q3 report summary."',
        ],
        badge: 'Multi-Platform',
    },
    {
        id: 'reminder',
        category: 'Actions',
        icon: Bell,
        color: 'amber',
        title: 'Reminders & Alarms',
        subtitle: 'Scheduled · Persistent · Alarm Overlay',
        description:
            'Set reminders for any future time. When the time arrives, Lumina fires an alarm overlay on-screen and calls your name aloud. Reminders survive restarts and are stored in the database.',
        usage: [
            '"Remind me to take my medicine at 8 PM."',
            '"Set an alarm for tomorrow 7:30 AM."',
            '"Remind me in 30 minutes to check the oven."',
        ],
        badge: 'Persistent',
    },
    {
        id: 'spotify',
        category: 'Actions',
        icon: Music,
        color: 'green',
        title: 'Spotify Control',
        subtitle: 'Play · Pause · Skip · Queue · Volume',
        description:
            'Full Spotify playback control via voice. Search for songs, artists, or playlists, play them, skip tracks, adjust volume, and queue music — hands-free.',
        usage: [
            '"Play Blinding Lights on Spotify."',
            '"Skip this song."',
            '"Volume up."',
            '"Queue some lofi hip-hop."',
        ],
        badge: 'Music',
    },
    {
        id: 'youtube',
        category: 'Actions',
        icon: Video,
        color: 'red',
        title: 'YouTube Control',
        subtitle: 'Search · Play · Pause · Skip · Queue',
        description:
            'Search for and play YouTube videos via voice. Controls playback in your real browser session so you can pause, skip, and navigate videos without touching the keyboard.',
        usage: [
            '"Play MrBeast\'s latest video."',
            '"Search for how to make pasta on YouTube."',
            '"Pause the video."',
        ],
        badge: 'Browser',
    },

    // ── System ──
    {
        id: 'computer_control',
        category: 'System',
        icon: Cpu,
        color: 'orange',
        title: 'Computer Control',
        subtitle: 'Mouse · Keyboard · Clipboard · Hotkeys',
        description:
            'Low-level PC control: move the mouse, simulate keyboard input, copy/paste clipboard content, press hotkeys, and interact with any window. Useful for automating GUI tasks that have no API.',
        usage: [
            '"Press Ctrl+S to save."',
            '"Click the submit button."',
            '"Copy the text in the active window."',
        ],
        badge: 'Automation',
    },
    {
        id: 'computer_settings',
        category: 'System',
        icon: Settings,
        color: 'slate',
        title: 'Computer Settings',
        subtitle: 'Volume · Brightness · Wi-Fi · Power',
        description:
            'Adjust Windows system settings via voice. Control speaker volume, screen brightness, toggle Wi-Fi/Bluetooth, switch power plans, and lock/sleep/shutdown the machine.',
        usage: [
            '"Set volume to 50%."',
            '"Reduce brightness by 20%."',
            '"Turn off Wi-Fi."',
            '"Lock the computer."',
        ],
        badge: 'Windows',
    },
    {
        id: 'open_app',
        category: 'System',
        icon: Layers,
        color: 'indigo',
        title: 'Open Applications',
        subtitle: 'Launch · Focus · Close any app',
        description:
            'Open, focus, or close any installed application by name. Lumina maps natural names like "calculator" or "notepad" to the correct executable and launches it instantly.',
        usage: [
            '"Open Notepad."',
            '"Launch VS Code."',
            '"Close Spotify."',
        ],
        badge: 'Launcher',
    },
    {
        id: 'screen_process',
        category: 'System',
        icon: Monitor,
        color: 'cyan',
        title: 'Screen Processor',
        subtitle: 'Screenshot · OCR · Visual Q&A',
        description:
            'Lumina can take a screenshot, run OCR to extract text, and answer questions about what is on your screen. Useful for reading error messages, UI labels, or anything displayed visually.',
        usage: [
            '"What does the error message on my screen say?"',
            '"Read the text in this dialog box."',
            '"Take a screenshot and describe what you see."',
        ],
        badge: 'Vision',
    },
    {
        id: 'desktop_control',
        category: 'System',
        icon: Monitor,
        color: 'teal',
        title: 'Desktop Control',
        subtitle: 'Window management · Taskbar · Workspace',
        description:
            'Manage your Windows desktop: minimise, maximise, tile, or close windows; switch virtual desktops; arrange workspaces; and interact with the taskbar.',
        usage: [
            '"Minimise all windows."',
            '"Maximise Chrome."',
            '"Switch to virtual desktop 2."',
        ],
        badge: 'Windows',
    },
    {
        id: 'cmd',
        category: 'System',
        icon: Terminal,
        color: 'lime',
        title: 'Command Line Control',
        subtitle: 'CMD · PowerShell · Shell scripts',
        description:
            'Execute shell commands, PowerShell scripts, and batch files. Lumina can run arbitrary commands, capture output, and relay results back to you in plain language.',
        usage: [
            '"Run ipconfig and tell me my IP address."',
            '"Execute the deploy.bat script."',
            '"Check disk usage with PowerShell."',
        ],
        badge: 'Shell',
    },

    // ── Remote ──
    {
        id: 'phone_dashboard',
        category: 'Remote',
        icon: Smartphone,
        color: 'violet',
        title: 'Remote Phone Dashboard',
        subtitle: 'LAN · AES-256 · QR Code Pairing · Phone Mic',
        description:
            'Access Lumina from your phone via your local network. A secure web interface lets you type commands, view the conversation log, stream your phone microphone as input, and upload files directly from your phone to your PC.',
        usage: [
            'Open Settings → Remote Control and scan the QR code with your phone.',
            'Enter the 6-digit PIN in the mobile browser.',
            'Type commands or tap the mic button to send audio from your phone.',
            'Drag and drop files onto the mobile UI to share them with your PC.',
        ],
        badge: 'LAN',
    },
    {
        id: 'cad',
        category: 'Creative',
        icon: Layers,
        color: 'amber',
        title: 'CAD Design Agent',
        subtitle: 'OpenSCAD · AI Geometry · 3D Print Ready',
        description:
            'Describe a 3D object and Lumina will generate OpenSCAD code, render a preview, and iterate based on your feedback. Outputs are print-ready STL files for your 3D printer.',
        usage: [
            '"Design a wall-mount phone holder with a 15-degree tilt."',
            '"Make it 10% thicker."',
            '"Export the final design and send it to my printer."',
        ],
        badge: 'Creative',
    },
    {
        id: 'smart_home',
        category: 'Creative',
        icon: Zap,
        color: 'yellow',
        title: 'Smart Home (TP-Link Kasa)',
        subtitle: 'Lights · Switches · Plugs · Scenes',
        description:
            'Control TP-Link Kasa smart home devices on your network. Turn lights on and off, dim them, change colours, control smart plugs, and create scenes — all by voice.',
        usage: [
            '"Turn off the bedroom light."',
            '"Set the living room lights to 40% brightness."',
            '"Turn on the office plug."',
        ],
        badge: 'IoT',
    },
    {
        id: 'printer',
        category: 'Creative',
        icon: Shield,
        color: 'slate',
        title: '3D Printer Control',
        subtitle: 'Moonraker · OctoPrint · Status · Start · Cancel',
        description:
            'Monitor and control your 3D printers via voice. Compatible with Moonraker (Klipper) and OctoPrint. Check print status, start prints, cancel jobs, and view bed temperatures.',
        usage: [
            '"What is the status of my Creality K1?"',
            '"Cancel the current print."',
            '"What is the bed temperature?"',
        ],
        badge: '3D Print',
    },
];

// ─── Colour maps ──────────────────────────────────────────────────────────────

const COLOR_MAP = {
    cyan:    { border: 'border-cyan-500/30',    bg: 'bg-cyan-500/10',    icon: 'text-cyan-400',   badge: 'border-cyan-500/30 bg-cyan-500/10 text-cyan-400',   dot: 'bg-cyan-400' },
    violet:  { border: 'border-violet-500/30',  bg: 'bg-violet-500/10',  icon: 'text-violet-400', badge: 'border-violet-500/30 bg-violet-500/10 text-violet-400', dot: 'bg-violet-400' },
    fuchsia: { border: 'border-fuchsia-500/30', bg: 'bg-fuchsia-500/10', icon: 'text-fuchsia-400',badge: 'border-fuchsia-500/30 bg-fuchsia-500/10 text-fuchsia-400', dot: 'bg-fuchsia-400' },
    amber:   { border: 'border-amber-500/30',   bg: 'bg-amber-500/10',   icon: 'text-amber-400',  badge: 'border-amber-500/30 bg-amber-500/10 text-amber-400',  dot: 'bg-amber-400' },
    emerald: { border: 'border-emerald-500/30', bg: 'bg-emerald-500/10', icon: 'text-emerald-400',badge: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400', dot: 'bg-emerald-400' },
    sky:     { border: 'border-sky-500/30',     bg: 'bg-sky-500/10',     icon: 'text-sky-400',    badge: 'border-sky-500/30 bg-sky-500/10 text-sky-400',    dot: 'bg-sky-400' },
    orange:  { border: 'border-orange-500/30',  bg: 'bg-orange-500/10',  icon: 'text-orange-400', badge: 'border-orange-500/30 bg-orange-500/10 text-orange-400', dot: 'bg-orange-400' },
    green:   { border: 'border-green-500/30',   bg: 'bg-green-500/10',   icon: 'text-green-400',  badge: 'border-green-500/30 bg-green-500/10 text-green-400',  dot: 'bg-green-400' },
    red:     { border: 'border-red-500/30',     bg: 'bg-red-500/10',     icon: 'text-red-400',    badge: 'border-red-500/30 bg-red-500/10 text-red-400',    dot: 'bg-red-400' },
    indigo:  { border: 'border-indigo-500/30',  bg: 'bg-indigo-500/10',  icon: 'text-indigo-400', badge: 'border-indigo-500/30 bg-indigo-500/10 text-indigo-400', dot: 'bg-indigo-400' },
    teal:    { border: 'border-teal-500/30',    bg: 'bg-teal-500/10',    icon: 'text-teal-400',   badge: 'border-teal-500/30 bg-teal-500/10 text-teal-400',   dot: 'bg-teal-400' },
    lime:    { border: 'border-lime-500/30',    bg: 'bg-lime-500/10',    icon: 'text-lime-400',   badge: 'border-lime-500/30 bg-lime-500/10 text-lime-400',   dot: 'bg-lime-400' },
    slate:   { border: 'border-slate-500/30',   bg: 'bg-slate-500/10',   icon: 'text-slate-400',  badge: 'border-slate-500/30 bg-slate-500/10 text-slate-400',  dot: 'bg-slate-400' },
    yellow:  { border: 'border-yellow-500/30',  bg: 'bg-yellow-500/10',  icon: 'text-yellow-400', badge: 'border-yellow-500/30 bg-yellow-500/10 text-yellow-400', dot: 'bg-yellow-400' },
};

// ─── Feature Card ─────────────────────────────────────────────────────────────

const FeatureCard = ({ feature }) => {
    const [expanded, setExpanded] = useState(false);
    const Icon = feature.icon;
    const c = COLOR_MAP[feature.color] || COLOR_MAP.cyan;

    return (
        <div
            onClick={() => setExpanded(e => !e)}
            className={`group border bg-black/30 backdrop-blur-sm rounded-xl p-4 transition-all duration-200 cursor-pointer ${
                expanded
                    ? `${c.border} ${c.bg} shadow-[0_0_16px_rgba(6,182,212,0.06)]`
                    : 'border-cyan-500/12 hover:border-cyan-500/25 hover:bg-cyan-500/5'
            }`}
        >
            {/* Card header */}
            <div className="flex items-start gap-3 mb-2">
                <div className={`shrink-0 w-9 h-9 rounded-lg border ${c.border} ${c.bg} flex items-center justify-center`}>
                    <Icon size={18} className={c.icon} />
                </div>
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                        <h3 className="text-sm font-semibold text-cyan-100 group-hover:text-white transition-colors leading-tight">
                            {feature.title}
                        </h3>
                        <span className={`text-[10px] px-2 py-0.5 rounded-full border ${c.badge} shrink-0`}>
                            {feature.badge}
                        </span>
                    </div>
                    <p className="text-[11px] text-cyan-700 tracking-wide mt-0.5">{feature.subtitle}</p>
                </div>
                <div className="shrink-0 text-cyan-700 mt-1">
                    {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                </div>
            </div>

            {/* Description — always visible, truncated when collapsed */}
            <p className={`text-xs text-gray-400 leading-relaxed ${expanded ? '' : 'line-clamp-2'}`}>
                {feature.description}
            </p>

            {/* Usage examples — only when expanded */}
            {expanded && (
                <div className="mt-3 pt-3 border-t border-cyan-500/10">
                    <p className="text-[10px] text-cyan-600 tracking-widest uppercase mb-2">How to use</p>
                    <ul className="flex flex-col gap-1.5">
                        {feature.usage.map((tip, i) => (
                            <li key={i} className="flex items-start gap-2">
                                <div className={`shrink-0 w-1.5 h-1.5 rounded-full ${c.dot} mt-1.5`} />
                                <span className="text-xs text-gray-300 leading-relaxed">{tip}</span>
                            </li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    );
};

// ─── Main Panel ───────────────────────────────────────────────────────────────

const FeaturesPanel = () => {
    const [activeCategory, setActiveCategory] = useState('All');
    const [searchQuery, setSearchQuery] = useState('');

    const filtered = FEATURES.filter(f => {
        const matchesCat = activeCategory === 'All' || f.category === activeCategory;
        const q = searchQuery.toLowerCase();
        const matchesSearch = !q ||
            f.title.toLowerCase().includes(q) ||
            f.subtitle.toLowerCase().includes(q) ||
            f.description.toLowerCase().includes(q) ||
            f.category.toLowerCase().includes(q);
        return matchesCat && matchesSearch;
    });

    const totalCount = FEATURES.length;
    const filteredCount = filtered.length;

    return (
        <div className="p-6 max-w-6xl mx-auto">

            {/* ── Header ── */}
            <div className="flex items-center justify-between mb-6">
                <div>
                    <h2 className="text-xl font-bold text-cyan-200 tracking-widest">Feature Compendium</h2>
                    <p className="text-xs text-cyan-700 mt-1 tracking-wide">
                        {filteredCount} of {totalCount} capabilities · Click any card to see usage
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse shadow-[0_0_6px_rgba(6,182,212,0.8)]" />
                    <span className="text-[10px] text-cyan-600 tracking-widest uppercase">Lumina v2.0</span>
                </div>
            </div>

            {/* ── Search ── */}
            <div className="max-w-xl mx-auto mb-5">
                <div className="relative">
                    <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-cyan-700" />
                    <input
                        type="text"
                        value={searchQuery}
                        onChange={e => setSearchQuery(e.target.value)}
                        placeholder="Search features, commands, capabilities…"
                        className="w-full bg-black/40 border border-cyan-700/30 rounded-lg pl-10 pr-4 py-2.5 text-sm text-cyan-50 focus:outline-none focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400/50 transition-all placeholder-cyan-800/50 backdrop-blur-sm"
                    />
                </div>
            </div>

            {/* ── Category Tabs ── */}
            <div className="flex justify-center gap-2 mb-7 flex-wrap">
                {CATEGORIES.map(cat => (
                    <button
                        key={cat}
                        onClick={() => setActiveCategory(cat)}
                        className={`px-3 py-1 text-xs rounded-md border transition-all duration-200 ${
                            activeCategory === cat
                                ? 'border-cyan-500/50 bg-cyan-500/10 text-cyan-300 shadow-[0_0_8px_rgba(6,182,212,0.1)]'
                                : 'border-cyan-800/30 text-cyan-600 hover:border-cyan-500/30 hover:text-cyan-400'
                        }`}
                    >
                        {cat}
                        {cat !== 'All' && (
                            <span className="ml-1.5 text-[9px] text-cyan-700">
                                {FEATURES.filter(f => f.category === cat).length}
                            </span>
                        )}
                    </button>
                ))}
            </div>

            {/* ── Cards Grid ── */}
            {filtered.length > 0 ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                    {filtered.map(feature => (
                        <FeatureCard key={feature.id} feature={feature} />
                    ))}
                </div>
            ) : (
                <div className="text-center py-16">
                    <div className="w-12 h-12 rounded-full border border-cyan-500/20 flex items-center justify-center mx-auto mb-4">
                        <Search size={20} className="text-cyan-700" />
                    </div>
                    <p className="text-cyan-600 text-sm mb-1">No features match your search</p>
                    <p className="text-cyan-800 text-xs">Try a different keyword or category.</p>
                </div>
            )}

            {/* ── Footer tip ── */}
            <div className="mt-8 pt-5 border-t border-cyan-500/10 text-center">
                <p className="text-[11px] text-cyan-800 tracking-wide">
                    All actions require explicit permission in Settings → Tool Permissions before Lumina can execute them.
                </p>
            </div>
        </div>
    );
};

export default FeaturesPanel;
