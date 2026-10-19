# Serpent Studio v1.2.71.76 (Alpha)

[Serpent.Studio.AppImage indir](https://github.com/bkbariskucuk/serpent-studio/releases/download/v1.2.71.76/Serpent.Studio.AppImage)

```bash
chmod +x Serpent.Studio.AppImage
./Serpent.Studio.AppImage
```

Linux x86_64 (Ubuntu 20.04 / Debian 11 ve üzeri). FUSE bulunmayan sistemlerde `--appimage-extract-and-run` parametresiyle çalıştırılabilir. Python veya ek bağımlılık kurulumu gerektirmez.

## v1.2.71.76 ile Gelen Yenilikler ve Düzeltmeler

* **Letarji Grafiği Açılış Akıcılığı:**
  * Grafik kurulumu sırasında kuyruklanan gereksiz tam canvas çizimleri kaldırıldı; animasyonun ilk kareleri artık 50–70 ms'lik çizimlerle kesilmiyor.
  * Animasyon başladıktan sonra kuyruklanan ikinci tam çizim engellendi; giriş animasyonunun ilk blit'i grafiği doğrudan boyuyor.
  * Animasyon bitişinde constrained layout yeniden hesaplanmıyor; son blit karesi hover arka planı olarak yeniden kullanılıyor. Bitişteki ~100 ms'lik tam çizim ve donma kaldırıldı.
  * Spektrum bilgi paneli, splitter boyutları ve sayfa geçişi grafik render'ından önce sabitleniyor; animasyon sırasında canvas'ın yeniden boyutlanması ve ~155 ms'lik ara yerleşim çizimi önleniyor.
  * Gerçek 70 binlik veride ilk kare aralıkları 55.9 / 70.6 ms'den 2.0 / 17.7 ms'ye indi; en kötü kare 17.7 ms. 500/1000/2000 binlik yoğun serilerde kare süresi 15.9–17.5 ms aralığında kaldı.

* **Spektrum Hesabı ve Literatür Uyumu:**
  * Serpent'in varsayılan enerji-bölmeli detektör çıktısının bın integrali olduğu doğrulandı; `φ(u) = ΔΦ/Δu`, `Δu = ln(E_max/E_min)` ve bağıl hata korunumu doğru.
  * Serpent `DET*E` üçüncü sütunundaki aritmetik `EMID` yerine letarji bın merkezi `u_i = (u_min + u_max)/2` kullanılmaya başlandı. 70 eşit-letarji bınlı ızgarada eski 0.0203 u'luk yatay kayma giderildi.
  * 0.625 eV ve 100 keV grup sınırlarının bın sınırlarına denk gelmediği durumlar için grup paylarının bın-nicelemeli olduğu dokümante edildi; tüm bin ataması ile sınırda kesirli paylaştırma arasındaki fark 0.4 yüzde puanının altında.
  * `dt -2` / `dt -3` kullanan detektörlerde Serpent'in sonucu zaten genişliğe böldüğü, uygulamanın ayrıca `Δu`'ya bölerek çift normalizasyon yapacağı konusunda sözdizimi rehberi, matematik sekmesi ve analiz tanılarına uyarı eklendi. Mevcut varsayılan integral çıktısında sonuçlar doğru kalır.
  * Eksen etiketlerinde `Neutron Energy (eV) (eV)` gibi birim yinelemeleri giderildi.

* **Test Doğrulaması:** Enerji spektrumu ve animasyon paketi 19/19 OK; 19 analiz/grafik modülünde 106/107 OK (tek hata bilinen heatmap/constrained-layout hatası); TR/EN, açık/koyu, hover/replay ve gerçek 70-bin verisiyle görsel doğrulama yapıldı.

## İndirme ve Doğrulama

Yalnızca `Serpent.Studio.AppImage` dosyasını indirmeniz yeterlidir. `.zsync` dosyaları uygulama içi otomatik güncelleyici içindir.

İndirdiğiniz dosyanın bütünlüğünü `SHA256SUMS.txt` ile karşılaştırabilirsiniz.
