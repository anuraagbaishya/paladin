import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
    plugins: [react()],
    build: {
        outDir: path.resolve(__dirname, '../static/js'),
        emptyOutDir: true,
        cssCodeSplit: true,
        rollupOptions: {
            input: path.resolve(__dirname, 'index.html'),
            output: {
                entryFileNames: 'bundle.js',
                assetFileNames: 'assets/[name].[ext]',
            },
        },
        manifest: false,
    },
    base: './',
});
