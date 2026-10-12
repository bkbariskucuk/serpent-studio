# Serpent Studio v1.2.69.51 (Alpha)

[Serpent.Studio.AppImage indir](https://github.com/bkbariskucuk/serpent-studio/releases/download/v1.2.69.51/Serpent.Studio.AppImage)

```bash
chmod +x Serpent.Studio.AppImage
./Serpent.Studio.AppImage
```

Linux x86_64 (Ubuntu 20.04 / Debian 11 ve üzeri). FUSE bulunmayan sistemlerde `--appimage-extract-and-run` parametresiyle çalıştırılabilir. Python veya ek bağımlılık kurulumu gerektirmez.

## v1.2.69.51 ile Gelen İyileştirmeler

* **Analiz Grafikleri Tam Dil Uyumu (TR/EN):** Tüm reaktör fiziği analiz çıktıları (k-etkin, PPF, eksenel akı profili, dönüşüm oranı, letarji/enerji spektrumu, gecikmiş nötron öncüleri, tükenme ve kinetik analizleri) başlık, eksen, referans çizgisi ve göstergeleriyle çalışma zamanında çift dilli hale getirildi.
* **Dinamik Açılır Kutu ve Navigasyon Güncellemesi:** Dil değiştirildiğinde grafik açılır menüleri, eksen seçimleri ve PPF çekirdek haritası seyir kontrolleri seçili veriyi kaybetmeden anında yeni dilde güncellenir.
* **Fizik Metrikleri ve Çözücü Göstergeleri:** Özet metrikler tablosundaki 50'den fazla reaktör fiziği değişken adı ve nötron spektrum tanı göstergeleri eksiksiz yerelleştirildi.
* **Kararlılık ve Ölçek Doğrulaması:** Grafik ölçek rozetleri ve çift dilli bileşenler için kapsamlı test doğrulaması tamamlandı.

## İndirme ve Doğrulama

Yalnızca `Serpent.Studio.AppImage` dosyasını indirmeniz yeterlidir. `.zsync` dosyaları uygulama içi otomatik güncelleyici içindir.

İndirdiğiniz dosyanın bütünlüğünü `SHA256SUMS.txt` ile karşılaştırabilirsiniz.
