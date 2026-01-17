/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_AGUI_ENDPOINT?: string;
  readonly VITE_DEBUG_MODE?: string;
  readonly MODE: string;
  readonly DEV: boolean;
  readonly PROD: boolean;
  readonly SSR: boolean;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
