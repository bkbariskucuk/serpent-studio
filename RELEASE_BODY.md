# Serpent Studio v0.2.52.15

> Advanced Graphical User Interface, Interactive Core Geometry Visualizer, and Analytical Post-Processing Platform for **Serpent 2 Monte Carlo** Reactor Physics.

---

### 📥 Son Kullanıcı İçin İndirme / Download for End-Users

> [!IMPORTANT]
> **Tek İndirmeniz Gereken Dosya / Only File You Need:**  
> 👉 [**`SerpentStudio-x86_64.AppImage`**](https://github.com/bkbariskucuk/serpent-studio/releases/download/v0.2.52.15/SerpentStudio-x86_64.AppImage) (~132 MB)

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

### 🌟 Bu Sürümde Neler Yeni? (Release Notes - v0.2.52.15)

#### 1. 🖱️ Linux Üst Düzey Pencere Mimarisi & Tıklama Dayanıklılığı (Top-Level Window Architecture)
- **Linux Masaüstü Entegrasyonu:** `Qt.WindowType.SplashScreen` bayrağı kaldırılarak Linux X11/Wayland pencere yöneticilerinin (GNOME Mutter, KDE KWin) pencereyi tıklanınca kapatılan geçici bir dekorasyon olarak görmesi engellendi.
- **Tıklama Güvencesi:** Pencere doğrudan standart `Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint` üst düzey uygulama penceresine dönüştürüldü. Ekrana veya arka plana tıklandığında uygulamanın kapanması tamamen engellendi.
- **Kusursuz Klavye & İmleç Etkileşimi:** Giriş alanlarına `StrongFocus` ve `Qt.FocusReason.OtherFocusReason` verilerek imleç kaybolma veya klavye odağını alamama sorunları giderildi.
- **Serbest Masaüstü Taşıma:** Pencere arka planından tutularak masaüstünde akıcı şekilde sürüklenebilir.

#### 2. 🎨 Yenilenen Zarif Güncelleme Arayüzü (Redesigned Update Dialog)
- **Hero Header:** 48x48 uygulama ikonu, sürüm durumu rozeti (`✨ NEW RELEASE` / `⚠ MANDATORY`) içeren modern kart tasarımı.
- **Akıllı Delta Tasarruf Kartı:** Sürüm karşılaştırma (`v0.2.52.15 ➜ v0.2.52.15`) ve ZSync delta optimizasyon bilgisi (`⚡ Smart Delta: ~2-5 MB indirme`).
- **Modern Koyu Tema:** `#080D1A` derin obsidyen arka plan, özelleştirilmiş şık ince kaydırma çubukları, Markdown sürüm notları okuyucu alanı.
- **Akıcı Butonlar & Canlı Yeniden Başlatma:** Güncelleme tamamlandığında yeşil `🔄 Restart Serpent Studio` butonuna dönüşerek anında yeniden başlatma imkanı.

#### 3. 🎬 Kesintisiz Açılış ve Şifre Ekranı Geçiş Animasyonu
- Yükleme (%100) tamamlandığında pencere kesinlikle kapanmaz veya kırpışmaz; aynı 640x400 çerçevede ~380 ms kübik geçişle şifre formuna evrilir.

#### 4. 🔐 Çift Kademeli Kimlik Doğrulama Sistemi
- Yetkili Yerel Kullanıcılar (`baris`, `admin`): Tuzlanmış PBKDF2-HMAC-SHA256 çevrimdışı doğrulama.
- Genel Kullanıcılar: Bulut HTTPS API doğrulama ve 30 günlük güvenli oturum ("Beni Hatırla").

---

### 🔒 Dosya Bütünlüğü Doğrulama (Checksums)

- **SHA-256:** `b4dd44f61770428e5e44c0ef253dea6af8190399520fe057cc813954de9979c8`

Terminalden doğrulamak için:
```bash
echo "b4dd44f61770428e5e44c0ef253dea6af8190399520fe057cc813954de9979c8  SerpentStudio-x86_64.AppImage" | sha256sum -c
```

---

### 💻 Sistem Gereksinimleri
- **İşletim Sistemi:** Linux x86_64 (Ubuntu 20.04+, Debian 11+, Fedora 36+, Arch Linux vb.)
- **Mimari:** 64-bit (x86_64)
- **Grafik:** OpenGL 2.1+ destekli ekran kartı (Yazılımsal işleme `--no-splash` bayrağıyla desteklenir)
