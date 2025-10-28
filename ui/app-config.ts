export interface AppConfig {
  pageTitle: string;
  pageDescription: string;
  companyName: string;

  supportsChatInput: boolean;
  supportsVideoInput: boolean;
  supportsScreenShare: boolean;
  isPreConnectBufferEnabled: boolean;

  logo: string;
  startButtonText: string;
  accent?: string;
  logoDark?: string;
  accentDark?: string;

  // for LiveKit Cloud Sandbox
  sandboxId?: string;
  agentName?: string;
}

export const APP_CONFIG_DEFAULTS: AppConfig = {
  companyName: 'ANA',
  pageTitle: 'ANA - Advanced Neural Assistant',
  pageDescription: 'A voice agent built with ANA',

  supportsChatInput: true,
  supportsVideoInput: true,
  supportsScreenShare: true,
  isPreConnectBufferEnabled: true,

  logo: '/ana.png',
  accent: '#002cf2',
  logoDark: '/ana.png',
  accentDark: '#1fd5f9',
  startButtonText: 'Start ANA',

  // for LiveKit Cloud Sandbox
  sandboxId: undefined,
  agentName: undefined,
};
