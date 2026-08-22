import { defineConfig, type Plugin } from 'vite'
import vue from '@vitejs/plugin-vue'

function asyncCssPlugin(): Plugin {
  return {
    name: 'async-css',
    apply: 'build',
    transformIndexHtml: {
      order: 'post',
      handler(html) {
        return html.replace(
          /<link rel="stylesheet"(\s[^>]*)>/g,
          (match, attrs) => {
            const hrefMatch = attrs.match(/\shref="([^"]+)"/);
            if (!hrefMatch) return match;
            const href = hrefMatch[1];
            const co = attrs.includes('crossorigin') ? ' crossorigin' : '';
            return (
              `<link rel="preload" as="style"${co} href="${href}" onload="this.onload=null;this.rel='stylesheet'">` +
              `<noscript>${match}</noscript>`
            );
          }
        );
      },
    },
  };
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue(), asyncCssPlugin()],
  build: {
    cssCodeSplit: false,
    rollupOptions: {
      output: {
        manualChunks: (id) => {
          if (id.includes('node_modules/vue')) return 'vue';
        },
      },
    },
  },
})
