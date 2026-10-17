# Serpent Studio v1.2.71.65 (Alpha)

[Serpent.Studio.AppImage indir](https://github.com/bkbariskucuk/serpent-studio/releases/download/v1.2.71.65/Serpent.Studio.AppImage)

```bash
chmod +x Serpent.Studio.AppImage
./Serpent.Studio.AppImage
```

Linux x86_64 (Ubuntu 20.04 / Debian 11 ve üzeri). FUSE bulunmayan sistemlerde `--appimage-extract-and-run` parametresiyle çalıştırılabilir. Python veya ek bağımlılık kurulumu gerektirmez.

## v1.2.71.65 ile Gelen Yeni Yetenekler ve İyileştirmeler

* **Analysis Outputs sonsuz döngü düzeltmesi:** Analysis Outputs sayfasını sonsuz "taranıyor" döngüsüne sokan kök neden giderildi — workspace kökü her yenilemede sessizce yeniden yazılıp silindiği için dosya-sistemi olayları döngüyü kendi kendine besliyordu. Artık workspace kökü önbelleğe alındı, gerçek dosya değişikliklerinde tek bir dengeli yenileme çalışıyor.
* **Demet sihirbazında merkezden halka dolgusu:** "Halka sayısı" artık merkezi sayar: 1 yalnızca merkez hücreyi, büyüdükçe iç bölge halka halka büyür, en üst değer tüm kafesi iç pinnen doldurur; kalan dış hücreler dış piniyle kaplanır. Kare ve altıgen geometride aynı davranış; "Fill pattern" seçicisi tek başına gereksiz olduğu için kaldırıldı. Assembly Editor'a da merkezden halka dolduran "Halkalar (merkezden)" satırı eklendi.
* **Sihirbazda CRS elle yerleşimi:** Kontrol çubuğu (CRS) aktifken önizleme tuvalindeki hücrelere sol tıkla kılavuz borusu yerleştirip bırakabilirsiniz. Standart (PWR 25) veya merkez desenleri yerleşimi önden kurar; "Empty (manual placement)" ile tamamen kendiniz seçersiniz; "Guide tubes: N" sayacı canlı güncellenir. Grid boyutu değiştiğinde yerleşim otomatik yeniden hesaplanır.
* **Sihirbazda Canvas | Script görünümü:** Canlı tuvalin başlığının sağına bir anahtar geldi; "Script" modunda yalnızca o demetin Serpent söz dizimi (`lat` kartı + matrix satırları; altıgen için `pinlat_` notu) okunur halde gösterilir. Betik görünümünde yakınlaştırma araçları devre dışıdır; canvas'a dönüşte otomatik Fit uygulanır.
* **Segmented anahtarlarda akıcı kayma:** "Standard | Custom Stack" ve "Canvas | Script" anahtarlarında aktif vurgu artık yumuşak bir kayma animasyonuyla taşınır (150 ms). "Tüm Animasyonları Durdur" seçiliyken animasyon yerine anında yerleşir.
* **Pin Inspector düzenleme turu:** Pencere 1200×800'e büyütüldü; katman satırlarında ▲▼ düğmeleri ortalanıp büyütüldü, ad alanı genişletildi, uzun katman adları ("Coolant Matrix") satırda taşmadan okunur; koyu temada form arka planı ve kaydırma çubukları temayla tutarlı.
* **Splash ekranı %10 büyük ve açık azure:** Ana ekran 704×440'a büyütüldü (oran korunur; tüm öğe ve fontlar ölçekli). Koyu lacivert yerine ferah açık azure cam görünüm: safir çerçeve beyaz kırılmalı, izohips arazi açık zeminde net, tipografi koyu lacivert + safir, ilerleme çubuğu beyaz cam ray üzerinde derin safir dolgu. Login ve hata ekranları da açık şemaya uyarlandı.
* **Yılan logosu navy emaye:** Splash ambleminin beyaz pulları derin safire çekildi, pul aralıkları parlak gökyüzü tonuna alındı — uygulama ikonu ve güncelleme penceresi dahil tüm yüzeylerde açık zeminde net okunur.

## İndirme ve Doğrulama

Yalnızca `Serpent.Studio.AppImage` dosyasını indirmeniz yeterlidir. `.zsync` dosyaları uygulama içi otomatik güncelleyici içindir.

İndirdiğiniz dosyanın bütünlüğünü `SHA256SUMS.txt` ile karşılaştırabilirsiniz.
