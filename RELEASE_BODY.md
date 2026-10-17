# Serpent Studio v1.2.71.67 (Alpha)

[Serpent.Studio.AppImage indir](https://github.com/bkbariskucuk/serpent-studio/releases/download/v1.2.71.67/Serpent.Studio.AppImage)

```bash
chmod +x Serpent.Studio.AppImage
./Serpent.Studio.AppImage
```

Linux x86_64 (Ubuntu 20.04 / Debian 11 ve üzeri). FUSE bulunmayan sistemlerde `--appimage-extract-and-run` parametresiyle çalıştırılabilir. Python veya ek bağımlılık kurulumu gerektirmez.

## v1.2.71.67 ile Gelen Düzeltmeler

* **Splash ekranı paketlenmiş sürümde de akıcı:** İzohips animasyonları derlenmiş sürümde takılabiliyordu — başlangıç ekranını ayrı bir süreçte çalıştıran mekanizma paketlenmiş uygulamada devreye giremiyordu. Artık başlangıç ekranı, paketlenmiş sürümde de kendi bağımsız sürecinde çalışıyor; arka plandaki yükleme işleri animasyonu etkilemiyor.
* **Kapanışta oluşabilen çökme giderildi:** Uygulama kapatılırken bazı oturumlarda oluşan çökme kayıtlarının (SEGV) kök nedeni, Python kapanışındaki nesne temizliğiydi. Kapanış artık ayarlar ve kayıtlar diske güvenle yazıldıktan sonra bu adım atlanarak yapılıyor — çökme yok, veri kaybı yok.
* **Başlangıç ekranı kapatma davranışı sağlamlaştırıldı:** Başlangıç penceresindeki kapatma akışında yalnızca uç durumlarda ortaya çıkabilecek gizli bir hata tuzu kapatıldı.

## İndirme ve Doğrulama

Yalnızca `Serpent.Studio.AppImage` dosyasını indirmeniz yeterlidir. `.zsync` dosyaları uygulama içi otomatik güncelleyici içindir.

İndirdiğiniz dosyanın bütünlüğünü `SHA256SUMS.txt` ile karşılaştırabilirsiniz.
