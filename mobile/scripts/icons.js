// Builds every Android launcher icon and splash image from the one logo:
// app/static/icons/icon.svg. Change the logo there, then run `npm run icons && npm run build`.
const fs = require("fs");
const path = require("path");
const sharp = require("sharp");

const SRC = path.join(__dirname, "../../app/static/icons/icon.svg");
const RES = path.join(__dirname, "../android/app/src/main/res");
const BG = "#f5f4ef";
const INK = "#1b1d1a";
const DOT = "#1e6b47";

const svg = fs.readFileSync(SRC, "utf8");
// The mark is the <g> group; the rounded <rect> is the background. Colours come from our
// own light-mode values so the dark-mode media query in the source is ignored.
const mark = svg.match(/<g[\s\S]*<\/g>/)[0];

function art({ bg, ink = INK, dot = DOT, pad = 0, shape = "none" }) {
  const v = 512 + 2 * pad;
  const back =
    shape === "rounded" ? `<rect x="${-pad}" y="${-pad}" width="${v}" height="${v}" rx="${(112 * v) / 512}" fill="${bg}"/>` :
    shape === "circle" ? `<circle cx="256" cy="256" r="${v / 2}" fill="${bg}"/>` :
    shape === "square" ? `<rect x="${-pad}" y="${-pad}" width="${v}" height="${v}" fill="${bg}"/>` : "";
  return Buffer.from(
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${-pad} ${-pad} ${v} ${v}">
      <style>.n{stroke:${ink}}.dot{fill:${dot}}</style>${back}${mark}</svg>`,
  );
}

const DENSITIES = { mdpi: 1, hdpi: 1.5, xhdpi: 2, xxhdpi: 3, xxxhdpi: 4 };

async function png(svgBuf, size, file) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  await sharp(svgBuf, { density: 300 }).resize(size, size).png().toFile(file);
}

async function main() {
  // Adaptive icon layers are 108dp with a 66dp safe zone. pad 165 puts the 512 art at about
  // 66dp of the 108dp canvas, so the mark survives every launcher mask.
  const foreground = art({ pad: 165 });
  const monochrome = art({ pad: 165, ink: "#000", dot: "#000" });

  for (const [d, k] of Object.entries(DENSITIES)) {
    const dir = path.join(RES, `mipmap-${d}`);
    await png(art({ bg: BG, shape: "rounded" }), 48 * k, path.join(dir, "ic_launcher.png"));
    await png(art({ bg: BG, shape: "circle", pad: 60 }), 48 * k, path.join(dir, "ic_launcher_round.png"));
    await png(foreground, 108 * k, path.join(dir, "ic_launcher_foreground.png"));
    await png(monochrome, 108 * k, path.join(dir, "ic_launcher_monochrome.png"));
  }

  // Pre-Android 12 splash: the mark centred on the app background.
  const splashes = fs.readdirSync(RES).filter((d) => d.startsWith("drawable")).map((d) => path.join(RES, d, "splash.png"));
  for (const file of splashes.filter(fs.existsSync)) {
    const { width, height } = await sharp(file).metadata();
    const side = Math.round(Math.min(width, height) * 0.3);
    const logo = await sharp(art({}), { density: 300 }).resize(side, side).png().toBuffer();
    await sharp({ create: { width, height, channels: 4, background: BG } })
      .composite([{ input: logo, gravity: "centre" }]).png().toFile(file + ".tmp");
    fs.renameSync(file + ".tmp", file);
  }

  fs.writeFileSync(path.join(RES, "values/ic_launcher_background.xml"),
    `<?xml version="1.0" encoding="utf-8"?>\n<resources>\n    <color name="ic_launcher_background">${BG.toUpperCase()}</color>\n</resources>\n`);
  const adaptive = `<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@color/ic_launcher_background"/>
    <foreground android:drawable="@mipmap/ic_launcher_foreground"/>
    <monochrome android:drawable="@mipmap/ic_launcher_monochrome"/>
</adaptive-icon>
`;
  for (const name of ["ic_launcher.xml", "ic_launcher_round.xml"]) {
    fs.writeFileSync(path.join(RES, "mipmap-anydpi-v26", name), adaptive);
  }
  console.log(`Icons and ${splashes.length} splash images written from ${path.relative(process.cwd(), SRC)}`);
}

main().catch((e) => { console.error(e); process.exit(1); });
