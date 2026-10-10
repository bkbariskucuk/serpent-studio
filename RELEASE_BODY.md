# Serpent Studio v1.2.69.49 (Alpha)

[Serpent.Studio.AppImage indir](https://github.com/bkbariskucuk/serpent-studio/releases/download/v1.2.69.49/Serpent.Studio.AppImage)

```bash
chmod +x Serpent.Studio.AppImage
./Serpent.Studio.AppImage
```

Linux x86_64; GLIBC 2.31 veya üzeri. FUSE yoksa `--appimage-extract-and-run` kullanılabilir. Python/Conda kurulumu gerekmez; Serpent hesap motoru ve lisanslı veri kütüphaneleri pakete dahil değildir.

v1.2.69.48 veya daha eski sürümden ilk geçişte çalışmalarınızı kaydedip uygulamayı kapatın ve yukarıdaki yeni AppImage'ı doğrudan indirin. Eski istemcinin güncelleyicisindeki güvenlik/kapanış düzeltmeleri ancak yeni uygulama açıldığında etkinleşir.

## Düzeltmeler

- View Panel Permissions penceresinde açık/koyu tema uyumu.
- Paketli uygulamada sunucu doğrulamasını atlayan yerel hesap ve geliştirme değişkeni yollarının kapatılması.
- Hatırlanan oturumun çevrimiçi doğrulanması, geç ağ yanıtlarına karşı token güvenliği ve çalışma kaybetmeyen oturum kilidi.
- Geometri ve ayrık pencere izinleri; `--no-splash` başlangıcında da oturum denetimi.
- Güvenli sunucu adresi ayarı ve uzak parola değiştirme desteği.
- Staging, SHA-256 doğrulaması ve atomik değiştirme kullanan güncelleme; gerçek timeout, zorunlu güncelleme ve güvenli restart davranışı.
- GitHub dosya/URL/zsync eşleşmesi; bütün ELF dosyalarında GLIBC sınırı ve hata gizlemeyen GUI smoke testi.

## Dosyalar ve doğrulama

Yalnız `Serpent.Studio.AppImage` indirmeniz yeterlidir. `Serpent.Studio` aynı dosyanın alternatif adıdır. `.zsync` dosyaları güncelleyici içindir; eski dosya adını kullanan istemciler için güncel uyumluluk haritası da yayımlanır.

İndirdiğiniz dosyanın SHA-256 özetini bu sürümün `SHA256SUMS.txt` dosyasındaki aynı adlı kayıtla karşılaştırın. `version_manifest.json` dosyası sürüm, URL, boyut ve doğrulanmış hash içerir.

## Sunucu dağıtımı hakkında

Varsayılan adres `https://serpent-studio.onrender.com` olarak korunur. Bu masaüstü yayını canlı Render veritabanını taşımış veya yönetici parolasını döndürmüş değildir. Sunucu kaynaklarındaki güvenlik düzeltmeleri ayrı dağıtım gerektirir; uzak parola değiştirme özelliği yeni sunucu endpoint'ine ihtiyaç duyar.

Mevcut ücretsiz Render SQLite verilerinin kaybolmasını önlemek için bu sürüm ayrı release dalından yayımlanır; `main` otomatik dağıtımı tetiklenmez. Canlı backend geçişi, yedekleme/secret rotasyonu ve kalıcı harici veritabanı bağlantısı doğrulanana kadar bekletilir. Ücretli kaynak oluşturulmaz.
