function loadSettings() {
  chrome.storage.local.get(
    { extensionIsDisabled: false, appearChance: 1.0, flipChance: 0.25 },
    (data) => {
      document.getElementById("disableExtension").checked = !data.extensionIsDisabled;
      document.getElementById("appearChance").value = Math.round(data.appearChance * 100);
      document.getElementById("flipChance").value = Math.round(data.flipChance * 100);
    }
  );
}

function saveSettings() {
  chrome.storage.local.set({
    extensionIsDisabled: !document.getElementById("disableExtension").checked,
    appearChance: parseInt(document.getElementById("appearChance").value) / 100,
    flipChance: parseInt(document.getElementById("flipChance").value) / 100,
  });
}

function updateTitle() {
  const name = chrome.runtime.getManifest().name.replace(/youtube/i, "").trim();
  const el = document.getElementById("extension-title");
  el.textContent = el.textContent.replace("TITLE", name);
}

document.addEventListener("DOMContentLoaded", () => {
  loadSettings();
  updateTitle();
});
["disableExtension", "appearChance", "flipChance"].forEach(id => {
  document.getElementById(id).addEventListener("input", saveSettings);
});
