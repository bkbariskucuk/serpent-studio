# Serpent Studio v1.2.71.62 (Alpha)

[Serpent.Studio.AppImage indir](https://github.com/bkbariskucuk/serpent-studio/releases/download/v1.2.71.62/Serpent.Studio.AppImage)

```bash
chmod +x Serpent.Studio.AppImage
./Serpent.Studio.AppImage
```

Linux x86_64 (Ubuntu 20.04 / Debian 11 ve üzeri). FUSE bulunmayan sistemlerde `--appimage-extract-and-run` parametresiyle çalıştırılabilir. Python veya ek bağımlılık kurulumu gerektirmez.

## v1.2.71.62 ile Gelen Yeni Yetenekler ve İyileştirmeler

* **Splash İzohips Saf Dağ Yamacı Morfolojisi ve Sıfır Kasma:** Splash ekranındaki izohips arazisinden tüm yapay tepe, kapalı halka ve nirengi tepe noktacığı (spot height) öğeleri kaldırılarak dış kenara monotonik yükselen doğal dağ yamacı morfolojisine geçildi. `QPolygonF` tamponları ve kirli-bölge güncellemeleri ile render performansı optimize edildi (tam kare ort ~3 ms, 60 FPS akıcı ve kasmasız).
* **Çatallı Kanvas Çerçevesi (Forked Canvas Frame):** Assembly Canvas ve Core Canvas sağ üst köşesindeki yüzen araç ikonları (Geri Al / İleri Al / Boyama / Palet / Ölçüm / Popout) özel çatallı çerçeve (`ForkCanvasGroupBox`) ile estetik bir körfezle çevrelendi. Açık ve koyu temayla canlı senkronize çalışır.
* **Küçük Alt Chevron Göstergesi:** Ağaç görünümünde açık durumdaki aşağı bakan chevron simgeleri zarif bir oranda küçültüldü (%25).
* **Analiz Çıktıları Sıfır Kasma (Dirty-Region Overlay):** Analiz Çıktıları sayfasındaki "Scanning Outputs..." reaktör döndürük yükleme animasyonunda kirli-bölge boyama uygulanarak X11/Wayland üzerinde arka plan yırtılması ve kasma engellendi; "Tüm Animasyonları Durdur" erişilebilirlik tercihiyle tam uyumlu hale getirildi.

## İndirme ve Doğrulama

Yalnızca `Serpent.Studio.AppImage` dosyasını indirmeniz yeterlidir. `.zsync` dosyaları uygulama içi otomatik güncelleyici içindir.

İndirdiğiniz dosyanın bütünlüğünü `SHA256SUMS.txt` ile karşılaştırabilirsiniz.
