// frontend/pages/Skills/featuresData.js
// Capability catalog for the Skills page (migrated from src/Ui_TEST FeaturesPanel).
// Data-only module — no view logic. Removed capabilities (CAD, Kasa smart-home,
// 3D printer) are intentionally NOT included: those backend runtimes were
// removed in earlier phases, so advertising them would be inaccurate.
import {
  Sparkles, Mic, Brain, Globe, FileText, Code2, Monitor,
  Smartphone, Gamepad2, PlaneTakeoff, Music, Search, Bell,
  Camera, FolderOpen, Terminal, Mail, Settings, Cpu, Video, Layers,
} from 'lucide-react';

export const FEATURE_CATEGORIES = ['All', 'Voice & AI', 'Actions', 'System', 'Remote'];

export const FEATURES = [
  // ── Voice & AI ──
  { id: 'voice', category: 'Voice & AI', icon: Mic, color: 'cyan', title: 'Real-Time Voice Conversation', subtitle: 'Gemini Live API · VAD · Streaming TTS',
    description: 'Talk to Lumina naturally using your microphone. Voice Activity Detection (VAD) automatically detects when you start and stop speaking — no push-to-talk needed. Lumina responds in real-time with a synthesized voice.',
    usage: ['Click the mic button or press the hotkey to unmute.', 'Speak naturally — Lumina listens and responds immediately.', 'Lumina interrupts herself if you start talking mid-reply.'], badge: 'Always On' },
  { id: 'memory', category: 'Voice & AI', icon: Brain, color: 'violet', title: 'Hybrid Long-Term Memory', subtitle: 'SQLite · FAISS · FTS5 · RRF Fusion',
    description: 'Lumina remembers facts, preferences, and session summaries across restarts. Memory uses a three-layer retrieval engine: exact keyword search (FTS5), semantic vector search (FAISS), and a Reciprocal Rank Fusion (RRF) combiner to surface the most relevant context.',
    usage: ['Say "remember that I prefer dark mode" — Lumina stores it automatically.', 'Ask "what do you know about me?" to hear recalled memories.', 'Memory is reviewed at each startup so Lumina never forgets who you are.'], badge: 'Persistent' },
  { id: 'persona', category: 'Voice & AI', icon: Sparkles, color: 'fuchsia', title: 'Persona & Emotional Engine', subtitle: 'Emotion · Idle Mind · Debate · Jealousy',
    description: 'Lumina has a living personality. She can tease, debate, feel jealous, and proactively break the silence when she is idle. Persona modes range from "playful best friend" to "professional assistant". The intensity of each trait is configurable.',
    usage: ['Adjust persona mode in Settings → Persona.', 'Set teasing intensity from 0 (off) to 3 (maximum chaos).', 'Enable idle mind to have Lumina start conversations on her own.'], badge: 'Configurable' },
  { id: 'face_auth', category: 'Voice & AI', icon: Camera, color: 'amber', title: 'Face Authentication', subtitle: 'MediaPipe · Face Landmarks · Privacy Gate',
    description: 'Lumina uses your webcam to verify your face before allowing access. Uses Google MediaPipe face landmark detection — runs entirely locally, no cloud processing. Can be disabled for shared machines.',
    usage: ['Enable in Settings → Face Auth.', 'Register your face by holding a reference photo named reference.jpg in the backend folder.', 'Disable if you share your machine with others.'], badge: 'Optional' },

  // ── Actions ──
  { id: 'web_search', category: 'Actions', icon: Search, color: 'cyan', title: 'Web Search', subtitle: 'Real-time internet lookup',
    description: 'Lumina can search the web and summarise results for you in plain language. Ask any factual question and she will retrieve up-to-date answers instead of relying on training data alone.',
    usage: ['"Lumina, search for the latest news about AI."', '"What is the current price of Bitcoin?"', '"Find me a good chicken tikka masala recipe."'], badge: 'Built-in' },
  { id: 'browser', category: 'Actions', icon: Globe, color: 'sky', title: 'Browser Control', subtitle: 'Embedded Chromium · Local Browser · Automation',
    description: 'Lumina drives the embedded browser workspace and a local browser session for interacting with real sites. She can navigate, click, fill forms, read pages, and screenshot.',
    usage: ['"Open YouTube and play lo-fi music."', '"Go to github.com and search for React."', '"Read the main article on that page."'], badge: 'Embedded' },
  { id: 'file_processor', category: 'Actions', icon: FileText, color: 'emerald', title: 'File Processor (AI Analysis)', subtitle: 'PDF · Image · CSV · Audio · Video',
    description: 'Drop a file and ask Lumina to analyse it. Supported formats include PDFs (text extraction + summarisation), images (description + OCR), CSV data (statistics + insights), audio (transcription), and video (scene description).',
    usage: ['"Analyse this PDF and give me the key points."', '"What is in this image?"', '"Summarise this CSV — what are the trends?"', 'Upload via the mobile dashboard file-drop or the desktop UI.'], badge: 'Multi-format' },
  { id: 'file_controller', category: 'Actions', icon: FolderOpen, color: 'orange', title: 'File Controller', subtitle: 'Create · Read · Move · Delete · List',
    description: 'Full CRUD file-system operations. Lumina can create, read, rename, move, copy, and delete files and folders on your machine. Destructive operations go through the confirmation gate.',
    usage: ['"Create a new folder called Projects on my Desktop."', '"Move all .txt files in Downloads to Documents."', '"List the contents of my Documents folder."'], badge: 'Confirmed' },
  { id: 'dev_agent', category: 'Actions', icon: Code2, color: 'violet', title: 'Dev Agent', subtitle: 'Multi-file scaffolding · Dependency install · Auto-fix',
    description: 'Give Lumina a project description and she will plan, write every file, install dependencies, open VS Code, run the code, and auto-fix errors — all hands-free. Built on top of the code_helper module for single-snippet tasks.',
    usage: ['"Build me a Flask REST API with a /hello endpoint."', '"Create a React dashboard that shows my GitHub repos."', '"Write a Python script that scrapes product prices and saves them to CSV."'], badge: 'Autonomous' },
  { id: 'flight_finder', category: 'Actions', icon: PlaneTakeoff, color: 'sky', title: 'Flight Finder', subtitle: 'Google Flights · Web Scraping · Price Parsing',
    description: 'Search for flights between any two cities. Lumina opens Google Flights in the background, parses available options, and presents the cheapest and most convenient routes.',
    usage: ['"Find me flights from Kathmandu to Dubai next Friday."', '"What is the cheapest flight from London to Tokyo in August?"'], badge: 'Live Data' },
  { id: 'game_updater', category: 'Actions', icon: Gamepad2, color: 'fuchsia', title: 'Game Updater', subtitle: 'Steam · Epic Games · Install & Update',
    description: 'Control Steam and Epic Games from voice. Lumina can detect installed games, trigger updates, install new titles, and check download status — no clicking required.',
    usage: ['"Update all my Steam games."', '"Install Fortnite from Epic Games."', '"Check if Cyberpunk 2077 has any pending updates."'], badge: 'PC Gaming' },
  { id: 'send_message', category: 'Actions', icon: Mail, color: 'cyan', title: 'Send Messages', subtitle: 'WhatsApp · Discord · Email · SMS',
    description: 'Send messages to your contacts on various platforms without touching your phone or keyboard. Lumina opens the messaging app, composes the message, and sends it.',
    usage: ['"Send a WhatsApp to mom saying I\'ll be home late."', '"Message Rahul on Discord: GG well played."', '"Email my boss the Q3 report summary."'], badge: 'Multi-Platform' },
  { id: 'reminder', category: 'Actions', icon: Bell, color: 'amber', title: 'Reminders & Alarms', subtitle: 'Scheduled · Persistent · Alarm Overlay',
    description: 'Set reminders for any future time. When the time arrives, Lumina fires an alarm overlay on-screen and calls your name aloud. Reminders survive restarts and are stored in the database.',
    usage: ['"Remind me to take my medicine at 8 PM."', '"Set an alarm for tomorrow 7:30 AM."', '"Remind me in 30 minutes to check the oven."'], badge: 'Persistent' },
  { id: 'spotify', category: 'Actions', icon: Music, color: 'green', title: 'Spotify Control', subtitle: 'Play · Pause · Skip · Queue · Volume',
    description: 'Full Spotify playback control via voice. Search for songs, artists, or playlists, play them, skip tracks, adjust volume, and queue music — hands-free.',
    usage: ['"Play Blinding Lights on Spotify."', '"Skip this song."', '"Volume up."', '"Queue some lofi hip-hop."'], badge: 'Music' },
  { id: 'youtube', category: 'Actions', icon: Video, color: 'red', title: 'YouTube Control', subtitle: 'Search · Play · Pause · Skip · Queue',
    description: 'Search for and play YouTube videos via voice. Controls playback in the embedded browser so you can pause, skip, and navigate videos without touching the keyboard.',
    usage: ['"Play MrBeast\'s latest video."', '"Search for how to make pasta on YouTube."', '"Pause the video."'], badge: 'Browser' },

  // ── System ──
  { id: 'computer_control', category: 'System', icon: Cpu, color: 'orange', title: 'Computer Control', subtitle: 'Mouse · Keyboard · Clipboard · Hotkeys',
    description: 'Low-level PC control: move the mouse, simulate keyboard input, copy/paste clipboard content, press hotkeys, and interact with any window. Useful for automating GUI tasks that have no API.',
    usage: ['"Press Ctrl+S to save."', '"Click the submit button."', '"Copy the text in the active window."'], badge: 'Automation' },
  { id: 'computer_settings', category: 'System', icon: Settings, color: 'slate', title: 'Computer Settings', subtitle: 'Volume · Brightness · Wi-Fi · Power',
    description: 'Adjust Windows system settings via voice. Control speaker volume, screen brightness, toggle Wi-Fi/Bluetooth, switch power plans, and lock/sleep/shutdown the machine.',
    usage: ['"Set volume to 50%."', '"Reduce brightness by 20%."', '"Turn off Wi-Fi."', '"Lock the computer."'], badge: 'Windows' },
  { id: 'open_app', category: 'System', icon: Layers, color: 'indigo', title: 'Open Applications', subtitle: 'Launch · Focus · Close any app',
    description: 'Open, focus, or close any installed application by name. Lumina maps natural names like "calculator" or "notepad" to the correct executable and launches it instantly.',
    usage: ['"Open Notepad."', '"Launch VS Code."', '"Close Spotify."'], badge: 'Launcher' },
  { id: 'screen_process', category: 'System', icon: Monitor, color: 'cyan', title: 'Screen Processor', subtitle: 'Screenshot · OCR · Visual Q&A',
    description: 'Lumina can take a screenshot, run OCR to extract text, and answer questions about what is on your screen. Useful for reading error messages, UI labels, or anything displayed visually.',
    usage: ['"What does the error message on my screen say?"', '"Read the text in this dialog box."', '"Take a screenshot and describe what you see."'], badge: 'Vision' },
  { id: 'desktop_control', category: 'System', icon: Monitor, color: 'teal', title: 'Desktop Control', subtitle: 'Window management · Taskbar · Workspace',
    description: 'Manage your Windows desktop: minimise, maximise, tile, or close windows; switch virtual desktops; arrange workspaces; and interact with the taskbar.',
    usage: ['"Minimise all windows."', '"Maximise Chrome."', '"Switch to virtual desktop 2."'], badge: 'Windows' },
  { id: 'cmd', category: 'System', icon: Terminal, color: 'lime', title: 'Command Line Control', subtitle: 'CMD · PowerShell · Shell scripts',
    description: 'Execute shell commands, PowerShell scripts, and batch files. Lumina can run arbitrary commands, capture output, and relay results back to you in plain language.',
    usage: ['"Run ipconfig and tell me my IP address."', '"Execute the deploy.bat script."', '"Check disk usage with PowerShell."'], badge: 'Shell' },

  // ── Remote ──
  { id: 'phone_dashboard', category: 'Remote', icon: Smartphone, color: 'violet', title: 'Remote Phone Dashboard', subtitle: 'LAN · AES-256 · QR Code Pairing · Phone Mic',
    description: 'Access Lumina from your phone via your local network. A secure web interface lets you type commands, view the conversation log, stream your phone microphone as input, and upload files directly from your phone to your PC.',
    usage: ['Open Settings → Remote Control and scan the QR code with your phone.', 'Enter the 6-digit PIN in the mobile browser.', 'Type commands or tap the mic button to send audio from your phone.', 'Drag and drop files onto the mobile UI to share them with your PC.'], badge: 'LAN' },
];

// Colour map — feature accent palettes (unchanged from original).
export const FEATURE_COLOR_MAP = {
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
};

// Local filter (search + category). Pure — no state.
export function filterFeatures(features, category, query) {
  const q = (query || '').toLowerCase();
  return features.filter((f) => {
    const matchesCat = category === 'All' || f.category === category;
    const matchesSearch = !q ||
      f.title.toLowerCase().includes(q) ||
      f.subtitle.toLowerCase().includes(q) ||
      f.description.toLowerCase().includes(q) ||
      f.category.toLowerCase().includes(q);
    return matchesCat && matchesSearch;
  });
}
