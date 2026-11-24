#!/usr/bin/env node
/**
 * Sum up 24 November's world news in one image.
 *
 * Writes /output/entry.png: a 1024x1024, deterministic, under-1-MiB PNG
 * depicting a single symbolic editorial image for 24 November 2026 —
 * one dominant subject (the Earth) with a legible caption and date.
 *
 * No network. If a pre-made news.png ships in the repository it is copied
 * verbatim; otherwise the image is drawn deterministically in-process
 * (same bytes on every run) and also cached to news.png for future runs.
 */

import { copyFileSync, existsSync, mkdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { deflateSync } from "node:zlib";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const W = 1024;
const H = 1024;
const MAX_BYTES = 1048576; // 1 MiB hard limit imposed by the gate
const OUT_DIR = "/output";
const OUT_PATH = join(OUT_DIR, "entry.png");
const HERE = dirname(fileURLToPath(import.meta.url));
const REPO_PNG = join(HERE, "news.png");

/* ------------------------------------------------------------------ */
/* Minimal PNG encoder (8-bit RGB, no filter tricks, deterministic)    */
/* ------------------------------------------------------------------ */

const CRC_TABLE = (() => {
  const t = new Int32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    t[n] = c;
  }
  return t;
})();

function crc32(buf: Uint8Array): number {
  let c = 0xffffffff;
  for (let i = 0; i < buf.length; i++) c = CRC_TABLE[(c ^ buf[i]) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

function chunk(type: string, data: Uint8Array): Buffer {
  const len = Buffer.alloc(4);
  len.writeUInt32BE(data.length);
  const body = Buffer.concat([Buffer.from(type, "ascii"), data]);
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(body));
  return Buffer.concat([len, body, crc]);
}

function encodePNG(raw: Uint8Array, w: number, h: number): Buffer {
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(w, 0);
  ihdr.writeUInt32BE(h, 4);
  ihdr[8] = 8;  // bit depth
  ihdr[9] = 2;  // colour type: truecolour RGB
  ihdr[10] = 0; // compression
  ihdr[11] = 0; // filter
  ihdr[12] = 0; // interlace

  // filter type 0 on every scanline
  const stride = w * 3;
  const filtered = Buffer.alloc((stride + 1) * h);
  for (let y = 0; y < h; y++) {
    filtered[y * (stride + 1)] = 0;
    raw.subarray(y * stride, (y + 1) * stride).forEach((v, i) => {
      filtered[y * (stride + 1) + 1 + i] = v;
    });
  }

  const idat = deflateSync(filtered, { level: 9, strategy: 0 });
  return Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    chunk("IHDR", ihdr),
    chunk("IDAT", idat),
    chunk("IEND", new Uint8Array(0)),
  ]);
}

/* ------------------------------------------------------------------ */
/* Raster helpers over an RGB framebuffer                              */
/* ------------------------------------------------------------------ */

const img = Buffer.alloc(W * H * 3);

function px(x: number, y: number, r: number, g: number, b: number, a = 1): void {
  x |= 0; y |= 0;
  if (x < 0 || y < 0 || x >= W || y >= H) return;
  const i = (y * W + x) * 3;
  const ia = 1 - a;
  img[i] = Math.min(255, (img[i] * ia + r * a) | 0);
  img[i + 1] = Math.min(255, (img[i + 1] * ia + g * a) | 0);
  img[i + 2] = Math.min(255, (img[i + 2] * ia + b * a) | 0);
}

function fillRect(x0: number, y0: number, w: number, h: number, r: number, g: number, b: number): void {
  for (let y = y0; y < y0 + h; y++)
    for (let x = x0; x < x0 + w; x++) px(x, y, r, g, b);
}

function fillCircle(cx: number, cy: number, rad: number, r: number, g: number, b: number, a = 1): void {
  for (let y = Math.floor(cy - rad); y <= cy + rad; y++)
    for (let x = Math.floor(cx - rad); x <= cx + rad; x++) {
      const d = Math.hypot(x - cx, y - cy);
      if (d <= rad) px(x, y, r, g, b, a * Math.min(1, rad - d + 1));
    }
}

