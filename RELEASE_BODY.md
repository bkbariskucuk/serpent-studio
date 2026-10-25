# Serpent Studio v1.2.72.80 (Alpha)

[Serpent.Studio.AppImage indir](https://github.com/bkbariskucuk/serpent-studio/releases/download/v1.2.72.80/Serpent.Studio.AppImage)

```bash
chmod +x Serpent.Studio.AppImage
./Serpent.Studio.AppImage
```

Linux x86_64 (Ubuntu 20.04 / Debian 11 ve üzeri). FUSE bulunmayan sistemlerde `--appimage-extract-and-run` parametresiyle çalıştırılabilir. Python veya ek bağımlılık kurulumu gerektirmez.

## v1.2.72.80 ile Gelen Yenilikler ve Düzeltmeler

* **Dosya Seçim Penceresi Vektörel Araç Çubuğu ve İkon Teması Senkronizasyonu (`ui/theme.py`, `ui/import_file_dialog.py`):**
  * Koyu sistem temalarında (KDE Breeze-Dark vb.) açık modda beyaz butonlar üzerinde oluşan "hayalet ikon" kontrast sorunu giderildi.
  * `sync_system_icon_theme` ile Qt sistem ikon teması uygulamanın anlık açık/koyu mod durumuna göre otomatik senkronize edilir; Look in klasör ikonu, dosya listeleri ve Hızlı Konumlar açık modda koyu/renkli, koyu modda açık gliflere uyarlandı.
  * Üst araç çubuğu butonları (`backButton`, `forwardButton`, `toParentButton`, `newFolderButton`, `listModeButton`, `detailModeButton`) kristal netliğinde saf vektörel SVG ikonlara bağlandı; normal, disabled ve aktif durumlar için bağımsız HiDPI ölçekleri oluşturuldu.
  * 24×24 px ergonomik boyut, 6 px köşe radyusu ve durum bazlı stil harmonizasyonu sağlandı.

* **Genişletilmiş Ergonomik Dosya Seçim Penceresi (`StudioFileDialog` - `ui/import_file_dialog.py`):**
  * 960×600 px geniş standart pencere boyutu ve 210 px sabit asgari sol kenar çubuğu genişliği ile isim kesilmeleri ("Masaüstü" -> "Ma...") engellendi.
  * Sol panele saf SVG vektör ikonlu hızlı erişim butonları yerleştirildi: 🖥️ Masaüstü / Desktop, 📁 Çalışma Alanı / Workspace, 🏠 Ev Dizini / Home ve ⚛️ Nükleer Veri / Nuclear Data.

* **Windows Sürücü Arama Sihirbazı Formatında Kütüphane Konumlandırma ve Doğrulama (`ui/library_locator_dialog.py`, `core/discovery.py`):**
  * Sezgisel "Kütüphaneleri Otomatik Olarak Ara" ve "Bilgisayarıma Gözat" modülleri eklendi.
  * Doğrudan yol düzenleme metin kutuları (`QLineEdit`), `[Gözat...]` ve anlık `[Doğrula]` butonları entegre edildi.
  * Zengin doğrulama penceresi (`LibraryValidationDialog`) ile izotop sayısı, dosya boyutu, nükleer sürüm ve ZAID sözdizimi derinlemesine doğrulanıp rozetlerle sunulur.

* **Operation Ayarları ve Backend Tanı Ekranında Tam İki Dilli (TR/EN) Yerelleştirme ve SVG İkon Standardizasyonu (`core/i18n.py`, `ui/theme.py`, `ui/backend_diagnostics_dialog.py`):**
  * Tofu (`▯`) kutucuk oluşturan unicode emojiler temizlendi; saf vektörel SVG ikonlar standartlaştırıldı.
  * Backend tanı penceresinde kütüphaneler için disk üzerindeki tam yolları gösteren bağımsız kartlar geliştirildi.
  * Operation sekmesi ve tanı ekranı %100 eksiksiz Türkçe ve İngilizce dil desteğine kavuşturuldu.

## İndirme ve Doğrulama

Yalnızca `Serpent.Studio.AppImage` dosyasını indirmeniz yeterlidir. `.zsync` dosyaları uygulama içi otomatik güncelleyici içindir.

İndirdiğiniz dosyanın bütünlüğünü `SHA256SUMS.txt` ile karşılaştırabilirsiniz.
