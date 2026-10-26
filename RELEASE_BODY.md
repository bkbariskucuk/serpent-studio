# Serpent Studio v1.2.72.81 (Alpha)

[Serpent.Studio.AppImage indir](https://github.com/bkbariskucuk/serpent-studio/releases/download/v1.2.72.81/Serpent.Studio.AppImage)

```bash
chmod +x Serpent.Studio.AppImage
./Serpent.Studio.AppImage
```

Linux x86_64 (Ubuntu 20.04 / Debian 11 ve üzeri). FUSE bulunmayan sistemlerde `--appimage-extract-and-run` parametresiyle çalıştırılabilir. Python veya ek bağımlılık kurulumu gerektirmez.

## v1.2.72.81 ile Gelen Yenilikler ve Düzeltmeler

* **Çekirdek Matrisi ve Latisinde Dinamik Su / Soğutucu Pini Algoritması (`ui/main_window.py`):**
  * Sabit/ezbere pin numaraları (0, 4, 99) arama davranışı tamamen kaldırıldı.
  * İki aşamalı dinamik tespit: Malzeme tanımlarından (`mat ...`) soğutucu malzeme tespit edilir; ana çekirdek latisi (`lat 999` / `core_matrix`) taranarak yakıt demetleri (`custom_assemblies`) dışında kullanılan gerçek soğutucu pini izole edilir.
  * `smart_validasyon` dosyasında demet içi kılavuz tüpleri (`4`) ve zehir çubukları (`7`) elenerek yalnızca ana latis soğutucusu (`99`) çekirdek paletine eklenir.
  * Tuval boyama, su hücresi atama ve dış halka su temizleme butonları tespit edilen dinamik soğutucu piniyle senkronize çalışır.

* **Alt Paneller Çoklu Pop-out (Both Popout) Araç Çubuğu Senkronizasyonu (`ui/main_window.py`, `ui/workflow_dialogs.py`):**
  * Konsol ve Preflight panelleri birlikte ayrıldığında (`DetachedBottomNotebookWindow`) konsol araç çubuğunun (Clear, Copy, Find, Settings, filtre çipleri) kaybolması kusuru giderildi.
  * Ayrılmış çoklu sekme penceresinde Console sekmesinde köşe bileşeni olarak `cmd_toolbar`, Preflight Results aktifken `btn_dock_back` dinamik olarak atanır.
  * Konsol başlığı ile log metni arasındaki 39 px'lik görünmez dikey boşluk sıfırlandı; alt panel daraltıldığında dahi log yazılarının ezilmesi önlendi.

* **Çekirdek Yükseklik ve Adım Kararlılığı (`core/input_parser.py`, `ui/main_window.py`):**
  * Kontrol çubuğu kaydırıcısı oynatıldığında veya Ctrl+S yapıldığında kontrol çubuğu uç düzlemlerinin (`pz`) çekirdek eksenel boyutunu şişirmesi ve kullanıcının girdiği `core_height_spin` değerini ezmesi engellendi.
  * `_user_set_core_pitch` bayrağı ile kullanıcının manuel girdiği `pitch_spin` adımı koruma altına alındı.

* **Preflight Paneli Dikey Alan Tasarrufu ve Kategori Filtreleme (`ui/preflight_panel.py`):**
  * Özet rozetleri ve "Preflight" başlığı tek satıra indirgendi; başlık yerine tıklanabilir checkable filtre çipleri (`Error`, `Warning`, `Info`, `Passed`) yerleştirildi. Ağaç görünümüne dikeyde geniş alan kazandırıldı.

* **Kontrol Çubuğu Dinamik Malzemeleri ve Reflektör Senkronizasyonu (`ui/control_rods.py`, `ui/main_window.py`):**
  * Kontrol Çubuğu sekmesindeki soğurucu malzeme listesi projedeki malzeme tablosundan (`mat_table`) dinamik olarak beslendi.
  * Core Editor reflektör seçimi malzeme tablosuyla iki yönlü bağlandı; reflektör seçildiğinde malzeme listesine otomatik eklenir, değiştirildiğinde eskisi güncellenir.
  * Altıgen sınır açısı (Hex Angle) kilidi açılarak 0° (`hexxc`) ve 30° (`hexyc`) yönelimleri çift yönlü senkronize edildi.

## İndirme ve Doğrulama

Yalnızca `Serpent.Studio.AppImage` dosyasını indirmeniz yeterlidir. `.zsync` dosyaları uygulama içi otomatik güncelleyici içindir.

İndirdiğiniz dosyanın bütünlüğünü `SHA256SUMS.txt` ile karşılaştırabilirsiniz.
