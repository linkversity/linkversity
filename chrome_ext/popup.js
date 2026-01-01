const BASE_URL = "https://linkversity.lol";

document.addEventListener('DOMContentLoaded', async () => {
  const loginSection = document.getElementById('login-section');
  const saveSection = document.getElementById('save-section');
  const loginBtn = document.getElementById('login-btn');
  const logoutBtn = document.getElementById('logout-btn');
  const pathSelect = document.getElementById('path-select');
  const sectionSelect = document.getElementById('section-select');
  const saveBtn = document.getElementById('save-btn');
  const statusMsg = document.getElementById('status-msg');
  const currentUrlText = document.getElementById('current-url');

  // Check login status
  chrome.storage.local.get(['api_token'], (result) => {
    if (result.api_token) {
      showSaveSection();
    } else {
      showLoginSection();
    }
  });

  loginBtn.addEventListener('click', () => {
    chrome.runtime.sendMessage({ action: "login" }, (response) => {
      if (response && response.success) {
        showSaveSection();
      }
    });
  });

  logoutBtn.addEventListener('click', () => {
    chrome.storage.local.remove(['api_token'], () => {
      showLoginSection();
    });
  });

  async function showLoginSection() {
    loginSection.classList.remove('hidden');
    saveSection.classList.add('hidden');
  }

  async function showSaveSection() {
    loginSection.classList.add('hidden');
    saveSection.classList.remove('hidden');
    
    // Get current tab URL
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    currentUrlText.textContent = tab.url;

    loadPaths();
  }

  async function loadPaths() {
    const { api_token } = await chrome.storage.local.get(['api_token']);
    try {
      const resp = await fetch(`${BASE_URL}/slack/api/paths?token=${api_token}`);
      const paths = await resp.json();
      
      pathSelect.innerHTML = '<option value="">-- Select a Path --</option>';
      paths.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.id;
        opt.textContent = p.title;
        pathSelect.appendChild(opt);
      });
    } catch (e) {
      statusMsg.textContent = "Error loading paths.";
      statusMsg.className = "status error";
    }
  }

  pathSelect.addEventListener('change', async () => {
    const pathId = pathSelect.value;
    if (!pathId) {
      sectionSelect.disabled = true;
      return;
    }

    const { api_token } = await chrome.storage.local.get(['api_token']);
    sectionSelect.disabled = false;
    sectionSelect.innerHTML = '<option value="">Loading sections...</option>';

    try {
      const resp = await fetch(`${BASE_URL}/slack/api/sections?path_id=${pathId}&token=${api_token}`);
      const sections = await resp.json();
      
      sectionSelect.innerHTML = '<option value="">-- Select a Section --</option>';
      sections.forEach(s => {
        const opt = document.createElement('option');
        opt.value = s.id;
        opt.textContent = s.title;
        sectionSelect.appendChild(opt);
      });
    } catch (e) {
      statusMsg.textContent = "Error loading sections.";
    }
  });

  sectionSelect.addEventListener('change', () => {
    saveBtn.disabled = !sectionSelect.value;
  });

  saveBtn.addEventListener('click', async () => {
    const { api_token } = await chrome.storage.local.get(['api_token']);
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    saveBtn.disabled = true;
    saveBtn.textContent = "Saving...";
    
    try {
      const resp = await fetch(`${BASE_URL}/slack/api/save-link`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          token: api_token,
          url: tab.url,
          section_id: sectionSelect.value
        })
      });

      const result = await resp.json();
      if (result.success) {
        statusMsg.textContent = "Saved successfully!";
        statusMsg.className = "status success";
        setTimeout(() => window.close(), 1500);
      } else {
        throw new Error();
      }
    } catch (e) {
      statusMsg.textContent = "Failed to save.";
      statusMsg.className = "status error";
      saveBtn.disabled = false;
      saveBtn.textContent = "Save Link";
    }
  });
});
