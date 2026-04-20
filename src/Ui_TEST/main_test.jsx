/**
 * Ui_TEST entry point.
 * 
 * To use this test UI instead of production:
 *   1. In src/main.jsx, change the import from './App' to './Ui_TEST/AppTest'
 *   2. Or run with: VITE_UI_TEST=1 npm run dev
 * 
 * This file is NOT auto-loaded. It serves as documentation for how to switch.
 */
import React from 'react';
import ReactDOM from 'react-dom/client';
import AppTest from './AppTest';
import '../index.css';

ReactDOM.createRoot(document.getElementById('root')).render(
    <React.StrictMode>
        <AppTest />
    </React.StrictMode>
);
