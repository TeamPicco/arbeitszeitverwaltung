import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'
import './index.css'
import App from './App.tsx'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 5 * 60_000,
      gcTime: 10 * 60_000,
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>
        <App />
        <Toaster
          position="bottom-right"
          toastOptions={{
            duration: 4000,
            style: {
              background: '#fff',
              color: '#2D2D2D',
              border: '1px solid #E5E5E5',
              borderLeft: '4px solid #FF6B00',
              borderRadius: '10px',
              fontSize: '14px',
              fontFamily: 'Barlow, sans-serif',
              boxShadow: '0 4px 20px rgba(0,0,0,0.10)',
            },
            success: {
              iconTheme: { primary: '#16A34A', secondary: '#fff' },
              style: { borderLeftColor: '#16A34A' },
            },
            error: {
              iconTheme: { primary: '#DC2626', secondary: '#fff' },
              style: { borderLeftColor: '#DC2626' },
            },
          }}
        />
      </QueryClientProvider>
    </BrowserRouter>
  </StrictMode>
)
