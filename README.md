# Serpent Studio

[![Release](https://img.shields.io/github/v/release/bkbariskucuk/serpent-studio?include_prereleases&style=flat-square)](https://github.com/bkbariskucuk/serpent-studio/releases/latest)
[![Platform](https://img.shields.io/badge/platform-Linux%20x86__64-blue?style=flat-square)](https://github.com/bkbariskucuk/serpent-studio/releases/latest)
[![Architecture](https://img.shields.io/badge/architecture-Native%20C%20Binary-green?style=flat-square)](https://github.com/bkbariskucuk/serpent-studio/releases/latest)

> Advanced graphical user interface, interactive core geometry visualizer, and analytical post-processing platform for the **Serpent 2 Monte Carlo** reactor physics code.

---

## 🚀 Quick Download & Run (Linux x86_64)

Serpent Studio is distributed as a standalone, portable **Linux AppImage**. No Python, Conda, or external dependencies are required.

### 1. Download
Download the latest AppImage from **[GitHub Releases](https://github.com/bkbariskucuk/serpent-studio/releases/latest)**:

```bash
# Download latest AppImage release
wget https://github.com/bkbariskucuk/serpent-studio/releases/latest/download/SerpentStudio-x86_64.AppImage
```

### 2. Make Executable and Run
```bash
chmod +x SerpentStudio-x86_64.AppImage
./SerpentStudio-x86_64.AppImage
```

---

## 🌟 Key Features

- **Core & Assembly Geometry Visualization:** Interactive 2D/3D core map inspection, fuel assembly lattice grid, and pin-level material assignment.
- **Control Rod Kinematics:** Bank insertion depth controls, step-by-step movement preview, and differential reactivity tracking.
- **Nuclear Data Discovery:** Integrated isotopic composition wizards, enrichment calculators, and automated cross-section library detection.
- **Analytical Charting Suite:**
  - $K_{\text{eff}}$ evolution vs. Burnup & Cycle Days
  - Power Peaking Factors (PPF) with multi-axial slicing
  - Core moderation ratio ($V_m / V_f$) and heavy metal inventory
  - Delayed neutron fractions ($\beta_{\text{eff}}$) and kinetics parameters
  - Reactivity coefficients and decay heat analysis
- **Accessibility & CVD Support:** Full palette support for Color Vision Deficiencies (Protanopia, Deuteranopia, Tritanopia, Achromatopsia).
- **Delta Auto-Updates:** Built-in ZSync auto-updater downloads only changed blocks (~2-5 MB) on new releases.

---

## 🔄 Automatic Delta Updates

Serpent Studio features embedded ZSync delta updating. When a new version is released:
1. Open Serpent Studio.
2. Select **Help -> Check for Updates...** from the menu bar.
3. Click **Update** to fetch only the altered delta blocks and restart.

---

## 📋 System Requirements

- **Operating System:** Linux (Ubuntu 20.04+, Debian 11+, Fedora 36+, Rocky Linux 9+, Arch Linux)
- **Architecture:** x86_64 (64-bit)
- **Graphics:** OpenGL 2.1+ compatible GPU (Software fallback supported via `--no-splash`)

---

## 📄 License & Disclaimer

Serpent Studio is proprietary software. All rights reserved.  
Serpent is a continuous-energy Monte Carlo reactor physics burnup calculation code developed at VTT Technical Research Centre of Finland. Serpent Studio is an independent graphical environment and is not officially affiliated with VTT.
