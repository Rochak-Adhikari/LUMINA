import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './app/App';
// Reuse the existing global stylesheet (fonts, glass utils, tailwind layers).
import '../src/index.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
