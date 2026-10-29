# Serpent Studio v1.2.72.87 (Alpha)

[Serpent.Studio.AppImage indir](https://github.com/bkbariskucuk/serpent-studio/releases/download/v1.2.72.87/Serpent.Studio.AppImage)

Linux x86_64 · Debian 11 / Ubuntu 20.04 ve üzeri · GLIBC 2.31 tabanı.

```bash
chmod +x Serpent.Studio.AppImage
./Serpent.Studio.AppImage
```

FUSE bulunmayan sistemlerde `--appimage-extract-and-run` kullanılabilir. Python kurulumu gerekmez. Gerçek Git ve uzak depo işlemleri için sistemde Git bulunmalıdır; Git olmadan yerel gömülü tasarım geçmişi kullanılabilir.

## Bu sürümde

- **Dosya bazlı tasarım geçmişi:** Aynı klasördeki her `.txt` için bağımsız dallar, aşamalar, geri alma/yineleme, renkler ve uzak depo bağlantısı. Dal penceresi ek dosya sorusu çıkarmadan açılır; dosya üstteki listeden değiştirilebilir.
- **Dallanma ve birleştirme:** Seçili daldan alt dal açma, ilk aşamadan önce görünür dal bağlantısı, düğüme çift tıklayarak ilgili dala geçiş. Birleştirme önizlemesi, yan yana farklar ve çakışma uyarıları. Dal silmede birleşmemiş kayıt ve güncel revizyon kontrolleri.
- **GitLab / GitHub API:** Sunucu adresi ve kişisel erişim tokenıyla depo seçimi; birleştirme isteği/PR oluşturma, inceleme ve birleştirme; iş kaydı oluşturma, kapatma ve yeniden açma. Uzak dalı yerelde açma, Gönder ve Güncellemeleri Al butonları.
- **Düğüm notları:** Aşamalara kullanıcı notu ekleme/düzenleme/silme, notlu düğüm simgesi ve notlarda arama. Notlar yeniden açılışta korunur.
- **Görsel düzenlemeler:** Belirgin düğüm seçim halkası, dal ile aynı renkte ana panel simgesi, küçük pencerelerde kaydırılabilir detay paneli. Ortak renk seçici; görsel seçim, HEX/RGB, palet ve son renkler. Yinelenen üst araç çubuğu sürüm kontrol düğmesi kaldırıldı.
- **Kararlılık:** Kapalı dal grafiğine animasyon callback'i kaynaklı Qt çökmesi düzeltildi. Simülasyon çıktıları ve komşu tasarım dosyaları dosya sürüm işlemlerine dahil edilmez.

## Geçiş ve bağlantı bilgileri

Önceki klasör geçmişi korunur; yeni dosya geçmişi mevcut `.txt` dosyasından başlar. Dosyayı yeniden adlandırmak eski yerel geçmişi otomatik taşımaz. Dal renkleri ve düğüm notları yereldir, uzak depoya gönderilmez. Tokenlar yalnız uygulama oturumunda bellekte tutulur; uygulama yeniden açıldığında tekrar girilir.

Uzak istekler aynı dosyanın gönderilmiş dallarıyla, iş kayıtları bu dosya için uygulamadan açılan kayıtlarla sınırlıdır. API üzerinden birleştirme yerel dosyayı kendiliğinden değiştirmez; hedef dalda Güncellemeleri Al kullanılır. Canlı GitLab/GitHub hesabıyla uçtan uca doğrulama yapılmadı; REST sözleşmeleri sahte HTTP taşımasıyla, Git gönderme/alma geçici bare depolarla sınandı.

## Paket doğrulama

Dağıtım standart yayın betiği üzerinden sürüm/içerik özeti, GLIBC tabanı, temiz paket ve yalıtılmış GUI açılış kontrollerinden geçirilir. İndirilen dosyanın özetini bu release'teki `SHA256SUMS.txt` veya `SHA512SUMS.txt` ile karşılaştırabilirsiniz.
