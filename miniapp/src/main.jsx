import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@fontsource-variable/montserrat'
import './index.css'
import App from './App.jsx'
import { TranslationProvider } from './i18n/TranslationContext'
import ErrorBoundary from './ErrorBoundary'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ErrorBoundary>
      <TranslationProvider>
        <App />
      </TranslationProvider>
    </ErrorBoundary>
  </StrictMode>,
)
