# Serpent Studio v0.2.52.14

> Advanced Graphical User Interface, Interactive Core Geometry Visualizer, and Analytical Post-Processing Platform for **Serpent 2 Monte Carlo** Reactor Physics.

---

### 📥 Son Kullanıcı İçin İndirme / Download for End-Users

> [!IMPORTANT]
> **Tek İndirmeniz Gereken Dosya / Only File You Need:**  
> 👉 [**`SerpentStudio-x86_64.AppImage`**](https://github.com/bkbariskucuk/serpent-studio/releases/download/v0.2.52.14/SerpentStudio-x86_64.AppImage) (~132 MB)

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
| ⚙️ `SerpentStudio-x86_64.AppImage.zsync` | ~280 KB | **Delta Güncelleme Haritası:** Uygulama içi otomatik güncelleyicinin yeni sürümlerde sadece değişen parçaları (~2-5 MB) indirmesini sağlar. | Otomatik (Uygulama kullanır) |
| 📋 `version_manifest.json` | 652 B | **Sürüm Kontrol Metaverisi:** Uygulamanın menüsündeki *"Check for Updates..."* butonu için canlı sürüm bilgisi. | Otomatik (Uygulama kullanır) |

---

### 🌟 Bu Sürümde Neler Yeni? (Release Notes - v0.2.52.14)

#### 1. 🎬 Kesintisiz Açılış ve Şifre Ekranı Geçiş Animasyonu (Seamless Splash-to-Auth In-Place Transition)
- **Tek Pencere Bütünlüğü:** Splash ekranındaki yükleme süreci (%100) tamamlandığında pencere kesinlikle kapanmaz, yok olmaz veya kırpışmaz.
- **Akıcı Dönüşüm Animasyonu:** Tam 640x400 pencere geometrisi ve modern topoğrafik izohips konturları korunarak ~380 ms kübik geçiş animasyonuyla şifre/giriş ekranına evrilir.
- **Dinamik Eleman Geçişleri:** İlerleme çubuğu ve görev metinleri sönerken, logo ve "Serpent Studio" marka yazısı başlık pozisyonuna yükselir; şifre formu, maskeleme butonu (şifre göster/gizle) ve canlı bulut bağlantı rozeti (🟢 Online / 🟡 Çevrimdışı Mod) belirmeye başlar.
- **Zarif Çıkış Animasyonu:** Başarılı giriş sonrasında buton yeşil "✓ Başarılı" durumuna geçer ve 200 ms yumuşak kararma animasyonunun ardından ana pencere (`MainWindow`) tam ekran açılır.

#### 2. 🔐 Çift Kademeli Kimlik Doğrulama Sistemi (Dual-Tier Authentication)
- **Yetkili Yerel Kullanıcılar (`baris`, `admin`):** Tuzlanmış PBKDF2-HMAC-SHA256 algoritmasıyla çevrimdışı doğrulanabilir (`offline_allowed: true`). İnternet bağlantısı olmasa bile anında oturum açılabilir.
- **Genel Son Kullanıcılar:** Güvenli HTTPS bulut API doğrulaması gerektirir; internet bağlantısı zorunludur.
- **Beni Hatırla:** Başarılı kimlik doğrulama sonrasında 30 günlük güvenli oturum token'ı saklanır; sonraki açılışlarda kullanıcıyı bekletmeden ana ekrana geçer.

#### 3. 🔄 Uygulama İçi Delta Güncelleme Motoru (In-App Delta Updates)
- Menü çubuğuna **Help -> Check for Updates...** penceresi eklendi.
- GitHub Releases CDN üzerinden kotasız sürüm denetimi ve ZSync delta blok indirme entegrasyonu sağlandı.
- Yeni sürüm çıktığında yüzlerce MB indirmek yerine yalnızca değişen kod blokları indirilerek bant genişliği ve zaman tasarrufu sağlanır.

#### 4. 👁️ Erişilebilirlik ve Renk Körlüğü Modları (Color Vision Deficiency)
- Menü çubuğuna **Accessibility -> Color Blindness** menüsü eklendi:
  - Default (Normal)
  - Protanopia (Kırmızı zayıflığı)
  - Deuteranopia (Yeşil zayıflığı)
  - Tritanopia (Mavi zayıflığı)
  - Achromatopsia (Tam renk körlüğü)
- PPF ve Matplotlib analiz grafiklerinde Okabe-Ito ve Tol CVD bilimsel renk paletleri devrededir.

---

### 🔒 Dosya Bütünlüğü Doğrulama (Checksums)

- **SHA-256:** `841641a43bd4d261a9b673a31dd8a5c8e62651f7985902cb5ecfab90c19afd7a`

Terminalden doğrulamak için:
```bash
echo "841641a43bd4d261a9b673a31dd8a5c8e62651f7985902cb5ecfab90c19afd7a  SerpentStudio-x86_64.AppImage" | sha256sum -c
```

---

### 💻 Sistem Gereksinimleri
- **İşletim Sistemi:** Linux x86_64 (Ubuntu 20.04+, Debian 11+, Fedora 36+, Arch Linux vb.)
- **Mimari:** 64-bit (x86_64)
- **Grafik:** OpenGL 2.1+ destekli ekran kartı (Yazılımsal işleme `--no-splash` bayrağıyla desteklenir)
