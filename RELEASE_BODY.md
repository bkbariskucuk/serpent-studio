# Serpent Studio v1.2.70.56 (Alpha)

[Serpent.Studio.AppImage indir](https://github.com/bkbariskucuk/serpent-studio/releases/download/v1.2.70.56/Serpent.Studio.AppImage)

```bash
chmod +x Serpent.Studio.AppImage
./Serpent.Studio.AppImage
```

Linux x86_64 (Ubuntu 20.04 / Debian 11 ve üzeri). FUSE bulunmayan sistemlerde `--appimage-extract-and-run` parametresiyle çalıştırılabilir. Python veya ek bağımlılık kurulumu gerektirmez.

## v1.2.70.56 ile Gelen İyileştirmeler

* **Simülasyon Hata Ekranından Konsola Işınlanma:** Simülasyon başarısız olduğunda veya sıfır dışı çıkış kodu ürettiğinde "Konsolu İncele" butonu ile kullanıcı doğrudan editör sayfasına yönlendirilir; alt konsol çekmecesi otomatik açılır, bağımsız penceredeyse öne getirilir, log filtresi hatalara odaklanır ve komut penceresi odaklanır.
* **Kalıcı Çok Segmentli Mesafe Ölçüm Aracı:** Mesafe aracı açma/kapama (toggle) modunda çalışır; ardışık tıklamalarla birden fazla segment sahnede kalıcı olarak ölçülür ve HUD bilgi kartlarıyla sunulur. Ctrl+Z / Ctrl+Y ile segmentler geri/ileri alınabilir; sağ tık aktif çizgiyi iptal eder veya segmentleri temizler.
* **Kanvas İnceleme/Kaydırma vs. Boyama Modu (Pan & Inspect vs. Paint Mode):** Kanvaslar varsayılan olarak serbest gezinme (Pan) modunda açılır. Sol tık ile sürükleme hücreleri boyamaz, açık el imleci ile serbestçe pan yapar. Başlık çubuğundaki Boyama butonu ile boyama moduna geçilerek pin ve demet yerleşimi yapılır.
* **Parametre Değişiminde Fare Tekerlek Güvenliği:** Yan paneldeki sayısal spinbox bileşenleri (`ModernSpinBox`) yalnızca metin kutusu açıkça tıklandığında ve odaklandığında fare tekerleği ile değer değiştirir; sayfa kaydırılırken değerlerin kazara bozulması engellendi.
* **Obsidian Konsol Teması ve Görünüm Ayarları:** Koyu mod konsolu derin siyah/obsidyen `#05080E` paletine geçirildi. Konsol araç çubuğuna SVG ayarlar ikonu ile canlı önizlemeli `ConsoleAppearanceDialog` eklendi; Deep Navy, Charcoal, Obsidian, Pure Light önayarları ve özel renk seçimi `QSettings` ile kalıcı kılındı.
* **Çekirdek Şekli Temizliği:** Manuel tasarım açılır listesinden `Unknown` seçeneği kaldırıldı; yalnızca tanımlanamayan bir latis içe aktarıldığında dinamik uyarı olarak gösterilip geçerli seçimde otomatik silinir.
* **Termohidrolik (TH) Gruplarında Doğal Hiyerarşik Sıralama:** Termohidrolik grupları ana demet aileleri altında toplanarak doğal alfabetik-sayısal sıralama (A1 -> A2 -> A10) ile hiyerarşik yapıya kavuşturuldu.
* **Sıfır Emoji ve Çift Dilli (i18n) Bütünlük:** Arayüz pencerelerindeki, araç çubuklarındaki ve durum bildirimlerindeki tüm emojiler temizlendi; saf vektörel SVG ikonlar ve tam Türkçe/İngilizce yerelleştirme entegre edildi.

## İndirme ve Doğrulama

Yalnızca `Serpent.Studio.AppImage` dosyasını indirmeniz yeterlidir. `.zsync` dosyaları uygulama içi otomatik güncelleyici içindir.

İndirdiğiniz dosyanın bütünlüğünü `SHA256SUMS.txt` ile karşılaştırabilirsiniz.
