'use client';

import { useEffect, useState } from 'react';
import { FloppyDisk, X } from '@phosphor-icons/react/dist/ssr';
import { Button } from '@/components/livekit/button';
import { cn } from '@/lib/utils';

interface Config {
  email: {
    smtp_server: string;
    smtp_port: number;
    user?: string;
    password?: string;
  };
  hardware: {
    serial_port: string;
    baud_rate: number;
    timeout: number;
  };
  model: {
    model_name: string;
    voice: string;
    temperature: number;
  };
  wake_word: {
    keyword_path: string;
    sensitivity: number;
    max_retries: number;
    retry_delay_seconds: number;
  };
  file_manager: {
    sandbox_path: string;
    max_file_size_mb: number;
  };
  user_name: string;
}

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const [config, setConfig] = useState<Config | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (isOpen) {
      fetchConfig();
    }
  }, [isOpen]);

  const fetchConfig = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/config');
      if (res.ok) {
        const data = await res.json();
        setConfig(data);
      }
    } catch (error) {
      console.error('Failed to load config', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!config) return;
    setSaving(true);
    try {
      const res = await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      });
      if (res.ok) {
        onClose();
      }
    } catch (error) {
      console.error('Failed to save config', error);
    } finally {
      setSaving(false);
    }
  };

  const handleChange = (section: keyof Config, key: string, value: any) => {
    if (!config) return;
    setConfig({
      ...config,
      [section]: {
        ...(config[section] as any),
        [key]: value,
      },
    });
  };

  const handleRootChange = (key: keyof Config, value: any) => {
    if (!config) return;
    setConfig({
      ...config,
      [key]: value,
    });
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-background text-foreground max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-lg border p-6 shadow-lg">
        <div className="mb-6 flex items-center justify-between">
          <h2 className="text-xl font-bold">Settings</h2>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="size-5" />
          </Button>
        </div>

        {loading ? (
          <div className="flex justify-center p-8">Loading...</div>
        ) : config ? (
          <div className="space-y-6">
            {/* User Settings */}
            <section className="space-y-4">
              <h3 className="border-b pb-2 text-lg font-semibold">User</h3>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">User Name</label>
                  <input
                    type="text"
                    value={config.user_name || ''}
                    onChange={(e) => handleRootChange('user_name', e.target.value)}
                    className="bg-muted focus:ring-primary w-full rounded-md border px-3 py-2 text-sm outline-none focus:ring-2"
                  />
                </div>
              </div>
            </section>

            {/* Model Settings */}
            <section className="space-y-4">
              <h3 className="border-b pb-2 text-lg font-semibold">Model</h3>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Model Name</label>
                  <input
                    type="text"
                    value={config.model.model_name}
                    onChange={(e) => handleChange('model', 'model_name', e.target.value)}
                    className="bg-muted focus:ring-primary w-full rounded-md border px-3 py-2 text-sm outline-none focus:ring-2"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Voice</label>
                  <input
                    type="text"
                    value={config.model.voice}
                    onChange={(e) => handleChange('model', 'voice', e.target.value)}
                    className="bg-muted focus:ring-primary w-full rounded-md border px-3 py-2 text-sm outline-none focus:ring-2"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Temperature</label>
                  <input
                    type="number"
                    step="0.1"
                    value={config.model.temperature}
                    onChange={(e) =>
                      handleChange('model', 'temperature', parseFloat(e.target.value))
                    }
                    className="bg-muted focus:ring-primary w-full rounded-md border px-3 py-2 text-sm outline-none focus:ring-2"
                  />
                </div>
              </div>
            </section>

            {/* Wake Word Settings */}
            <section className="space-y-4">
              <h3 className="border-b pb-2 text-lg font-semibold">Wake Word</h3>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Keyword Path</label>
                  <input
                    type="text"
                    value={config.wake_word.keyword_path}
                    onChange={(e) => handleChange('wake_word', 'keyword_path', e.target.value)}
                    className="bg-muted focus:ring-primary w-full rounded-md border px-3 py-2 text-sm outline-none focus:ring-2"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Sensitivity</label>
                  <input
                    type="number"
                    step="0.1"
                    value={config.wake_word.sensitivity}
                    onChange={(e) =>
                      handleChange('wake_word', 'sensitivity', parseFloat(e.target.value))
                    }
                    className="bg-muted focus:ring-primary w-full rounded-md border px-3 py-2 text-sm outline-none focus:ring-2"
                  />
                </div>
              </div>
            </section>

            {/* Hardware Settings */}
            <section className="space-y-4">
              <h3 className="border-b pb-2 text-lg font-semibold">Hardware</h3>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Serial Port</label>
                  <input
                    type="text"
                    value={config.hardware.serial_port}
                    onChange={(e) => handleChange('hardware', 'serial_port', e.target.value)}
                    className="bg-muted focus:ring-primary w-full rounded-md border px-3 py-2 text-sm outline-none focus:ring-2"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Baud Rate</label>
                  <input
                    type="number"
                    value={config.hardware.baud_rate}
                    onChange={(e) =>
                      handleChange('hardware', 'baud_rate', parseInt(e.target.value))
                    }
                    className="bg-muted focus:ring-primary w-full rounded-md border px-3 py-2 text-sm outline-none focus:ring-2"
                  />
                </div>
              </div>
            </section>

            <div className="flex justify-end gap-4 border-t pt-4">
              <Button variant="outline" onClick={onClose}>
                Cancel
              </Button>
              <Button onClick={handleSave} disabled={saving}>
                <FloppyDisk className="size-4" />
                {saving ? 'Saving...' : 'Save Changes'}
              </Button>
            </div>
          </div>
        ) : (
          <div className="text-center text-red-500">Failed to load configuration</div>
        )}
      </div>
    </div>
  );
}
