import fs from 'node:fs';
import { createRequire } from 'node:module';
import path from 'node:path';

const require = createRequire(import.meta.url);
const pwPath = fs.existsSync('/tmp/pw-runner/node_modules/playwright')
  ? '/tmp/pw-runner/node_modules/playwright'
  : 'playwright';
const { chromium } = require(pwPath);

const targetUrl = process.env.PREVIEW_TARGET_URL || 'http://127.0.0.1:8765';
const outDir = process.env.PREVIEW_OUT_DIR || 'docs/preview';
const badge = process.env.PREVIEW_BADGE || 'LIVE PREVIEW';
const title = process.env.PREVIEW_TITLE || 'Project';
const desc = process.env.PREVIEW_DESC || '';
const tags = (process.env.PREVIEW_TAGS || '')
  .split(',')
  .map((t) => t.trim())
  .filter(Boolean);
const repoLabel = process.env.PREVIEW_REPO || '';
const liveUrl = process.env.PREVIEW_LIVE_URL || '';
const theme = process.env.PREVIEW_THEME || 'blue';

const THEMES = {
  blue: {
    bg: 'linear-gradient(135deg, #f4f7fb 0%, #e8eef7 100%)',
    text: '#0f172a',
    muted: '#475569',
    badgeBg: '#1d4ed8',
    badgeDot: '#60a5fa',
    badgeText: '#ffffff',
    tagBg: '#e2e8f0',
    tagText: '#334155',
    divider: 'rgba(15, 23, 42, 0.12)',
    link: '#1d4ed8',
    browserBg: '#f1f5f9',
    browserBorder: 'rgba(15, 23, 42, 0.12)',
    urlText: '#334155',
  },
  green: {
    bg: 'linear-gradient(135deg, #f3faf5 0%, #e3f2e8 100%)',
    text: '#0f172a',
    muted: '#475569',
    badgeBg: '#166534',
    badgeDot: '#4ade80',
    badgeText: '#ffffff',
    tagBg: '#e2ece5',
    tagText: '#334155',
    divider: 'rgba(15, 23, 42, 0.12)',
    link: '#166534',
    browserBg: '#f1f5f9',
    browserBorder: 'rgba(15, 23, 42, 0.12)',
    urlText: '#334155',
  },
  dark: {
    bg: 'linear-gradient(135deg, #0b1628 0%, #10213a 100%)',
    text: '#f8fafc',
    muted: '#cbd5e1',
    badgeBg: '#0369a1',
    badgeDot: '#38bdf8',
    badgeText: '#ffffff',
    tagBg: 'rgba(255, 255, 255, 0.10)',
    tagText: '#e2e8f0',
    divider: 'rgba(255, 255, 255, 0.14)',
    link: '#38bdf8',
    browserBg: '#1e293b',
    browserBorder: 'rgba(255, 255, 255, 0.16)',
    urlText: '#cbd5e1',
  },
};

const palette = THEMES[theme] || THEMES.blue;

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

async function captureViewport(browser, { width, height, isMobile, hasTouch }, destPath) {
  const context = await browser.newContext({
    viewport: { width, height },
    deviceScaleFactor: 1,
    isMobile: Boolean(isMobile),
    hasTouch: Boolean(hasTouch),
  });
  const page = await context.newPage();
  try {
    await page.goto(targetUrl, { waitUntil: 'networkidle', timeout: 25000 });
  } catch {
    await page.goto(targetUrl, { waitUntil: 'load', timeout: 25000 });
  }
  await page.waitForTimeout(1500);
  await page.screenshot({ path: destPath, fullPage: false });
  await context.close();
}

