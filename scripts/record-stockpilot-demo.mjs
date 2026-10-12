// Re-records assets/stockpilot-demo.gif from a local StockPilot build.
// 1. In StockPilot: npm run build, then start offline with no API key:
//    DEMO_MODE=true PORT=3011 node server/dist/index.js
// 2. Here: mkdir -p frames && node scripts/record-stockpilot-demo.mjs
// 3. ffmpeg -f concat -safe 0 -i frames/list.txt -vf "fps=10,scale=800:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=128:stats_mode=diff[p];[b][p]paletteuse=dither=none:diff_mode=rectangle" -loop 0 assets/stockpilot-demo.gif
import { chromium } from 'playwright';
const url = process.argv[2] ?? 'http://localhost:3011/';
const b = await chromium.launch();
const ctx = await b.newContext({ viewport: { width: 1280, height: 800 } });
const p = await ctx.newPage();
// Lossless frames via CDP screencast; timestamps let ffmpeg keep real timing.
const fs = await import('node:fs');
const cdp = await ctx.newCDPSession(p);
const frames = [];
cdp.on('Page.screencastFrame', async (f) => {
  const n = String(frames.length).padStart(5, '0');
  fs.writeFileSync(`frames/${n}.png`, Buffer.from(f.data, 'base64'));
  frames.push({ file: `${n}.png`, t: f.metadata.timestamp });
  await cdp.send('Page.screencastFrameAck', { sessionId: f.sessionId }).catch(() => {});
});
const scrollTo = (y) => p.evaluate((y) => window.scrollTo({ top: y, behavior: 'smooth' }), y);
const yOf = (sel) => p.evaluate((s) => document.querySelector(s).getBoundingClientRect().top + window.scrollY, sel);
const ask = async (q) => {
  const input = p.locator('input[name="nl-query"]');
  await input.click();
  await input.fill('');
  await input.pressSequentially(q, { delay: 55 });
  await p.waitForTimeout(400);
  await p.click('button[type=submit]:has-text("Ask")');
};
await p.goto(url);
await p.waitForTimeout(1500);
await cdp.send('Page.startScreencast', { format: 'png', everyNthFrame: 1 });
await p.waitForTimeout(300);
await p.getByRole('button', { name: 'Dismiss this tip' }).click();
await scrollTo(150);
await p.waitForTimeout(900);
await ask('cheap profitable midcaps that fell this month');
await p.waitForTimeout(2600);
await scrollTo(await yOf('input[placeholder^="e.g. Infosys"]') + 300);
await p.waitForTimeout(3200);
await scrollTo(150);
await p.waitForTimeout(1200);
await ask('techonolgy stocks with low debt');
await p.waitForTimeout(2600);
await scrollTo(await yOf('input[placeholder^="e.g. Infosys"]') + 300);
await p.waitForTimeout(3200);
await scrollTo(0);
await p.waitForTimeout(1200);
await cdp.send('Page.stopScreencast');
await p.waitForTimeout(300);
const lines = frames.map((f, i) => `file '${f.file}'\nduration ${((frames[i + 1]?.t ?? f.t + 1) - f.t).toFixed(3)}`);
lines.push(`file '${frames.at(-1).file}'`);
fs.writeFileSync('frames/list.txt', lines.join('\n') + '\n');
await ctx.close();
await b.close();