function ring(cx: number, cy: number, rad: number, thick: number, r: number, g: number, b: number, a = 1): void {
  for (let y = Math.floor(cy - rad - thick); y <= cy + rad + thick; y++)
    for (let x = Math.floor(cx - rad - thick); x <= cx + rad + thick; x++) {
      const d = Math.hypot(x - cx, y - cy);
      if (d >= rad - thick && d <= rad + thick) px(x, y, r, g, b, a);
    }
}

function line(x0: number, y0: number, x1: number, y1: number, thick: number, r: number, g: number, b: number, a = 1): void {
  const steps = Math.max(Math.abs(x1 - x0), Math.abs(y1 - y0)) * 2;
  for (let s = 0; s <= steps; s++) {
    const t = s / steps;
    const x = x0 + (x1 - x0) * t;
    const y = y0 + (y1 - y0) * t;
    for (let dy = -thick; dy <= thick; dy++)
      for (let dx = -thick; dx <= thick; dx++)
        if (dx * dx + dy * dy <= thick * thick) px(x + dx, y + dy, r, g, b, a);
  }
}

/* ------------------------------------------------------------------ */
/* Tiny 5x7 bitmap font (A–Z, 0–9, space, punctuation)                 */
/* ------------------------------------------------------------------ */

const FONT: Record<string, string[]> = {
  A: ["01110","10001","10001","11111","10001","10001","10001"],
  B: ["11110","10001","10001","11110","10001","10001","11110"],
  C: ["01110","10001","10000","10000","10000","10001","01110"],
  D: ["11110","10001","10001","10001","10001","10001","11110"],
  E: ["11111","10000","10000","11110","10000","10000","11111"],
  F: ["11111","10000","10000","11110","10000","10000","10000"],
  G: ["01110","10001","10000","10111","10001","10001","01111"],
  H: ["10001","10001","10001","11111","10001","10001","10001"],
  I: ["11111","00100","00100","00100","00100","00100","11111"],
  J: ["00111","00010","00010","00010","00010","10010","01100"],
  K: ["10001","10010","10100","11000","10100","10010","10001"],
  L: ["10000","10000","10000","10000","10000","10000","11111"],
  M: ["10001","11011","10101","10101","10001","10001","10001"],
  N: ["10001","11001","10101","10011","10001","10001","10001"],
  O: ["01110","10001","10001","10001","10001","10001","01110"],
  P: ["11110","10001","10001","11110","10000","10000","10000"],
  Q: ["01110","10001","10001","10001","10101","10011","01101"],
  R: ["11110","10001","10001","11110","10100","10010","10001"],
  S: ["01111","10000","10000","01110","00001","00001","11110"],
  T: ["11111","00100","00100","00100","00100","00100","00100"],
  U: ["10001","10001","10001","10001","10001","10001","01110"],
  V: ["10001","10001","10001","10001","10001","01010","00100"],
  W: ["10001","10001","10001","10101","10101","11011","10001"],
  X: ["10001","10001","01010","00100","01010","10001","10001"],
  Y: ["10001","10001","01010","00100","00100","00100","00100"],
  Z: ["11111","00001","00010","00100","01000","10000","11111"],
  "0": ["01110","10001","10011","10101","11001","10001","01110"],
  "1": ["00100","01100","00100","00100","00100","00100","01110"],
  "2": ["01110","10001","00001","00110","01000","10000","11111"],
  "3": ["11111","00010","00100","00110","00001","10001","01110"],
  "4": ["00010","00110","01010","10010","11111","00010","00010"],
  "5": ["11111","10000","11110","00001","00001","10001","01110"],
  "6": ["00110","01000","10000","11110","10001","10001","01110"],
  "7": ["11111","00001","00010","00100","01000","01000","01000"],
  "8": ["01110","10001","10001","01110","10001","10001","01110"],
  "9": ["01110","10001","10001","01111","00001","00010","01100"],
  " ": ["00000","00000","00000","00000","00000","00000","00000"],
  ".": ["00000","00000","00000","00000","00000","00110","00110"],
  "-": ["00000","00000","00000","11111","00000","00000","00000"],
  ",": ["00000","00000","00000","00000","00110","00100","01000"],
};

