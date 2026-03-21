# NotebookLM Deep Research Launcher (Chrome Extension)

## Что делает

По клику на иконку расширения:
1. Если NotebookLM уже открыт, запускает сценарий в текущей вкладке.
2. Если вкладки нет, открывает `https://notebooklm.google.com/`.
3. Создаёт новый notebook.
4. Открывает правый выпадающий список режима исследования и выбирает `Deep Research`.
5. Размещает prompt в поле ввода.
6. Запускает исследование.
7. Ждёт завершения исследования.
8. Выполняет шаг добавления источников.
9. Запускает генерацию `Video Overview`.
10. Запускает генерацию `Audio Overview`.

## Установка

1. Откройте `chrome://extensions`.
2. Включите `Developer mode`.
3. Нажмите `Load unpacked`.
4. Выберите папку проекта: `/Users/kirill/MyApps/Good News`.

## Использование

- Нажмите на иконку расширения: запустится сценарий.
- Для настройки prompt откройте `Details` у расширения -> `Extension options`.

## Важно

- NotebookLM UI меняется, поэтому автоклики best-effort.
- Для работы нужна активная авторизация Google в Chrome.
- Если какой-то шаг не сработал, откройте options и скорректируйте prompt, затем повторите запуск.
- Все ошибки, таймауты и прерывания сценария логируются в:
  - `chrome.storage.local` ключ `runLogs` (последние 300 записей),
  - консоль service worker/content script (`[NotebookLM Launcher]`).
