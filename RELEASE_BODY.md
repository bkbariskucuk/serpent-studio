# Serpent Studio v0.2.59.32

> Advanced Graphical User Interface, Interactive Core Geometry Visualizer, and Analytical Post-Processing Platform for **Serpent 2 Monte Carlo** Reactor Physics.

---

### 📥 Son Kullanıcı İçin İndirme / Download for End-Users

> [!IMPORTANT]
> **Tek İndirmeniz Gereken Dosya / Only File You Need:**  
> 👉 [**`SerpentStudio-x86_64.AppImage`**](https://github.com/bkbariskucuk/serpent-studio/releases/download/v0.2.59.32/SerpentStudio-x86_64.AppImage) (~132 MB)

#### 🚀 Nasıl Çalıştırılır? / Quick Start:
1. **İzin Verin:** Dosyaya sağ tıklayın -> *Özellikler* -> *İzinler* -> *"Dosyayı program gibi çalıştırmaya izin ver"* seçeneğini işaretleyin.  
   *(Veya terminalden: `chmod +x SerpentStudio-x86_64.AppImage`)*
2. **Çalıştırın:** Çift tıklayın veya terminalden `./SerpentStudio-x86_64.AppImage` yazın.  
   *(Python veya herhangi bir kütüphane kurulumu gerektirmez, tamamen bağımsızdır).*

---

### 📦 Dosya Açıklamaları (Assets Guide)

| Dosya Adı | Boyut | Açıklama | Kullanıcı İndirmeli mi? |
| :--- | :--- | :--- | :--- |
| 🟢 **`SerpentStudio-x86_64.AppImage`** | **~132 MB** | **Ana çalıştırılabilir uygulama paketi** | **EVET (Tek gerekli dosya)** |
| ⚙️ `SerpentStudio-x86_64.AppImage.zsync` | ~230 KB | **Delta Güncelleme Haritası:** Uygulama içi otomatik güncelleyicinin yeni sürümlerde sadece değişen parçaları indirmesini sağlar. | Otomatik (Uygulama kullanır) |
| 📋 `version_manifest.json` | 652 B | **Sürüm Kontrol Metaverisi:** Uygulamanın menüsündeki *"Check for Updates..."* butonu için canlı sürüm bilgisi. | Otomatik (Uygulama kullanır) |

---

### 🌟 Bu Sürümde Neler Yeni? (Release Notes - v0.2.59.32)

#### 1. 🛡️ Çevrimdışı Kimlik Doğrulama Güvenliği & Özel Yerel Hesap (Offline Auth Overhaul)
- **Eski Hesapların Temizlenmesi:** Önceki genel çevrimdışı kullanıcı hesapları (`admin`, `baris`) ve varsayılan parolaları sistemden tamamen kaldırıldı.
- **Özel Yetkili Yerel Hesap:** Yerel yetkili kullanıcı adı `bariskucuk` olarak tanımlandı ve 16 haneli yüksek entropili güçlü parola ile koruma altına alındı (PBKDF2-HMAC-SHA256, 100.000 iterasyon).
- **Yüksek Güvenlik:** `credentials.json`, `~/.config/serpent-studio/local_credentials.json` ve çekirdek auth modülü yeni güvenlik politikasıyla güncellendi; birim testleriyle doğrulandı.

#### 2. 🔷 Yakıt Demeti (Assembly) Altıgen Kafes Çizim Restorasyonu (Hexagonal Canvas Restoration)
- **Kök Düzeltme:** Çoklu dil (i18n) geçişlerinde combobox seçenek metinlerinin teknik Serpent sözdizimini (`lat 1/2/3`) bozması engellendi.
- **Sağlam Geometri Tespiti:** Demet çizim motoru (`draw_assembly_canvas`), demet lattice tipi (`type 2/3`), indeks numaraları ve anahtar sözcükleri eksiksiz kapsayacak şekilde altıgen geometri çizimini (`ClickableCoreHexItem`) güvenceye aldı.
- Altıgen demetler hem Türkçe hem İngilizce dil modlarında gerçeğe uygun altıgen hücre matrisi olarak görüntülenmektedir.

#### 3. 🎨 Arayüz, Tema ve Dinamik Dil Geliştirmeleri (UI & Theme Polish)
- **SpinBox Tooltip Tema Uyumu:** Sayısal giriş (SpinBox) üzerine gelindiğinde beliren tooltip pencerelerinin simsiyah açılma sorunu giderildi; Dark ve Light temalarla tam uyumlu dinamik QSS ve palet entegrasyonu sağlandı.
- **İki Kademeli Serpent Input Preview Başlığı:** Önizleme başlık alanı iki kademeli hiyerarşik yapıya geçirilerek panel daraltılsa bile combobox veya butonların altında kalması engellendi.
- **Kontrol Çubuğu (CRS) Popout Tema Uyumu:** Popout iletişim kutusunda buton stilleri, kaydırma çubuğu ve arka plan renk uyumsuzlukları giderildi.
- **8 Ana Sekmede Dinamik Dil (i18n):** Materials, Assembly, Core Editor, Control Rods, Detectors, Coefficients, Settings ve Plot sekmelerindeki tüm etiket ve alanlar dil tercihine bağlandı.

#### 4. 🧪 Otomatik Doğrulama ve Testler
- Pre-flight test paketi (`test_version_policy`, `test_splash_and_bootstrap`, `test_dark_mode`, `test_updater`, `test_auth`, `test_accessibility_and_color_blindness`, `test_th_core_mapper_and_crs`, `test_search_include_and_crashes`) ve yeni arayüz testleri eksiksiz geçirilmiştir.

---

### 🔒 Dosya Bütünlüğü Doğrulama (Checksums)

- **SHA-256:** `c647900e1607d896a9134604dd59b976e768e4eab963897e8bd642d4c88b0cf1`

Terminalden doğrulamak için:
```bash
echo "c647900e1607d896a9134604dd59b976e768e4eab963897e8bd642d4c88b0cf1  SerpentStudio-x86_64.AppImage" | sha256sum -c
```

---

### 💻 Sistem Gereksinimleri

- **İşletim Sistemi:** Linux x86_64 (Ubuntu 20.04+, Debian 11+, Fedora 36+, Arch Linux vb.)
- **Mimari:** 64-bit (x86_64)
- **Grafik:** OpenGL 2.1+ destekli ekran kartı (Yazılımsal işleme `--no-splash` bayrağıyla desteklenir)
