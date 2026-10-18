# Serpent Studio v1.2.71.75 (Alpha)

[Serpent.Studio.AppImage indir](https://github.com/bkbariskucuk/serpent-studio/releases/download/v1.2.71.75/Serpent.Studio.AppImage)

```bash
chmod +x Serpent.Studio.AppImage
./Serpent.Studio.AppImage
```

Linux x86_64 (Ubuntu 20.04 / Debian 11 ve üzeri). FUSE bulunmayan sistemlerde `--appimage-extract-and-run` parametresiyle çalıştırılabilir. Python veya ek bağımlılık kurulumu gerektirmez.

## v1.2.71.75 ile Gelen Yenilikler ve Düzeltmeler

* **Otomatik Güncelleme Bildirimi (Toast):**
  * Açılışta arka planda yapılan otomatik güncelleme denetimi güncelleme bulduğunda artık modal pencere dayatılmaz; sağ alt köşede tema duyarlı, 12 saniye sonra kendiliğinden kapanan bir bildirim gösterilir.
  * Bildirime tıklamak güncelleme penceresini açar; elle yapılan kontrollerde ve zorunlu güncellemelerde önceki modal davranış aynen korunur.
  * Aynı sürüm için bildirim oturumlar arası yalnızca bir kez gösterilir (sürüm hafızası).

* **Sihirbazlarda Ctrl+Z / Ctrl+Y / Ctrl+Shift+Z Onarımı (New Assembly & New Core):**
  * Ctrl+Y artık her odak durumunda çalışır; çakışan (ambiguous) Ctrl+Shift+Z bağlaması düzeltildi.
  * Spinbox içine değer girildikten sonra da geri/ileri alma eksiksiz çalışır; spinbox kısayol yakalaması sihirbaz geçmişine bağlandı.
  * Metin kutuları (`QLineEdit`, `QPlainTextEdit`, `QTextEdit`) aktifken kısayollar yerel metin düzenleyicisine devredilmeye devam eder.

## İndirme ve Doğrulama

Yalnızca `Serpent.Studio.AppImage` dosyasını indirmeniz yeterlidir. `.zsync` dosyaları uygulama içi otomatik güncelleyici içindir.

İndirdiğiniz dosyanın bütünlüğünü `SHA256SUMS.txt` ile karşılaştırabilirsiniz.
