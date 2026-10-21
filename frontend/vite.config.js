// Configuração do Vite (a ferramenta que roda o React no seu computador).
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // host: true deixa o iPhone (no mesmo Wi-Fi) abrir o site pelo IP do Mac.
    host: true,
    // Tudo que começa com /api é repassado para o servidor Python (FastAPI).
    // Assim o React não precisa saber em que porta o Python está.
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
