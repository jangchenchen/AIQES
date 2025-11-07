import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";
const srcPath = fileURLToPath(new URL("./src", import.meta.url));
export default defineConfig({
    plugins: [react()],
    resolve: {
        alias: {
            "@": resolve(srcPath),
        },
    },
});
