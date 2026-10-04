# Serpent Studio v0.2.64.39

> Advanced Graphical User Interface, Interactive Core Geometry Visualizer, and Analytical Post-Processing Platform for **Serpent 2 Monte Carlo** Reactor Physics.

---

### 📥 Son Kullanıcı İçin İndirme / Download for End-Users

> [!IMPORTANT]
> **Tek İndirmeniz Gereken Dosya / Only File You Need:**  
> 👉 [**`SerpentStudio-x86_64.AppImage`**](https://github.com/bkbariskucuk/serpent-studio/releases/download/v0.2.64.39/SerpentStudio-x86_64.AppImage) (~132 MB)

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

### 🌟 Bu Sürümde Neler Yeni? (Release Notes - v0.2.64.39)

#### 1. 🎞️ Malzeme Paneli & Termal Saçılma Çift Yönlü Kayma Animasyonu
- **Pürüzsüz Yatay Kayma (`SlidingStackedWidget`):** Malzeme Paneli içindeki Material Composition ve Thermal Scattering S(α, β) görünümleri arasındaki geçişe 260 ms süreli yumuşak yatay kayma (horizontal slide) animasyonu entegre edildi.
- **İleri Geçiş (Malzeme → Termal S(α, β)):** Sağdan sola doğru (`offset = +width → 0`) OutCubic eğrisiyle akıcı kayma. Tablo verisi animasyon başlamadan önce yüklenerek boş ekran veya takılma engellenir.
- **Geri Geçiş (Termal S(α, β) → Malzeme):** "← Back to Materials" butonuna tıklandığında veya termal tablodan bir satıra çift tıklandığında soldan sağa doğru (`offset = -width → 0`) ters yönlü kayma ile malzeme tablosuna dönülür.
- **Mantıksal Durum ve Kesinti Güvenliği:** Animasyon devam ederken `currentIndex()` ve `currentWidget()` anında hedef sayfayı raporlar; hızlı ardışık tıklamalarda veya yeniden boyutlandırma olaylarında çalışan animasyon grubu temizce sonlandırılır.
- **Erişilebilirlik Uyumu:** `accessibility/stop_animations` tercihi aktifken veya başsız ortamlarda animasyon otomatik bypass edilir.

#### 2. 🌄 Splash Ekranı: Oturuma Özgü Rastgele Arazi & Meksika Dalgası (v0.2.64.39)
- **Rastgele Arazi Üretimi:** Her açılışta sol ve sağ kenar için bağımsız fraktal gürültü ve doruklarla seviye eğrileri üretilir (yapı gereği kesişmeyen 6 seviye, doruk nirengi noktaları).
- **Meksika Dalgası Hareketi:** Rastgele hız ve genlik modülasyonuyla uzantı doğrultusunda ilerleyen dalga darbeleri (60 FPS kilitli, ~3.5 ms/kare).

#### 3. 🧪 Kapsamlı Test Doğrulaması
- Tam birim test paketi ve `test_materials_thermal_toggle` (7/7 test OK) eksiksiz doğrulanmıştır.

---

### 🔒 Dosya Bütünlüğü Doğrulama (Checksums)

- **SHA-256:** `7b1e2cb5114a4bc2cddfb891d060cd1001c36600334257a7d5dc0ca87c10c051`

Terminalden doğrulamak için:
```bash
echo "7b1e2cb5114a4bc2cddfb891d060cd1001c36600334257a7d5dc0ca87c10c051  SerpentStudio-x86_64.AppImage" | sha256sum -c
```

---

### 💻 Sistem Gereksinimleri

- **İşletim Sistemi:** Linux x86_64 (Ubuntu 20.04+, Debian 11+, Fedora 36+, Arch Linux vb.)
- **Mimari:** 64-bit (x86_64)
- **Grafik:** OpenGL 2.1+ destekli ekran kartı (Yazılımsal işleme `--no-splash` bayrağıyla desteklenir)