async function main() {
  fs.mkdirSync(outDir, { recursive: true });
  const desktopPath = path.join(outDir, 'desktop.png');
  const mobilePath = path.join(outDir, 'mobile.png');
  const socialPath = path.join(outDir, 'social-preview.png');

  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });

  try {
    await captureViewport(browser, { width: 1440, height: 900 }, desktopPath);
    await captureViewport(
      browser,
      { width: 390, height: 844, isMobile: true, hasTouch: true },
      mobilePath,
    );

    const desktopB64 = fs.readFileSync(desktopPath).toString('base64');
    const mobileB64 = fs.readFileSync(mobilePath).toString('base64');

    const html = `<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    width: 1280px;
    height: 640px;
    overflow: hidden;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, Helvetica, Arial, sans-serif;
    background: ${palette.bg};
    color: ${palette.text};
    display: flex;
    align-items: stretch;
    padding: 46px 52px;
    gap: 44px;
  }
  .left {
    width: 470px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    flex-shrink: 0;
  }
  .badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: ${palette.badgeBg};
    color: ${palette.badgeText};
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.08em;
    padding: 7px 14px;
    border-radius: 999px;
    width: fit-content;
    margin-bottom: 22px;
  }
  .badge-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: ${palette.badgeDot};
  }
  h1 {
    font-size: 46px;
    line-height: 1.08;
    font-weight: 800;
    letter-spacing: -0.02em;
    margin-bottom: 18px;
  }
  .desc {
    font-size: 18px;
    line-height: 1.5;
    color: ${palette.muted};
    margin-bottom: 24px;
  }
  .tags {
    display: flex;
    flex-wrap: wrap;
    gap: 9px;
  }
  .tag {
    background: ${palette.tagBg};
    color: ${palette.tagText};
    font-size: 13px;
    font-weight: 600;
    padding: 7px 13px;
    border-radius: 8px;
  }
  .footer {
    border-top: 1px solid ${palette.divider};
    padding-top: 18px;
    font-size: 14px;
    line-height: 1.55;
  }
  .footer-repo {
    font-weight: 700;
  }
  .footer-url {
    color: ${palette.link};
    font-weight: 600;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 13px;
  }
  .right {
    flex: 1;
    position: relative;
    display: flex;
    align-items: center;
  }
  .desktop-frame {
    width: 600px;
    border-radius: 14px;
    overflow: hidden;
    background: ${palette.browserBg};
    border: 1px solid ${palette.browserBorder};
    box-shadow: 0 28px 60px rgba(2, 6, 23, 0.22);
    transform: translateY(-20px);
  }
  .browser-bar {
    height: 32px;
    display: flex;
    align-items: center;
    padding: 0 14px;
    gap: 7px;
    border-bottom: 1px solid ${palette.browserBorder};
  }
  .dot { width: 10px; height: 10px; border-radius: 50%; }
  .dot.r { background: #ef4444; }
  .dot.y { background: #f59e0b; }
  .dot.g { background: #22c55e; }
  .url-bar {
    margin-left: 10px;
    font-size: 11px;
    color: ${palette.urlText};
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .desktop-img {
    display: block;
    width: 100%;
    height: 375px;
    object-fit: cover;
    object-position: top center;
  }
  .mobile-frame {
    position: absolute;
    right: -6px;
    bottom: -10px;
    width: 176px;
    height: 368px;
    border-radius: 26px;
    padding: 8px;
    background: #0f172a;
    box-shadow: 0 24px 50px rgba(2, 6, 23, 0.38);
    border: 2px solid rgba(255, 255, 255, 0.14);
  }
  .mobile-img {
    display: block;
    width: 100%;
    height: 100%;
    border-radius: 19px;
    object-fit: cover;
    object-position: top center;
  }
</style>
</head>
<body>
  <div class="left">
    <div>
      <div class="badge"><span class="badge-dot"></span>${escapeHtml(badge)}</div>
      <h1>${escapeHtml(title)}</h1>
      <p class="desc">${escapeHtml(desc)}</p>
      <div class="tags">
        ${tags.map((t) => `<span class="tag">${escapeHtml(t)}</span>`).join('')}
      </div>
    </div>
    <div class="footer">
      <div class="footer-repo">noobucodonosor · ${escapeHtml(repoLabel)}</div>
      <div class="footer-url">${escapeHtml(liveUrl)}</div>
    </div>
  </div>
  <div class="right">
    <div class="desktop-frame">
      <div class="browser-bar">
        <span class="dot r"></span><span class="dot y"></span><span class="dot g"></span>
        <span class="url-bar">${escapeHtml(liveUrl)}</span>
      </div>
      <img class="desktop-img" src="data:image/png;base64,${desktopB64}" />
    </div>
    <div class="mobile-frame">
      <img class="mobile-img" src="data:image/png;base64,${mobileB64}" />
    </div>
  </div>
</body>
</html>`;

    const cardContext = await browser.newContext({
      viewport: { width: 1280, height: 640 },
      deviceScaleFactor: 1,
    });
    const cardPage = await cardContext.newPage();
    await cardPage.setContent(html, { waitUntil: 'load' });
    await cardPage.waitForTimeout(300);
    await cardPage.screenshot({ path: socialPath });
    await cardContext.close();
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
