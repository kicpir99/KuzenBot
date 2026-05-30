# KuzenBot 🐢⚡

<div align="center">
  <a href="#-english-version">🇬🇧 English</a> • <a href="#-wersja-polska">🇵🇱 Polski</a>
</div>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python Version">
  <img src="https://img.shields.io/badge/UI-PyQt6-green" alt="PyQt6">
  <img src="https://img.shields.io/badge/Game-Smite_2-orange" alt="Smite 2">
</p>

---

## 🇬🇧 English Version

**KuzenBot** is an advanced, lightweight overlay for Smite 2 players that delivers the best community builds and meta statistics right to your screen, without the need to minimize the game (Alt-Tab).

> ⚠️ **IMPORTANT:** For the overlay to render correctly on top of the game, Smite 2 **must** be running in **Borderless Window** or **Windowed** mode. Exclusive Fullscreen mode will block the overlay from appearing.

### 📸 See it in action

*(Drag and drop your GIFs/screenshots directly into the GitHub editor to generate links and replace the ones below)*

<div align="center">
  <img src="https://github.com/user-attachments/assets/your-link-here-1" alt="Expanded view with build list" width="45%">
  <img src="https://github.com/user-attachments/assets/your-link-here-2" alt="Mini Mode during match" width="45%">
</div>

### ✨ Main Features

* 🔄 **Two Build Engines on the Fly:** Seamlessly switch between community-created builds and mathematically calculated stats from top players (Stats: Master+ & Demigod).
* 🎯 **God Detection (Auto Mode):** The integrated scanner can automatically detect the god you just picked and instantly load their builds.
* 📱 **Dedicated Mini Mode:** With one click, collapse the app into a minimalist bar that discreetly displays items and skill orders during the match.
* 🛡️ **Click-Through & Always on Top:** Ability to "lock" the overlay – making it transparent to mouse clicks, allowing for normal gameplay while it hovers over the Smite 2 UI.
* 🌍 **Multilingual Support (i18n):** Full support for multiple languages (EN, PL, FR, DE, ES, PT, and more).

### 🛠️ Tech Stack

* **Language:** Python 3.10+
* **GUI:** PyQt6 (with advanced `QPropertyAnimation` animations)
* **Architecture:** Custom HTTP threading system (`QThread`) with local Caching for instant data loading.
* **Game Integration:** Real-time log analysis.

### 🚀 Getting Started (For Developers)

If you want to run the project from the source:

1. Clone the repository:
   ```bash
   git clone [https://github.com/TwojNick/KuzenBot.git](https://github.com/TwojNick/KuzenBot.git)
   cd KuzenBot
   ```

---

## 🇵🇱 Wersja Polska

**KuzenBot** to zaawansowana, lekka nakładka (overlay) dla graczy Smite 2, która dostarcza najlepsze buildy społeczności i statystyki meta prosto na Twój ekran, bez konieczności minimalizowania gry (Alt-Tab).

> ⚠️ **WAŻNE:** Aby nakładka wyświetlała się poprawnie nad grą, Smite 2 **musi** być uruchomiony w trybie **Borderless Window** (Okno bez ramek) lub **Windowed** (W oknie). Pełny ekran (Exclusive Fullscreen) zablokuje widoczność interfejsu aplikacji.

### 📸 Zobacz w akcji

*(Przeciągnij i upuść swoje GIFy/screeny prosto do edytora GitHub, aby wygenerować linki i podmienić te poniżej)*

<div align="center">
  <img src="https://github.com/user-attachments/assets/your-link-here-1" alt="Wielki widok z listą buildów" width="45%">
  <img src="https://github.com/user-attachments/assets/your-link-here-2" alt="Tryb Mini w trakcie gry" width="45%">
</div>

### ✨ Główne Funkcje

* 🔄 **Dwa Silniki Buildów w Locie:** Płynne przełączanie między buildami tworzonymi przez społeczność (Community), a matematycznie wyliczanymi statystykami od najlepszych graczy (Stats: Master+ & Demigod).
* 🎯 **Wykrywanie Boga (Auto Mode):** Zintegrowany skaner potrafi automatycznie wykryć bohatera, którego właśnie wybrałeś, i natychmiast załadować jego buildy.
* 📱 **Dedykowany Tryb Mini:** Jednym kliknięciem zwiń aplikację do minimalistycznego paska, który dyskretnie wyświetla przedmioty i swapy podczas meczu.
* 🛡️ **Click-Through & Always on Top:** Możliwość "zablokowania" nakładki – staje się ona przezroczysta dla kliknięć myszką, pozwalając na normalną grę, gdy wisi nad interfejsem Smite 2.
* 🌍 **Wielojęzyczność (i18n):** Pełne wsparcie dla wielu języków (EN, PL, FR, DE, ES, PT i innych).

### 🛠️ Stack Technologiczny

* **Język:** Python 3.10+
* **Interfejs Graficzny:** PyQt6 (z zaawansowanymi animacjami `QPropertyAnimation`)
* **Architektura:** Własny system wątków HTTP (`QThread`) z lokalnym Cache'owaniem dla natychmiastowego ładowania danych.
* **Integracja z grą:** Analiza logów w czasie rzeczywistym.

### 🚀 Jak zacząć (Dla developerów)

Jeśli chcesz uruchomić projekt ze źródeł:

1. Sklonuj repozytorium:
   ```bash
   git clone [https://github.com/TwojNick/KuzenBot.git](https://github.com/TwojNick/KuzenBot.git)
   cd KuzenBot
   ```