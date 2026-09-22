# Serpent Studio v0.2.53.15

> Advanced Graphical User Interface, Interactive Core Geometry Visualizer, and Analytical Post-Processing Platform for **Serpent 2 Monte Carlo** Reactor Physics.

---

### 📥 Son Kullanıcı İçin İndirme / Download for End-Users

> [!IMPORTANT]
> **Tek İndirmeniz Gereken Dosya / Only File You Need:**  
> 👉 [**`SerpentStudio-x86_64.AppImage`**](https://github.com/bkbariskucuk/serpent-studio/releases/download/v0.2.53.15/SerpentStudio-x86_64.AppImage) (~132 MB)

#### 🚀 Nasıl Çalıştırılır? / Quick Start:
1. **İzin Verin:** Dosyaya sağ tıklayın -> *Özellikler* -> *İzinler* -> *"Dosyayı program gibi çalıştırmaya izin ver"* seçeneğini işaretleyin.  
   *(Veya terminalden: `chmod +x SerpentStudio-x86_64.AppImage`)*
2. **Çalıştırın:** Çift tıklayın veya terminalden `./SerpentStudio-x86_64.AppImage` yazın.  
   *(Python veya herhangi bir kütüphane kurulumu gerektirmez, tamamen bağımsızdır).*

---

### 📦 Dosya Açıklamaları (Assets Guide)

| Dosya Adı | Boyut | Açıklama | Kullanıcı İndirmeli mi? |
| :--- | :--- | :--- | :---: |
| 🟢 **`SerpentStudio-x86_64.AppImage`** | **132.0 MB** | **Ana çalıştırılabilir uygulama paketi** | **EVET (Tek gerekli dosya)** |
| ⚙️ `SerpentStudio-x86_64.AppImage.zsync` | ~230 KB | **Delta Güncelleme Haritası:** Uygulama içi otomatik güncelleyicinin yeni sürümlerde sadece değişen parçaları (~2-5 MB) indirmesini sağlar. | Otomatik (Uygulama kullanır) |
| 📋 `version_manifest.json` | 652 B | **Sürüm Kontrol Metaverisi:** Uygulamanın menüsündeki *"Check for Updates..."* butonu için canlı sürüm bilgisi. | Otomatik (Uygulama kullanır) |

---

### 🌟 Bu Sürümde Neler Yeni? (Release Notes - v0.2.53.15)

#### 1. 🧼 Tamamen Sıfır & Temiz Çalışma Alanı (Clean Base State)
- **Sıfır Dosya Güvencesi:** Uygulama temiz kurulumda veya ilk açılışta hiçbir artık dosya, proje veya örnek veri içermez.
- **Otomatik Klasör Kaldırıldı:** Geçmişte otomatik oluşturulan `workspace/umay` klasörü ve `umay.txt` dosyası tamamen kaldırıldı.
- **Temiz Düzenleyici:** Uygulama doğrudan `workspace/` kök dizinine bağlı temiz `untitled.txt` arabelleği ile başlar; kullanıcı kaydetmedikçe diske hiçbir dosya yazılmaz.

#### 2. ♿ Kapsamlı Erişilebilirlik Paketi (Accessibility Suite)
- **🔍 Arayüz Ölçekleme & Yakınlaştırma (UI Scaling & Zoom):** %100 (Varsayılan), %125, %150, %175 ön ayarları ile `Ctrl++`, `Ctrl+-`, `Ctrl+0` klavye kısayolları eklendi.
- **🏁 Malzeme Doku / Geometrik Tarama (Pattern Hatching):** Renk körlüğü ve düşük görme için yakıt, zarf, kontrol çubuğu ve soğutucu hücrelerinde renk dışı belirgin geometrik tarama desenleri (`DiagCross`, `HorPattern`, `CrossPattern`, `DensePattern`).
- **🎯 Yüksek Karşıtlıklı Odak Göstergesi (High-Visibility Focus Indicator):** Klavye (Tab) geziniminde odaklanan tüm bileşenlerin etrafında 2px parlak neon camgöbeği (`#38BDF8` / `#0EA5E9`) belirgin sınır halkası eklendi.
- **⏸️ Tüm Animasyonları Durdur (Stop All Animations):** Tek tıkla açılış ekranı dalgalanmalarını, sayfa kayma geçişlerini ve kayan durum metinlerini anında dondurma.
- **🔔 Simülasyon Tamamlama Açılır Bildirimi (Simulation Completion Popup Alert):** Sesli uyarı yerine simülasyon tamamlandığında çalışma süresi, k-eff değeri, çıkış kodu ve hata önizlemesini bildiren zarif `SimulationCompletionDialog` açılır penceresi bağlandı. Çıktıları ve konsolu doğrudan açma imkanı sunar.
- **➕ Kanvas Kılavuz & Koordinat Çaprazı (Canvas Crosshairs):** Çekirdek ve yakıt çubuğu kanvaslarında imleç altında kesikli tam ekran kılavuz çizgileri ve merkez hedef retikülü eklendi.

#### 3. 🔐 Çift Kademeli Kimlik Doğrulama & Kararlı Linux Pencere Mimarisi
- Yetkili Yerel Kullanıcılar (`baris`, `admin`): Çevrimdışı PBKDF2-HMAC-SHA256 doğrulama.
- Genel Kullanıcılar: Bulut HTTPS API doğrulama ve 30 günlük güvenli oturum.
- Linux X11/Wayland üst düzey pencere dayanıklılığı ile tıklamalarda kapanmayan kararlı yapı.

---

### 🔒 Dosya Bütünlüğü Doğrulama (Checksums)

- **SHA-256:** `a09fd9bed68584b9c75def9fc4f9a9841c7d32147ce2e803fcd4d8b825994c30`

Terminalden doğrulamak için:
```bash
echo "a09fd9bed68584b9c75def9fc4f9a9841c7d32147ce2e803fcd4d8b825994c30  SerpentStudio-x86_64.AppImage" | sha256sum -c
```

---

### 💻 Sistem Gereksinimleri
- **İşletim Sistemi:** Linux x86_64 (Ubuntu 20.04+, Debian 11+, Fedora 36+, Arch Linux vb.)
- **Mimari:** 64-bit (x86_64)
- **Grafik:** OpenGL 2.1+ destekli ekran kartı (Yazılımsal işleme `--no-splash` bayrağıyla desteklenir)
