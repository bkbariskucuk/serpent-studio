# Serpent Studio v0.2.66.44

> Advanced Graphical User Interface, Interactive Core Geometry Visualizer, and Analytical Post-Processing Platform for **Serpent 2 Monte Carlo** Reactor Physics.

---

### 📥 Son Kullanıcı İçin İndirme / Download for End-Users

> [!IMPORTANT]
> **Tek İndirmeniz Gereken Dosya / Only File You Need:**  
> 👉 [**`SerpentStudio-x86_64.AppImage`**](https://github.com/bkbariskucuk/serpent-studio/releases/download/v0.2.66.44/SerpentStudio-x86_64.AppImage) (~132 MB)

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

### 🌟 Bu Sürümde Neler Yeni? (Release Notes - v0.2.66.44)

#### 1. 🎯 Kod Editöründe "lat" Komutuna Otomatik Odaklanma (Auto-Navigate to Lattice)
- **Hassas Konumlandırma (`locate_lattice_header`):** Çekirdek (`grid_size_spin`) veya yakıt demeti (`assembly_size_spin`) ızgara boyutu değiştiğinde mini kod editörü anında ilgili `lat <id> ...` komut satırına gider, imleci konumlandırır ve satırı yumuşak bir ışıkla vurgular.
- **Halka Sarma & Dış Katman:** Core panelindeki en dıştaki demet sayısı (`core_ring_edge_spin`) değiştiğinde veya "⚡ Halkaları Sar" tıklandığında kod görünümü doğrudan ana çekirdek lattice tanımına odaklanır.
- **Modüler Include Desteği:** `navigate_to_lattice_in_code` mekanizması, include dosyası modunda çalışırken de ana dosya ve alt dosyalar arasında şeffaf navigasyon sağlar.

#### 2. 🔄 Geri Al / Yinele (Ctrl+Z & Ctrl+Y) UI Senkronizasyonu
- **Döngüsüz Çift Yönlü Senkronizasyon:** Kanvas üzerinde geri al veya yinele yapıldığında `assembly_size_spin` ("Grid (NxN):"), demet adı (`asm_name_edit`), pin adımı (`pin_pitch_spin`) ve çekirdek ızgara boyutu (`grid_size_spin`) anında matrisin gerçek durumuna eşitlenir.
- Sinyaller geçici olarak kilitlenerek (`blockSignals(True)`) gereksiz tetiklemeler ve döngüsel olay akışları engellenmiştir.

#### 3. ⚛️ Eşmerkezli Kor Geometrisi & +2 Izgara Adımları (v0.2.66 Serisi)
- **Halka Üretim Aracı:** Belirlenen dış katman demet sayısına göre merkezden dışa doğru eşmerkezli halkalar otomatik sarılır.
- **2şerli Tek Sayı Adımı:** Çekirdek ızgarası her zaman tek sayılarla (`3x3, 5x5, 7x7...`) ve `+2` adımlarıyla büyüyüp küçülür.

#### 4. 🧪 Kapsamlı Test Doğrulaması
- Tüm birim ve entegrasyon test paketi (102 test) eksiksiz doğrulanmıştır.

---

### 🔒 Dosya Bütünlüğü Doğrulama (Checksums)

- **SHA-256:** `2bd88fa2110f4ae88b48e9869f506c4cf295f76271f5330ccde6a503b1677dd6`

Terminalden doğrulamak için:
```bash
echo "2bd88fa2110f4ae88b48e9869f506c4cf295f76271f5330ccde6a503b1677dd6  SerpentStudio-x86_64.AppImage" | sha256sum -c
```

---

### 💻 Sistem Gereksinimleri
- **İşletim Sistemi:** Linux (Ubuntu 20.04+, Debian 11+, Fedora 34+, Arch Linux, openSUSE vb.)
- **Mimari:** x86_64 (64-bit)
- **Gerekli Kütüphaneler:** Standart glibc ve FUSE (AppImage desteği için).
