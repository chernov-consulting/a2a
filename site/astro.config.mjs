import { defineConfig } from 'astro/config';
import tailwind from '@astrojs/tailwind';

export default defineConfig({
  integrations: [tailwind()],
  site: 'https://a2a.chernov.io',
  output: 'static',
  build: {
    assets: '_assets',
  },
});
