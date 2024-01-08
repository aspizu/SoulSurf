import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { crx } from "@crxjs/vite-plugin";
import manifest from "./manifest.json";
import civetVitePlugin from "@danielx/civet/dist/vite.mjs";

export default defineConfig({
  plugins: [
    civetVitePlugin({ implicitExtension: false, typecheck: true }),
    react({
      babel: {
        plugins: [["module:@preact/signals-react-transform"]],
      },
    }),
    crx({ manifest }),
  ],
});
