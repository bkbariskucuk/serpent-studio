# Serpent Studio v0.2.55.18

> Advanced Graphical User Interface, Interactive Core Geometry Visualizer, and Analytical Post-Processing Platform for **Serpent 2 Monte Carlo** Reactor Physics.

---

### 📥 Son Kullanıcı İçin İndirme / Download for End-Users

> [!IMPORTANT]
> **Tek İndirmeniz Gereken Dosya / Only File You Need:**  
> 👉 [**`SerpentStudio-x86_64.AppImage`**](https://github.com/bkbariskucuk/serpent-studio/releases/download/v0.2.55.18/SerpentStudio-x86_64.AppImage) (~132 MB)

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

### 🌟 Bu Sürümde Neler Yeni? (Release Notes - v0.2.55.18)

#### 1. 🔍 Serpent Syntax Preview Kayan Ctrl+F Arama & Değiştirme Çubuğu (Floating Search & Replace)
- **Zarif & Sayfa Mizanpajını Bozmayan Overlay:** Kod editörünün üzerine doğrudan binen, gölgeli (`QGraphicsDropShadowEffect`) ve modern yuvarlatılmış köşeli kart görünümü.
- **Canlı Eşleşme Sayacı:** Toplam ve aktif eşleşmeyi anlık gösteren gösterge (`1 / 4`, `No results`).
- **Pürüzsüz Gezinme:** Önceki (`▲` / `Shift+Enter`) ve sonraki (`▼` / `Enter`) eşleşmelere hızlı sıçrama.
- **Gelişmiş Arama Filtreleri:** Büyük/küçük harf duyarlılığı (`Aa`), tam kelime (`\b`) ve düzenli ifade (`.*`) desteği.
- **Zarif Bul & Değiştir Paneli:** `Ctrl+H` veya `⇄` butonuyla açılan entegre değiştirme paneli (Replace / Replace All).
- **Akıllı Odak ve Escape İle Kapatma:** Seçili metni otomatik arama kutusuna alma, `Esc` ile kapatıp odağı hemen kod editörüne döndürme, kısayol çakışmalarının temizlenmesi.

#### 2. 📂 Akıllı Include Dosyası Çözümleme ve Harici Dosya Önizlemesi (Smart Include Resolution)
- **`THIncludeResolver` Entegrasyonu:** Serpent ana girdisindeki `include "tip_a.txt"` gibi göreceli veya tam yollar; proje dizini, çalışma dizini, `Base Condition`, `includes`, `inc`, `bundles` ve referans yolları taranarak diskteki gerçek dosyayla otomatik eşleştirilir.
- **Harici Dosya Gözatma:** Açılır listedeki `+ Browse External Include...` seçeneğiyle disk üzerindeki herhangi bir Serpent include dosyası seçilip incelenebilir.
- **Önbellek & Senkronizasyon Koruması:** Geçici dosya yokluk mesajlarının önbellekte takılı kalması önlendi; include dosyası incelenirken yanlışlıkla ana girdi üretiminin dosya içeriğinin üzerine yazılması engellendi.

#### 3. 🛡️ Fontconfig & Unicode Fallback Çökme Koruması (Zero Crash Architecture)
- **Kök Neden Çözümü:** KaTeX WOFF web yazı tiplerinin sistem fontconfig mekanizmasında Unicode non-BMP sembolleri (emojiler) için hatalı fallback olarak atanması sonucu `libfontconfig.so.1` (`FcCharSetHasChar`) seviyesinde oluşan SIGSEGV çökmesi kökünden giderildi.
- **Çok Katmanlı Güvenlik:** Sistem düzeyinde WOFF engelleyici kural ve `main.py` içerisinde otomatik çalışma zamanı güvenlik denetimi (`_ensure_fontconfig_safety()`) devreye alındı.
- **Kararlılık:** CRS Sekmesi (Control Rods), TH Core Canvas demet tıklamaları, `THAssemblyDetailDialog`, `AddMaterialDialog` ve `PinCustomizerDialog` pencereleri %100 kararlı ve çökmeye karşı korumalı hale getirildi.

#### 4. ⚙️ TH Demet ID & CRS Haritalama Penceresi (Manual Mapper) Çökme Koruması
- **Sinyal Senkronizasyonu Kök Düzeltmesi:** `THCoreManualMapperDialog` penceresinde parametreler değiştirilip *"Uygula"* butonuna basıldığında `THTemplatePage` nesnesinde tanımlı olmayan `system_modified` çağrısından kaynaklanan `AttributeError` çökmesi kökünden giderildi.
- **Sinyal & Hata Yakalama Mimarisi:** `THTemplatePage` sınıfına `system_modified` sinyali eklendi, diyalog kabul işleyicisi hata yakalama bloklarıyla donatıldı.
- **Küresel İstisna Kalkanı:** `main.py` içerisine entegre edilen `_global_exception_handler` ile PyQt6 slotlarında oluşabilecek beklenmedik istisnaların uygulamayı kapatması (qFatal/abort) tamamen engellendi.

#### 5. 🧪 Otomatik Doğrulama ve Regresyon Testleri
- `tests/test_search_include_and_crashes.py` test paketi eklenerek arama çubuğu kontrolleri, include çözümleme, diyaloglar ve manual mapper senkronizasyonu tam test güvencesine alındı.

---

### 🔒 Dosya Bütünlüğü Doğrulama (Checksums)

- **SHA-256:** `4944bb3828df3c2736270dc320197b153c2d8294cd395c02a5fb151cc1187905`

Terminalden doğrulamak için:
```bash
echo "4944bb3828df3c2736270dc320197b153c2d8294cd395c02a5fb151cc1187905  SerpentStudio-x86_64.AppImage" | sha256sum -c
```

---

### 💻 Sistem Gereksinimleri

- **İşletim Sistemi:** Linux x86_64 (Ubuntu 20.04+, Debian 11+, Fedora 36+, Arch Linux vb.)
- **Mimari:** 64-bit (x86_64)
- **Grafik:** OpenGL 2.1+ destekli ekran kartı (Yazılımsal işleme `--no-splash` bayrağıyla desteklenir)
