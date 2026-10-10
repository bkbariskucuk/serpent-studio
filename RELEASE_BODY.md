# Serpent Studio v1.2.69.48 (Alpha)

> Advanced Graphical User Interface, Interactive Core Geometry Visualizer, and Analytical Post-Processing Platform for **Serpent 2 Monte Carlo** Reactor Physics.

---

### 📥 Son Kullanıcı İçin İndirme / Download for End-Users

> [!IMPORTANT]
> **Tek İndirmeniz Gereken Dosya / Only File You Need:**  
> 👉 [**`Serpent Studio.AppImage`**](https://github.com/bkbariskucuk/serpent-studio/releases/download/v1.2.69.48/Serpent.Studio.AppImage) (~134 MB)  
> *(Alternatif doğrudan ikili: [`Serpent Studio`](https://github.com/bkbariskucuk/serpent-studio/releases/download/v1.2.69.48/Serpent.Studio))*

#### 🚀 Nasıl Çalıştırılır? / Quick Start:
1. **İzin Verin:** Dosyaya sağ tıklayın -> *Özellikler* -> *İzinler* -> *"Dosyayı program gibi çalıştırmaya izin ver"* seçeneğini işaretleyin.  
   *(Veya terminalden: `chmod +x "Serpent Studio.AppImage"`)*
2. **Çalıştırın:** Çift tıklayın veya terminalden `./"Serpent Studio.AppImage"` yazın.  
   *(Python veya herhangi bir kütüphane kurulumu gerektirmez, tamamen bağımsızdır).*

---

### 📦 Dosya Açıklamaları (Assets Guide)

| Dosya Adı | Boyut | Açıklama | Kullanıcı İndirmeli mi? |
| :--- | :--- | :--- | :--- |
| 🟢 **`Serpent Studio.AppImage`** | **~134 MB** | **Ana çalıştırılabilir uygulama paketi** | **EVET (Tek gerekli dosya)** |
| 📦 **`Serpent Studio`** | **~134 MB** | **Doğrudan bağımsız çalıştırılabilir ikili dosya** | İsteğe bağlı |
| ⚙️ `Serpent Studio.AppImage.zsync` | ~235 KB | **Delta Güncelleme Haritası:** Uygulama içi otomatik güncelleyicinin yeni sürümlerde sadece değişen parçaları indirmesini sağlar. | Otomatik (Uygulama kullanır) |
| 📋 `version_manifest.json` | ~700 B | **Sürüm Kontrol Metaverisi:** Uygulamanın menüsündeki *"Check for Updates..."* butonu için canlı sürüm bilgisi. | Otomatik (Uygulama kullanır) |

---

### 🌟 Bu Sürümde Neler Yeni? (Release Notes - v1.2.69.48)

#### 1. 🚀 Alfa Sürecine Resmi Geçiş (v1.x.x.x Alpha Release)
- Projenin olgunluk seviyesi resmi **Alfa** aşamasına taşındı ve versiyon numarasındaki majör sayaç 1 olarak güncellendi.

#### 2. 🎯 Demet (Lattice) Ayrıştırma Kararlılığı
- Ayrıştırıcı, demetleri algılarken yalnızca doğrudan `lat` komutuna bakacak şekilde sınırlandırıldı. Üstteki ayraç/bölüm yorum satırlarının (`%=====`) demet ismi sanılması kesin olarak engellendi.

#### 3. 🎨 Vektörel SVG Logo ve Sistem İkonu
- Pencere, sistem tepsisi ve masaüstü başlatıcı ikonları `QSvgRenderer` ile pürüzsüz vektörel SVG (`splash_logo.svg`) formatına bağlandı; AppImage ve sistem hicolor ikon dizinlerine ölçeklenebilir SVG formatında entegre edildi.

#### 4. 📦 "Serpent Studio" Dağıtım Paketi Adlandırması
- Dağıtım paketi adı "Serpent Studio.AppImage" yerine doğrudan son kullanıcı dostu **"Serpent Studio"** ve **"Serpent Studio.AppImage"** olarak yayımlandı.

---

### 🔒 Dosya Bütünlüğü Doğrulama (Checksums)

- **SHA-256:** `619d664953875bcad947616c1c4874cd72fdb4768639325af162c301d7721dc9`

Terminalden doğrulamak için:
```bash
echo "619d664953875bcad947616c1c4874cd72fdb4768639325af162c301d7721dc9  Serpent Studio.AppImage" | sha256sum -c
```

---

### 💻 Sistem Gereksinimleri
- **İşletim Sistemi:** Linux (Ubuntu 20.04+, Debian 11+, Fedora 34+, Arch Linux, openSUSE vb.)
- **Mimari:** x86_64 (64-bit)
- **Gerekli Kütüphaneler:** Standart glibc ve FUSE (AppImage desteği için).
