let lastUrl = "";
let lastTitle = "";
let startTime = Date.now();
let isAFK = false;

// Настройка AFK встроенными средствами Chrome (минимум 15 секунд)
const AFK_THRESHOLD_SECONDS = 300; 
chrome.idle.setDetectionInterval(AFK_THRESHOLD_SECONDS);

// Функция отправки данных на сервер Python
async function sendLogToPython(title, url, durationSeconds) {
    if (durationSeconds < 1) return; 
    
    try {
        await fetch('http://127.0.0.1:5000/log', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                process_name: "Browser", 
                window_title: `${title} (${url})`,
                duration_seconds: durationSeconds
            })
        });
    } catch (err) {
        console.log("Python сервер недоступен, лог утерян.");
    }
}

// Принудительный сброс текущего накопленного времени
async function flushCurrentLog() {
    if (lastUrl !== "" && !isAFK) {
        let now = Date.now();
        let durationSeconds = Math.round((now - startTime) / 1000);
        if (durationSeconds > 0) {
            await sendLogToPython(lastTitle, lastUrl, durationSeconds);
        }
        startTime = now;
    }
}

// Проверка и фиксация смены вкладки
async function checkCurrentTab() {
    if (isAFK) return;

    try {
        let [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (!tab || !tab.url) return;

        // Если страница действительно поменялась
        if (tab.url !== lastUrl || tab.title !== lastTitle) {
            await flushCurrentLog();
            
            // Начинаем отсчет для новой страницы
            lastUrl = tab.url;
            lastTitle = tab.title;
            startTime = Date.now();
        }
    } catch (e) {
        console.error(e);
    }
}

// Подписываемся на события браузера
chrome.tabs.onActivated.addListener(checkCurrentTab);

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (changeInfo.status === 'complete' && tab.active) {
        checkCurrentTab();
    }
});

// Отслеживание AFK состояния
chrome.idle.onStateChanged.addListener(async (state) => {
    if (state === "idle" || state === "locked") {
        isAFK = true;
        let now = Date.now();
        let durationSeconds = Math.round((now - startTime) / 1000) - AFK_THRESHOLD_SECONDS;
        if (durationSeconds > 0 && lastUrl !== "") {
            await sendLogToPython(lastTitle, lastUrl, durationSeconds);
        }
    } else if (state === "active") {
        isAFK = false;
        startTime = Date.now();
        lastUrl = ""; 
        await checkCurrentTab();
    }
});

// Периодический сброс данных (каждые 30 секунд)
setInterval(async () => {
    if (lastUrl !== "") {
        // Явно проверяем, активен ли пользователь прямо сейчас (с порогом, например, 60 секунд)
        chrome.idle.queryState(60, async (state) => {
            // Отправляем лог, ТОЛЬКО если пользователь действительно активен у компьютера
            if (state === "active" && !isAFK) {
                let now = Date.now();
                let durationSeconds = Math.round((now - startTime) / 1000);
                if (durationSeconds >= 60) {
                    await sendLogToPython(lastTitle, lastUrl, durationSeconds);
                    startTime = now; // Перезапускаем отсчет, не меняя URL
                }
            }
        });
    }
}, 30000);

// Сброс лога, если вкладка закрывается или браузер завершает работу
chrome.tabs.onRemoved.addListener(async () => {
    await flushCurrentLog();
    lastUrl = "";
    lastTitle = "";
});