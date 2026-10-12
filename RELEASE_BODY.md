# Serpent Studio v1.2.69.50 (Alpha)

[Serpent.Studio.AppImage indir](https://github.com/bkbariskucuk/serpent-studio/releases/download/v1.2.69.50/Serpent.Studio.AppImage)

```bash
chmod +x Serpent.Studio.AppImage
./Serpent.Studio.AppImage
```

Linux x86_64; GLIBC 2.31 veya üzeri. FUSE yoksa `--appimage-extract-and-run` kullanılabilir. Python/Conda kurulumu gerekmez; Serpent hesap motoru ve lisanslı veri kütüphaneleri pakete dahil değildir.

## v1.2.69.50 Yenilikleri ve Güvenlik Sıkılaştırması

- **Kalıcı Neon PostgreSQL Entegrasyonu:** Render Free Web Service ephemeral dosya sistemi sınırlamasından bağımsız, kalıcı bulut veritabanı bağlandı. Sunucu güncellemelerinde veya yeniden başlatmalarda kullanıcı hesapları, oturumlar ve panel erişim kısıtlamaları (`restricted_panels`) korunur.
- **Giriş Hız Sınırlayıcı (Rate Limiting):** Kaba kuvvet (brute-force) saldırılarına karşı kayan pencere algoritmasıyla 5 dakikada 5 başarısız denemede IP geçici olarak kilitlenir (HTTP 429).
- **CORS ve Köken Sıkılaştırması:** Açık joker karakter (`*`) kaldırılarak yalnızca yetkili sunucu Host ve güvenli yerel kökenlere izin verildi.
- **Gizlilik ve Telemetri Koruması:** Kullanıcı nükleer modellerinin telemetriye gönderilmesi varsayılan olarak engellendi; açık kullanıcı onayına (`telemetry/share_scripts`) bağlandı.
- **Konteyner ve Çalışma Zamanı Güvenliği:** Konteyner root yerine `serpent` (UID 10001) kullanıcısı ile çalıştırılır, sistem CA sertifikaları (/etc/ssl/certs/ca-certificates.crt) doğrulanır.
- **render.yaml Temizliği:** Kod deposundaki düz metin yönetici parolaları ve hassas değişkenler temizlendi (`sync: false`).

## Dosyalar ve doğrulama

Yalnız `Serpent.Studio.AppImage` indirmeniz yeterlidir. `Serpent.Studio` aynı dosyanın alternatif adıdır. `.zsync` dosyaları güncelleyici içindir; eski dosya adını kullanan istemciler için güncel uyumluluk haritası da yayımlanır.

İndirdiğiniz dosyanın SHA-256 özetini bu sürümün `SHA256SUMS.txt` dosyasındaki aynı adlı kayıtla karşılaştırın. `version_manifest.json` dosyası sürüm, URL, boyut ve doğrulanmış hash içerir.

AppImage boyutu: 139.684.344 bayt. SHA-256:

```text
e15f182f3b9f05a1d59fb0e959e7bb46e616d77301cb54792a0dd0e7960ff9bd
```

Doğrulama: masaüstü ve preflight testleri 195/195 PASS, CI testleri 20/20 PASS. Paket içindeki ELF dosyalarının en yüksek GLIBC gereksinimi 2.30; standalone/AppImage GUI smoke ve metadata/zsync/ABI kapıları başarılı.
