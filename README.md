# Serpent Studio

[![Release](https://img.shields.io/github/v/release/bkbariskucuk/serpent-studio?include_prereleases&style=flat-square&color=blue)](https://github.com/bkbariskucuk/serpent-studio/releases/latest)
[![Platform](https://img.shields.io/badge/platform-Linux%20x86__64-orange?style=flat-square)](https://github.com/bkbariskucuk/serpent-studio/releases/latest)
[![Architecture](https://img.shields.io/badge/binary-Native%20C%20(Nuitka)-green?style=flat-square)](https://github.com/bkbariskucuk/serpent-studio/releases/latest)
[![Updates](https://img.shields.io/badge/delta%20updates-ZSync%20Enabled-teal?style=flat-square)](https://github.com/bkbariskucuk/serpent-studio/releases/latest)

> Advanced graphical user interface, interactive core geometry visualizer, and analytical post-processing platform for the **Serpent 2 Monte Carlo** continuous-energy reactor physics calculation code.

---

## 🚀 Hızlı İndirme ve Çalıştırma / Quick Download & Run

Serpent Studio, bağımsız ve taşınabilir bir **Linux AppImage** paketi olarak dağıtılmaktadır. Python, Conda veya herhangi bir ek paket kurmanıza gerek yoktur.

### 📥 1. İndirin / Download
Yalnızca tek bir dosyayı indirmeniz yeterlidir:  
👉 **[SerpentStudio-x86_64.AppImage](https://github.com/bkbariskucuk/serpent-studio/releases/latest/download/SerpentStudio-x86_64.AppImage)** *(~159 MB)*

Veya terminalden:
```bash
wget https://github.com/bkbariskucuk/serpent-studio/releases/latest/download/SerpentStudio-x86_64.AppImage
```

### ⚡ 2. Çalıştırma İzni Verin ve Başlatın / Make Executable & Run
```bash
chmod +x SerpentStudio-x86_64.AppImage
./SerpentStudio-x86_64.AppImage
```
*(Masaüstü ortamında dosyaya sağ tıklayıp **Özellikler -> İzinler -> Dosyayı bir program gibi çalıştırmaya izin ver** seçeneğini de işaretleyebilirsiniz).*

---

## 📦 Dağıtım Dosyaları Rehberi / Release Assets Guide

| Dosya Adı | Açıklama | Kullanıcı İndirmeli mi? |
| :--- | :--- | :---: |
| 🟢 **`SerpentStudio-x86_64.AppImage`** | **Ana çalıştırılabilir uygulama paketi.** Çift tıklayarak doğrudan çalışır. | **EVET (Tek gerekli dosya)** |
| ⚙️ `SerpentStudio-x86_64.AppImage.zsync` | **Delta Güncelleme Haritası:** Uygulama içindeki otomatik güncelleyici yeni sürümlerde sadece değişen kod bloklarını (~2-5 MB) indirmek için bu dosyayı arka planda kullanır. | Otomatik (Uygulama arka planda okur) |
| 📋 `version_manifest.json` | **Sürüm Kontrol Metaverisi:** Uygulamanın menüsündeki *"Help -> Check for Updates..."* özelliği için canlı sürüm ve değişiklik notlarını barındırır. | Otomatik (Uygulama arka planda okur) |

---

## 🌟 Öne Çıkan Özellikler / Key Features

- **Reaktör Kalbi ve Yakıt Demeti Geometrisi (Core & Lattice Visualizer):**
  - İnteraktif 2D/3D petek ve kartezyen çekirdek haritaları
  - Yakıt çubuğu (pin-by-pin) ve kontrol çubuğu malzeme eşlemesi
  - Dinamik eksenel ve radyal kesit görünümü
- **Kontrol Çubukları Kinematiği (Control Rod Movement):**
  - Çubuk grubu çekilme/batırılma derinlik kontrolleri (Bank Insertion Depth)
  - Adım adım kontrol çubuğu hareket önizlemesi ve diferansiyel reaktivite takibi
- **Nükleer Veri ve Zenginleştirme Asistanı:**
  - İzotopik bileşim sihirbazları ve ağır metal zenginleştirme hesaplayıcıları
  - JEFF-3.2 / ENDF/B-VII.1 tesir kesiti kütüphanelerinin otomatik algılanması
- **Gelişmiş Analitik Grafikleme:**
  - $K_{\text{eff}}$ zaman/yanma (burnup) grafikleri ve $1\sigma$ belirsizlik bantları
  - Güç Tepe Faktörleri (PPF - Power Peaking Factor) çoklu eksenel dilimleme
  - Yavaşlatıcı / Yakıt hacim oranları ($V_m / V_f$) ve ağır metal envanteri
  - Gecikmiş nötron fraksiyonları ($\beta_{\text{eff}}$), kinetik parametreler ve bozunma ısısı analizleri
- **Erişilebilirlik ve Renk Körlüğü Desteği (Color Vision Deficiency - CVD):**
  - Bilimsel Okabe-Ito ve Tol CVD algoritmalarıyla Protanopia, Deuteranopia, Tritanopia ve Achromatopsia renk profilleri
- **Çift Kademeli Kimlik Doğrulama (Dual-Tier Authentication):**
  - Yetkili hesaplar için yerel çevrimdışı tuzlanmış PBKDF2 doğrulaması
  - Genel son kullanıcılar için güvenli HTTPS bulut doğrulaması
- **Kesintisiz Uygulama İçi Güncellemeler (In-App Delta Updates):**
  - ZSync protokolüyle 160 MB yerine yalnızca değişen birkaç megabaytlık delta bloklarını indirerek anında güncelleme

---

## 🔄 Otomatik Güncellemeler Nasıl Çalışır?

Serpent Studio açıkken yeni bir sürüm çıktığında:
1. Menü çubuğundan **Help -> Check for Updates...** seçeneğine tıklayın.
2. Yeni sürüm notları ve değişiklikler listelenir.
3. **Update** butonuna bastığınızda ZSync motoru arka planda yalnızca değişen kısımları indirip uygulamayı günceller.

---

## 💻 Sistem Gereksinimleri

- **İşletim Sistemi:** Linux x86_64 (Ubuntu 20.04+, Debian 11+, Fedora 36+, Rocky Linux 9+, Arch Linux vb.)
- **Mimari:** 64-bit (x86_64)
- **Grafik:** OpenGL 2.1+ destekli ekran kartı (Yazılımsal grafik uyumluluk modu için `--no-splash` bayrağı kullanılabilir)

---

## 📄 Lisans ve Sorumluluk Reddi / License & Disclaimer

Serpent Studio tescilli bir yazılımdır. Tüm hakları saklıdır.  
*Serpent*, Finlandiya VTT Teknik Araştırma Merkezi tarafından geliştirilen sürekli enerjili Monte Carlo reaktör fiziği kodudur. Serpent Studio bağımsız bir grafiksel arayüz ve analiz platformu olup VTT ile resmi bir ortaklığı bulunmamaktadır.
