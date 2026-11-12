import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
// Served with the app, not from Google: no outside call, and the same type on every machine.
import '@fontsource-variable/inter/opsz.css'
import './index.css'
import './learning.css'
import './providers.css'
import App from './App.tsx'
// After App, so it loads after every component stylesheet and sets the final look.
import './apple.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
