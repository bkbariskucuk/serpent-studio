# Serpent Studio v0.2.53.16

> Advanced Graphical User Interface, Interactive Core Geometry Visualizer, and Analytical Post-Processing Platform for **Serpent 2 Monte Carlo** Reactor Physics.

---

### 📥 Son Kullanıcı İçin İndirme / Download for End-Users

> [!IMPORTANT]
> **Tek İndirmeniz Gereken Dosya / Only File You Need:**  
> 👉 [**`SerpentStudio-x86_64.AppImage`**](https://github.com/bkbariskucuk/serpent-studio/releases/download/v0.2.53.16/SerpentStudio-x86_64.AppImage) (~132 MB)

#### 🚀 Nasıl Çalıştırılır? / Quick Start:
1. **İzin Verin:** Dosyaya sağ tıklayın -> *Özellikler* -> *İzinler* -> *"Dosyayı program gibi çalıştırmaya izin ver"* seçeneğini işaretleyin.  
   *(Veya terminalden: `chmod +x SerpentStudio-x86_64.AppImage`)*
2. **Çalıştırın:** Çift tıklayın veya terminalden `./SerpentStudio-x86_64.AppImage` yazın.  
   *(Python veya herhangi bir kütüphane kurulumu gerektirmez, tamamen bağımsızdır).*

---

### 📦 Dosya Açıklamaları (Assets Guide)

| Dosya Adı | Boyut | Açıklama | Kullanıcı İndirmeli mi? |
| :--- | :--- | :--- | :---: |
| 🟢 **`SerpentStudio-x86_64.AppImage`** | **~132 MB** | **Ana çalıştırılabilir uygulama paketi** | **EVET (Tek gerekli dosya)** |
| ⚙️ `SerpentStudio-x86_64.AppImage.zsync` | ~230 KB | **Delta Güncelleme Haritası:** Uygulama içi otomatik güncelleyicinin yeni sürümlerde sadece değişen parçaları (~2-5 MB) indirmesini sağlar. | Otomatik (Uygulama kullanır) |
| 📋 `version_manifest.json` | 652 B | **Sürüm Kontrol Metaverisi:** Uygulamanın menüsündeki *"Check for Updates..."* butonu için canlı sürüm bilgisi. | Otomatik (Uygulama kullanır) |

---

### 🌟 Bu Sürümde Neler Yeni? (Release Notes - v0.2.53.16)

#### 1. ⚡ Sıfır Gecikmeli & Akıcı Splash Ekranı (Zero-Lag Splash Engine)
- **Donanım Hızlandırmalı Önbellekleme:** 969 noktalı 23 izohips topoğrafya eğrisi, radyal parlamalar ve degrade arka plan GPU dostu `QPixmap` önbelleğinde önceden işlenir.
- **50 Kat Render Hızlanması:** Çizim süresi 18.15 ms'den 0.36 ms'ye düşürülerek Linux X11/Wayland ortamlarında takılma, atlama ve gecikmeler tamamen ortadan kaldırıldı.
- **50 FPS Kararlı Zamanlayıcı:** Kare atlamayan optimize zamanlama ile pürüzsüz akış sağlandı.

#### 2. ⏸️ Kapsamlı Animasyon Durdurma Yayılımı (Complete Animation Suppression)
- **Grafik & Çizim Animasyonları:** Çizgi grafikler (`LineChartAnimator`), çubuk grafikler (`BarChartAnimator`) ve radyal PPF çekirdek haritaları (`PpfChartAnimator`) için giriş ve geçiş animasyonları anında tamamlanır; grafikler beklemeden direkt olarak çizilir.
- **Çalışma Alanı Ağacı & List/Delist:** Ağaç daraltma/genişletme basamak animasyonları, toplu liste açma/kapama ve dosya/anlık görüntü silme (delist) görsel geçişleri anında gerçekleşir.
- **Durum Akışı:** Durum çubuğundaki kayan yazı zamanlayıcısı durdurulup statik net metin moduna alınır.
- **Pencereler & Geçişler:** Ayrık konsol ve preflight pencerelerinin solma animasyonları ile tema geçiş katmanı anlık moda geçirilir.

#### 3. 🧼 Temiz Çalışma Alanı ve Dağıtım Ayrımı (Clean Workspace Architecture)
- Dağıtılan AppImage paketi hiçbir artık dosya veya örnek veri içermez; tertemiz bir başlangıç sunar.
- Geliştiricinin yerel çalışma alanı (`serpent-gui/workspace/`) tam güvenlikle korunur.

---

### 💻 Sistem Gereksinimleri

- **İşletim Sistemi:** Linux x86_64 (Ubuntu 20.04+, Debian 11+, Fedora 36+, Arch Linux vb.)
- **Mimari:** 64-bit (x86_64)
- **Grafik:** OpenGL 2.1+ destekli ekran kartı (Yazılımsal işleme `--no-splash` bayrağıyla desteklenir)
