<div align="center">
  <img src="logo.png" alt="KuzenBot Logo" width="120">

  # KuzenBot 🐢⚡
  **Stop Alt-Tabbing. Builds right on your screen.**
  
  <p align="center">
    <a href="#-english-version">🇬🇧 English</a> • <a href="#-wersja-polska">🇵🇱 Polski</a>
  </p>

  <p align="center">
    <img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python Version">
    <img src="https://img.shields.io/badge/UI-PyQt6-green" alt="PyQt6">
    <img src="https://img.shields.io/badge/Game-Smite_2-orange" alt="Smite 2">
    <img src="https://img.shields.io/github/v/release/kicpir99/KuzenBot?color=purple" alt="Latest Release">
  </p>

  <h3>
    <a href="https://kicpir99.github.io/KuzenBot/">🌐 Visit official website (Download)</a>
  </h3>
</div>

---

## 🇬🇧 English Version

**KuzenBot** is an advanced, lightweight overlay for Smite 2 players that delivers the best community builds and meta statistics right to your screen, without the need to minimize the game (Alt-Tab).

> ⚠️ **IMPORTANT:** For the overlay to render correctly on top of the game, Smite 2 **must** be running in **Borderless Window** or **Windowed** mode. Exclusive Fullscreen mode will block the overlay from appearing.

<div align="center">
  <h3>🛡️ 100% Safe. Zero game files modification.</h3>
  <p>KuzenBot is an external Windows overlay. It does not inject code into the game memory (Zero Memory Injection) and does not modify any files, making it completely safe to use with Anti-Cheat systems.</p>
</div>

### ✨ Main Features

| Feature | In-Game Preview |
| :--- | :---: |
| **✨ Flexible Mode (Extended & Mini)**<br>In base? Open Extended to view full item stats. In combat? Switch to Mini – a small tile that doesn't block vision. | <img src="mini.gif" width="350" alt="Mini Mode"> |
| **🤖 Intelligence (AUTO Mode)**<br>The app automatically detects the god you pick in the lobby and instantly loads the dedicated build. | <img src="lobby.gif" width="350" alt="God Detection"> |
| **🔒 Ghost Mode (Click-Through)**<br>One hotkey locks the overlay – making it transparent to mouse clicks. No more accidental panel clicks instead of casting abilities. | <img src="lock.gif" width="350" alt="Overlay Lock"> |
| **📊 Data Flexibility on the Fly**<br>Seamlessly switch between raw item statistics and the most popular community builds. | <img src="commstats.gif" width="350" alt="Data Switching"> |
| **👻 Invisible Interface**<br>Adjust the background opacity down to zero, leaving only clean item icons on the screen. | <img src="opacity.gif" width="350" alt="Opacity"> |
| **⚙️ Deep Customization**<br>Full control over the UI: precise settings, global hotkeys, and 8 built-in color themes. | <img src="options.gif" width="350" alt="Options and Themes"> |
| **🚀 Silent Auto-Updater**<br>After every game patch, the app automatically checks GitHub in the background, downloads updates, and offers a 1-click install. | <img src="auto-updater.png" width="350" alt="Auto Updates"> |

### 🛠️ Tech Stack

* **Language:** Python 3.10+
* **GUI:** PyQt6 (with advanced `QPropertyAnimation` animations)
* **Architecture:** Custom HTTP threading system (`QThread`) with local Caching for instant data loading.
* **Game Integration:** Real-time log analysis.

### 🚀 Getting Started (For Developers)

If you want to run the project from the source:

1. Clone the repository:
   ```bash
   git clone [https://github.com/kicpir99/KuzenBot.git](https://github.com/kicpir99/KuzenBot.git)
   cd KuzenBot