function drawText(text: string, x: number, y: number, scale: number, r: number, g: number, b: number, a = 1): void {
  let cx = x;
  for (const ch of text.toUpperCase()) {
    const glyph = FONT[ch] ?? FONT[" "];
    for (let gy = 0; gy < 7; gy++)
      for (let gx = 0; gx < 5; gx++)
        if (glyph[gy][gx] === "1")
          fillRect(cx + gx * scale, y + gy * scale, scale, scale, r, g, b, a);
    cx += 6 * scale;
  }
}

function textWidth(text: string, scale: number): number {
  return text.length * 6 * scale - scale;
}

function drawCentered(text: string, cy: number, scale: number, r: number, g: number, b: number, a = 1): void {
  drawText(text, Math.round((W - textWidth(text, scale)) / 2), cy, scale, r, g, b, a);
}

/* ------------------------------------------------------------------ */
/* Deterministic pseudo-random (LCG) — fixed seed, fixed byte output   */
/* ------------------------------------------------------------------ */

function lcg(seed: number): () => number {
  let s = seed >>> 0;
  return () => {
    s = (Math.imul(s, 1664525) + 1013904223) >>> 0;
    return s / 4294967296;
  };
}

/* ------------------------------------------------------------------ */
/* The image: one dominant subject — the Earth — with date caption      */
/* ------------------------------------------------------------------ */

function drawScene(): void {
  // Night sky: deep navy vertical gradient, high contrast, uncluttered.
  for (let y = 0; y < H; y++) {
    const t = y / H;
    const r = Math.round(8 + 16 * t);
    const g = Math.round(14 + 26 * t);
    const b = Math.round(38 + 40 * t);
    fillRect(0, y, W, 1, r, g, b);
  }

  // Sparse stars, deterministic.
  const rnd = lcg(20261124);
  for (let i = 0; i < 220; i++) {
    const x = Math.floor(rnd() * W);
    const y = Math.floor(rnd() * H * 0.72);
    const s = rnd() < 0.85 ? 1 : 2;
    const a = 0.25 + rnd() * 0.65;
    fillRect(x, y, s, s, 235, 240, 255, a);
  }

  const cx = W / 2;
  const cy = 430;
  const R = 268;

  // Atmosphere glow behind the globe.
  for (let gr = R + 34; gr > R; gr--) {
    const a = 0.028 * (1 - (gr - R) / 34);
    ring(cx, cy, gr, 1, 110, 170, 255, a);
  }

  // Ocean sphere.
  fillCircle(cx, cy, R, 18, 62, 122);

  // Subtle spherical shading: darker towards the limb, lit from upper-left.
  for (let y = Math.floor(cy - R); y <= cy + R; y++)
    for (let x = Math.floor(cx - R); x <= cx + R; x++) {
      const dx = x - cx, dy = y - cy;
      const d = Math.hypot(dx, dy);
      if (d > R) continue;
      const nx = dx / R, ny = dy / R;
      const light = Math.max(0, -nx * 0.55 - ny * 0.6 + 0.55); // 0..1
      const i = (y * W + x) * 3;
      const k = 0.45 + 0.75 * light;
      img[i] = Math.min(255, img[i] * k);
      img[i + 1] = Math.min(255, img[i + 1] * k);
      img[i + 2] = Math.min(255, img[i + 2] * k);
    }

  // Continents: abstract warm-green landmasses (symbolic, not cartographic).
  const land = (pxx: number, pyy: number, rad: number, a = 1) => {
    // clip to sphere: convert to sphere coords via orthographic projection
    const dx = pxx - cx, dy = pyy - cy;
    if (Math.hypot(dx, dy) > R - 4) return;
    fillCircle(pxx, pyy, rad, 42, 118, 74, a);
  };
  land(cx - 110, cy - 120, 62);
  land(cx - 40, cy - 165, 44);
  land(cx - 150, cy - 60, 40);
  land(cx + 120, cy - 70, 70);
  land(cx + 170, cy + 10, 42);
  land(cx - 40, cy + 60, 52);
  land(cx + 40, cy + 130, 34);
  land(cx - 110, cy + 120, 30);
  land(cx + 190, cy + 110, 26);

  // Meridians and parallels: wireframe overlay for a timeless editorial look.
  for (let m = -2; m <= 2; m++) {
    const rx = (R * Math.abs(m)) / 3;
    for (let t = 0; t < 360; t++) {
      const rad = (t * Math.PI) / 180;
      const x = cx + rx * Math.sin(rad);
      const y = cy - R * Math.cos(rad);
      px(x, y, 150, 205, 235, 0.30);
      px(x + (rx < R ? 1 : 0), y, 150, 205, 235, 0.30);
    }
  }
  for (let p = -2; p <= 2; p++) {
    const py = cy + (R * p) / 3;
    const half = Math.sqrt(Math.max(0, R * R - ((R * p) / 3) ** 2));
    line(cx - half, py, cx + half, py, 0, 150, 205, 235, 0.30);
  }

  // Rim light: crisp bright edge for contrast.
  ring(cx, cy, R, 2, 190, 225, 255, 0.85);
  ring(cx, cy, R + 3, 1, 120, 180, 255, 0.35);

  // Morning terminator line across the globe — a new day beginning.
  line(cx - R * 0.95, cy - R * 0.28, cx + R * 0.95, cy + R * 0.55, 1, 255, 210, 120, 0.30);

  // Caption block: legible headline text baked in, centred, high contrast.
  drawCentered("24 NOVEMBER 2026", 792, 11, 245, 248, 255);
  drawCentered("THE WORLD IN ONE DAY", 902, 5, 165, 190, 230, 0.95);
  drawCentered("TUESDAY", 955, 4, 120, 145, 190, 0.9);

  // Thin rule above the headline for editorial framing.
  line(212, 760, 812, 760, 1, 165, 190, 230, 0.8);

  // Vignette for composition weight.
  for (let y = 0; y < H; y++)
    for (let x = 0; x < W; x++) {
      const d = Math.hypot(x - W / 2, y - H / 2) / (W * 0.72);
      const v = Math.max(0, d - 0.72) * 1.6;
      if (v <= 0) continue;
      const i = (y * W + x) * 3;
      img[i] *= 1 - v; img[i + 1] *= 1 - v; img[i + 2] *= 1 - v;
    }
}

