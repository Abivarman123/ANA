import { NextResponse } from 'next/server';
import fs from 'fs/promises';
import path from 'path';

// Helper to get config path
// Assuming the UI is running from the 'ui' directory or root, we need to find the config.json in the project root.
// If process.cwd() is .../ANA/ui, then config is at ../config.json
// If process.cwd() is .../ANA, then config is at ./config.json
const getConfigPath = () => {
  const cwd = process.cwd();
  if (cwd.endsWith('ui')) {
    return path.join(cwd, '..', 'config.json');
  }
  return path.join(cwd, 'config.json');
};

export async function GET() {
  try {
    const configPath = getConfigPath();
    const fileContent = await fs.readFile(configPath, 'utf-8');
    const config = JSON.parse(fileContent);
    return NextResponse.json(config);
  } catch (error) {
    console.error('Error reading config:', error);
    return NextResponse.json({ error: 'Failed to read config' }, { status: 500 });
  }
}

export async function POST(req: Request) {
  try {
    const configPath = getConfigPath();
    const newConfig = await req.json();

    // Optional: Validate config here

    await fs.writeFile(configPath, JSON.stringify(newConfig, null, 2), 'utf-8');
    return NextResponse.json({ success: true, config: newConfig });
  } catch (error) {
    console.error('Error writing config:', error);
    return NextResponse.json({ error: 'Failed to save config' }, { status: 500 });
  }
}
