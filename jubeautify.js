let imageCount = 0;
let recentImages = [];
let settings = { extensionIsDisabled: false, appearChance: 1.0, flipChance: 0.25 };

function loadSettings(callback) {
  chrome.storage.local.get(
    { extensionIsDisabled: false, appearChance: 1.0, flipChance: 0.25 },
    (data) => { settings = data; if (callback) callback(); }
  );
}

function pickRandomImage(total) {
  if (total === 0) return 1;
  let candidates = Array.from({ length: total }, (_, i) => i + 1)
    .filter(n => !recentImages.includes(n));
  if (candidates.length === 0) { recentImages = []; candidates = Array.from({ length: total }, (_, i) => i + 1); }
  const pick = candidates[Math.floor(Math.random() * candidates.length)];
  recentImages.push(pick);
  if (recentImages.length > 8) recentImages.shift();
  return pick;
}

function applyOverlay(thumbnail) {
  if (thumbnail.dataset.jubeautified) return;
  thumbnail.dataset.jubeautified = "1";

  if (Math.random() > settings.appearChance) return;

  const parent = thumbnail.parentElement;
  if (!parent) return;
  parent.style.position = "relative";

  const imgNum = pickRandomImage(imageCount);
  const overlay = document.createElement("img");
  overlay.src = chrome.runtime.getURL(`images/${imgNum}.png`);
  overlay.style.cssText = [
    "position:absolute",
    "bottom:0",
    "right:0",
    "height:80%",
    "width:auto",
    "pointer-events:none",
    "z-index:10",
    `transform:${Math.random() < settings.flipChance ? "scaleX(-1)" : "none"}`,
  ].join(";");

  thumbnail.insertAdjacentElement("afterend", overlay);
}

function findThumbnails() {
  const selectors = [
    "ytd-thumbnail a > yt-image > img.yt-core-image",
    'img.style-scope.yt-img-shadow[width="86"]',
    ".yt-thumbnail-view-model__image img",
    ".ytp-videowall-still-image",
  ];
  const all = [];
  for (const sel of selectors) {
    document.querySelectorAll(sel).forEach(el => all.push(el));
  }
  return all.filter(el => {
    if (el.dataset.jubeautified) return false;
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) return false;
    const ratio = r.width / r.height;
    return ratio > 1.2 && ratio < 2.5;
  });
}

function tick() {
  if (settings.extensionIsDisabled) return;
  findThumbnails().forEach(applyOverlay);
}

function detectImageCount() {
  let count = 0;
  function probe(n) {
    const img = new Image();
    img.onload = () => { count = n; probe(n + 1); };
    img.onerror = () => { imageCount = count; };
    img.src = chrome.runtime.getURL(`images/${n}.png`);
  }
  probe(1);
}

loadSettings(() => {
  detectImageCount();
  setInterval(tick, 100);
  chrome.storage.onChanged.addListener(() => loadSettings(null));
});
