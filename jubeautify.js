const IMAGES_PATH = "images/";
let useAlternativeImages;
let flipBlacklist;
let blacklistStatus;
const EXTENSION_NAME = chrome.runtime.getManifest().name;

let extensionIsDisabled = false;
let appearChance = 1.00;
let flipChance = 0.25;

function applyOverlay(thumbnailElement, overlayImageURL, flip = false) {
    const overlayImage = document.createElement("img");
    overlayImage.id = EXTENSION_NAME;
    overlayImage.src = overlayImageURL;
    overlayImage.style.position = "absolute";
    overlayImage.style.top = overlayImage.style.left = "50%";
    overlayImage.style.width = "100%";
    overlayImage.style.transform = `translate(-50%, -50%) ${flip ? 'scaleX(-1)' : ''}`;
    overlayImage.style.zIndex = "0";
    thumbnailElement.parentElement.insertBefore(overlayImage, thumbnailElement.nextSibling);
}

function FindThumbnails() {
    const imageSelectors = [
        "ytd-thumbnail a > yt-image > img.yt-core-image",
        'img.style-scope.yt-img-shadow[width="86"]',
        '.yt-thumbnail-view-model__image img',
        'img.ytCoreImageHost'
    ];

    const allImages = [];
    for (const selector of imageSelectors) {
        allImages.push(...Array.from(document.querySelectorAll(selector)));
    }

    const targetAspectRatio = [16 / 9, 4 / 3];
    const errorMargin = 0.02;

    var listAllThumbnails = allImages.filter(image => {
        if (image.height === 0) return false;
        const aspectRatio = image.width / image.height;
        return targetAspectRatio.some(r => Math.abs(aspectRatio - r) < errorMargin);
    });

    const videoWallImages = document.querySelectorAll(".ytp-videowall-still-image");
    const cuedThumbnailOverlays = document.querySelectorAll('div.ytp-cued-thumbnail-overlay-image');
    const shortsImages = document.querySelectorAll('ytd-rich-grid-slim-media img, ytm-shorts-lockup-view-model img');
    listAllThumbnails.push(...videoWallImages, ...cuedThumbnailOverlays, ...shortsImages);

    return listAllThumbnails.filter(image => {
        const parent = image.parentElement;
        const isVideoPreview = parent.closest("#video-preview") !== null ||
            Array.from(parent.classList).some(cls => cls.includes("ytAnimated"));
        const isChapter = parent.closest("#endpoint") !== null;
        const processed = Array.from(parent.children).filter(child => {
            const alreadyHasAThumbnail = child.id && child.id.includes(EXTENSION_NAME);
            return alreadyHasAThumbnail || isVideoPreview || isChapter;
        });
        return processed.length == 0;
    });
}

function applyOverlayToThumbnails() {
    thumbnailElements = FindThumbnails();
    thumbnailElements.forEach((thumbnailElement) => {
        let flip = Math.random() < flipChance;
        let baseImagePath = getRandomImageFromDirectory();
        if (flip && flipBlacklist && flipBlacklist.includes(baseImagePath)) {
            flip = false;
        }
        const overlayImageURL = Math.random() < appearChance ?
            getImageURL(baseImagePath) : "";
        applyOverlay(thumbnailElement, overlayImageURL, flip);
    });
}

function getImageURL(index) {
    return chrome.runtime.getURL(`${IMAGES_PATH}${index}.png`);
}

const size_of_non_repeat = 8;
const last_indexes = Array(size_of_non_repeat).fill(-1);

var imageList = [];

function getRandomImageFromDirectory() {
    if (imageList.length <= size_of_non_repeat) last_indexes.fill(-1);
    let pick;
    do {
        pick = imageList[Math.floor(Math.random() * imageList.length)];
    } while (last_indexes.includes(pick));
    last_indexes.shift();
    last_indexes.push(pick);
    return pick;
}

async function getHighestImageIndex() {
    const response = await fetch(chrome.runtime.getURL(`${IMAGES_PATH}count.json`));
    const data = await response.json();
    imageList = data.images || [];
}

async function GetFlipBlocklist() {
    try {
        const response = await fetch(chrome.runtime.getURL(`${IMAGES_PATH}flip_blacklist.json`));
        const data = await response.json();
        useAlternativeImages = data.useAlternativeImages;
        flipBlacklist = data.blacklistedImages || data;
        blacklistStatus = `Flip blacklist found.`;
    } catch (error) {
        blacklistStatus = "No flip blacklist found.";
    }
}

async function LoadConfig() {
    return new Promise((resolve) => {
        chrome.storage.local.get({ extensionIsDisabled, appearChance, flipChance }, (config) => {
            extensionIsDisabled = config.extensionIsDisabled;
            appearChance = config.appearChance;
            flipChance = config.flipChance;
            resolve();
        });
    });
}

async function Main() {
    await LoadConfig();
    if (extensionIsDisabled) {
        console.info(`${EXTENSION_NAME} is disabled.`);
        return;
    }
    await GetFlipBlocklist();
    console.info(`${EXTENSION_NAME} detecting images... (404s below are normal)`);
    await getHighestImageIndex().then(() => {
        setInterval(applyOverlayToThumbnails, 100);
        console.info(`${EXTENSION_NAME} loaded. ${highestImageIndex} images. ${blacklistStatus}`);
    });
}

Main();
