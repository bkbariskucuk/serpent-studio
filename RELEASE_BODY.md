# Serpent Studio v1.2.71.64 (Alpha)

[Serpent.Studio.AppImage indir](https://github.com/bkbariskucuk/serpent-studio/releases/download/v1.2.71.64/Serpent.Studio.AppImage)

```bash
chmod +x Serpent.Studio.AppImage
./Serpent.Studio.AppImage
```

Linux x86_64 (Ubuntu 20.04 / Debian 11 ve üzeri). FUSE bulunmayan sistemlerde `--appimage-extract-and-run` parametresiyle çalıştırılabilir. Python veya ek bağımlılık kurulumu gerektirmez.

## v1.2.71.64 ile Gelen Yeni Yetenekler ve İyileştirmeler

* **Bütünsel Yeni Demet Sihirbazı (New Assembly Wizard):** `+ New Assembly` tıklandığında açılan tek satırlık ID kutusu yerine, iki sütunlu modern bir sihirbaz penceresi (`NewAssemblyWizardDialog`) getirildi. Sol tarafta tüm yapılandırma ayarları, sağ tarafta ise gerçek canlı Assembly Canvas yer alır.
* **En Dıştaki Halka Sayısı ve Pin Dolgu Seçimi:** Grid boyutu N×N dikkate alınarak dinamik olarak `0` ile `(N-1)//2` arasında sınırlandırılan "En Dıştaki Halka Sayısı" spinbox'ı eklendi. Halka sayısı 0 iken tek düze iç dolgu pini kullanılır; >0 iken dıştaki katmanlar tanımlı dış halka piniyle (renk ikonu ve adıyla) doldurulur. Altıgen ve kare geometride istenen yakıt/pin dolgusu kolaylıkla yapılandırılabilir.
* **Gerçek Canlı Assembly Canvas:** Sağ taraftaki önizleme tuvali, ana penceredeki Assembly Canvas ile birebir konsantrik pin katmanları (yakıt peleti, boşluk, gömlek, soğutucu malzeme renkleri), lat 1 kare, lat 2 altıgen X ve lat 3 altıgen Y geometri çekirdeği, kılavuz tüpü simgeleri, mouse tekerleğiyle yakınlaştırma/uzaklaştırma, sürükleme (pan) ve "Fit View" butonlarıyla yüksek çözünürlüklü anti-aliased olarak çizilir. Sol taraftaki her ayar değişiminde anında dinamik olarak güncellenir.
* **Kontrol Çubuğu (CRS) Sekmesi ile Dinamik Entegrasyon:** CRS sekmesinde tanımlı bankaların özellikleri (`ControlRodSystem.banks`) otomatik olarak çekilir. Banka seçildiğinde absorber tipi (B4C, AIC, vb.), gömlek malzemesi (SS304), absorber/gömlek yarıçapları ve kılavuz tüpü pini anlık bilgilendirme kartında gösterilir; standart PWR 25-thimble simetrik dağılımı ile kılavuz tüpleri yerleştirilir. Demet oluşturulduğunda CRS bankasıyla otomatik ilişkilendirilir.
* **Tam Düzenleme Desteği:** Pencerede demet tanımlandıktan sonra kaydedilen tüm parametreler Assembly Editor içinde kullanıcıya düzenlemeye sunulur; demet adı `assembly_names` ve UI editörüne işlenir, Serpent girdi metni anında üretilir.

## İndirme ve Doğrulama

Yalnızca `Serpent.Studio.AppImage` dosyasını indirmeniz yeterlidir. `.zsync` dosyaları uygulama içi otomatik güncelleyici içindir.

İndirdiğiniz dosyanın bütünlüğünü `SHA256SUMS.txt` ile karşılaştırabilirsiniz.
