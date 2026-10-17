# Serpent Studio v1.2.71.66 (Alpha)

[Serpent.Studio.AppImage indir](https://github.com/bkbariskucuk/serpent-studio/releases/download/v1.2.71.66/Serpent.Studio.AppImage)

```bash
chmod +x Serpent.Studio.AppImage
./Serpent.Studio.AppImage
```

Linux x86_64 (Ubuntu 20.04 / Debian 11 ve üzeri). FUSE bulunmayan sistemlerde `--appimage-extract-and-run` parametresiyle çalıştırılabilir. Python veya ek bağımlılık kurulumu gerektirmez.

## v1.2.71.66 ile Gelen Düzeltmeler

* **Syntax Preview artık yalnızca sizin eklediklerinizi yazıyor:** Önizleme, kafasından varsayılan pin, malzeme, kontrol çubuğu, detektör veya plot satırı hazırlamıyor. Malzemeler yalnızca Malzeme Tablosu'nda tanımladıklarınızdan, pinler yalnızca tanımladığınız pinler ve montajlarınızda kullandığınız stok pinlerden gelir; her kart siz ekledikçe adım adım görünür.
* **Kontrol çubukları artık isteğe bağlı:** Kontrol çubukları sekmesi kapalı başlar ve önizlemeye hiçbir şey eklemez. Etkinleştirdiğinizde standart üç banka kurulur; kapatırsanız deste kontrol çubuğu içermez.
* **Detektörler ve plotlar isteğe bağlı:** Spektrum/güç detektörleri yalnızca "Load Spectrum & Power Detectors" düğmesiyle yüklenir; birincil/ikincil plot grupları varsayılan olarak işaretsizdir. Boş bir çekirdekte konteyner geometrisi (sınır yüzeyleri, hücreler, reflektör) hiç üretilmez; termal saçılma kartları yalnızca tablonuzda tanımlı olan malzemeler için yazılır.
* **Pin oluşturma sessiz hatası düzeltildi:** "Save & Apply Pin" beklenmedik bir hatayla karşılaşırsa artık sessiz kalmıyor; "Pin Save Failed" diyaloğuyla nedeni gösterilir. Pin penceresinin kapanışında oluşabilen `_dirty` çökmesi (sunucudaki çökme raporu) giderildi; dialog kapandığı anda bellekten de temizleniyor.
* **Koyu tema liste düzeltmesi:** Kontrol çubuklarındaki demet liste kutusu, liste boşken tema değişiminde eski stilde kalıyordu; artık her iki temada da doğru renklerle güncelleniyor.

## İndirme ve Doğrulama

Yalnızca `Serpent.Studio.AppImage` dosyasını indirmeniz yeterlidir. `.zsync` dosyaları uygulama içi otomatik güncelleyici içindir.

İndirdiğiniz dosyanın bütünlüğünü `SHA256SUMS.txt` ile karşılaştırabilirsiniz.
