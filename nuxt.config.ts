export default defineNuxtConfig({
  devtools: { enabled: true },
  modules: ['@nuxtjs/supabase'],

  nitro: {
    preset: 'cloudflare-pages',
  },

  supabase: {
    // Placeholder values allow dev mode without a real Supabase project.
    // Set SUPABASE_URL + SUPABASE_KEY in .env to enable live data.
    url: process.env.SUPABASE_URL ?? 'https://placeholder.supabase.co',
    key: process.env.SUPABASE_KEY ?? 'placeholder-key',
    redirectOptions: {
      login: '/',
      callback: '/',
      // No auth required — public dashboard
      exclude: ['/*'],
    },
  },

  runtimeConfig: {
    public: {
      // Guards all Supabase calls in composables; false = demo/stub mode
      supabaseEnabled: !!(process.env.SUPABASE_URL && process.env.SUPABASE_KEY),
    },
  },

  css: ['~/assets/css/main.css'],

  app: {
    head: {
      title: 'CS26 — Live Telemetry',
      meta: [
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        { charset: 'utf-8' },
      ],
      link: [
        { rel: 'icon', href: '/favicon.svg', type: 'image/svg+xml' },
        { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
        { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' },
        {
          rel: 'stylesheet',
          href: 'https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@300;400;500;700&display=swap',
        },
      ],
    },
  },

  compatibilityDate: '2025-05-08',
})