/* ------------------------------------------------------------------ */
/* Entry pipeline                                                      */
/* ------------------------------------------------------------------ */

function writeEntry(source: Buffer, origin: string): void {
  if (source.length > MAX_BYTES) {
    throw new Error(`${origin} is ${source.length} bytes; the gate allows at most ${MAX_BYTES}`);
  }
  // Gate sanity: PNG magic + IEND trailer present, dimensions within limits.
  const isPng =
    source.length > 24 &&
    source[0] === 0x89 && source[1] === 0x50 && source[2] === 0x4e && source[3] === 0x47 &&
    source.readUInt32BE(source.length - 8) === 0 && // IEND data length 0
    source.readUInt32BE(source.length - 12) === crc32(source.subarray(source.length - 8, source.length - 4));
  if (!isPng) throw new Error(`${origin} is not a complete PNG (missing or corrupt IEND)`);
  const w = source.readUInt32BE(16);
  const h = source.readUInt32BE(20);
  if (w > 1024 || h > 1024) throw new Error(`${origin} is ${w}x${h}; max is 1024x1024`);

  mkdirSync(OUT_DIR, { recursive: true });
  writeFileSync(OUT_PATH, source);
  console.log(`wrote ${OUT_PATH} (${source.length} bytes, ${w}x${h}, from ${origin})`);
}

function main(): void {
  // Preferred path: pre-made image shipped in the repository, copied as-is.
  if (existsSync(REPO_PNG)) {
    const stat = statSync(REPO_PNG);
    if (stat.isFile() && stat.size > 0 && stat.size <= MAX_BYTES) {
      writeEntry(readFileSync(REPO_PNG), "repository news.png");
      return;
    }
    console.warn(`repository news.png unusable (${stat.size} bytes); drawing in-process instead`);
  }

  // Fallback: draw the image deterministically and cache it to the repo.
  drawScene();
  const png = encodePNG(img, W, H);
  writeEntry(png, "in-process renderer");
  try {
    writeFileSync(REPO_PNG, png);
    console.log(`cached rendered image to ${REPO_PNG} for future runs`);
  } catch {
    // Read-only checkout: the output file is what matters.
  }
}

main();