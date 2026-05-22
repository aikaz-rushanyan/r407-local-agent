document.getElementById('checkBtn').addEventListener('click', async () => {
  // Получаем текущую активную вкладку
  let [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab) {
    document.getElementById('result').innerText = `URL: ${tab.url}\nTitle: ${tab.title}`;
  }
});