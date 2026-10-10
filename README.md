# Serpent Studio

[Latest release](https://github.com/bkbariskucuk/serpent-studio/releases/latest) · Linux x86_64 · Nuitka / AppImage

Serpent 2 Monte Carlo hesaplamaları için grafiksel arayüz, geometri görüntüleme ve sonuç analiz platformu.

## İndirme ve çalıştırma

[Serpent.Studio.AppImage indir](https://github.com/bkbariskucuk/serpent-studio/releases/latest/download/Serpent.Studio.AppImage). GitHub dosya adında boşluk **yoktur**; eski `%20` bağlantılarını kullanmayın.

```bash
curl -fL -o Serpent.Studio.AppImage \
  https://github.com/bkbariskucuk/serpent-studio/releases/latest/download/Serpent.Studio.AppImage
chmod +x Serpent.Studio.AppImage
./Serpent.Studio.AppImage
```

Python/Conda kurulumu gerekmez. Sistemde FUSE bulunmuyorsa:

```bash
./Serpent.Studio.AppImage --appimage-extract-and-run
```

İndirdiğiniz sürümün release sayfasındaki `SHA256SUMS.txt` dosyasıyla özeti karşılaştırın. Sürüm değişirken farklı release'lerden dosya karışmasını önlemek için doğrulama sırasında aynı sürüm etiketinin bağlantılarını kullanın.

## Dağıtım dosyaları

| Dosya | İşlev |
| --- | --- |
| `Serpent.Studio.AppImage` | Ana taşınabilir uygulama; kullanıcı için gerekli dosya. |
| `Serpent.Studio` | Aynı AppImage'ın alternatif adı; ayrı bir native binary değildir. |
| `Serpent.Studio.AppImage.zsync` | Güncel AppImage için delta güncelleme haritası. |
| `SerpentStudio-x86_64.AppImage.zsync` | Eski istemcilerin keşfi için aynı güncel haritanın uyumluluk kopyası. |
| `version_manifest.json` | Gerçek asset URL'leri, sürüm, SHA256 ve dosya boyutu. |
| `SHA256SUMS.txt`, `SHA512SUMS.txt` | Uygulama, haritalar ve manifest için sağlama toplamları. |

## Hesap erişimi ve güncellemeler

Uygulamayı indirmek bir hesap oluşturmaz. Yeni kullanıcı için yönetici tarafından açık hesap yetkilendirmesi gerekir. Üretim paketi yalnız sunucuda doğrulanan hesapları kabul eder; yerel hesap dosyası, geliştirme değişkenleri veya hatırlanan eski oturum bu denetimi atlamaz. Üretim paketine geliştiricinin hesap veritabanı veya parola özeti eklenmez. Sunucu erişilemiyorsa bağlantı hatası, yanlış parola olarak yorumlanmamalıdır. Yerel/offline hesap desteği yalnız geliştirme kaynak çalıştırmasına aittir.

Varsayılan sunucu `https://serpent-studio.onrender.com` olarak korunur. Giriş penceresindeki **Server…** seçeneği başka bir yetkili HTTPS adresi ayarlayabilir; HTTP yalnız aynı bilgisayardaki loopback test sunucuları için kabul edilir. Adres değişirse yeniden giriş gerekir. Ağ bağlantısı veya oturum yetkisi kaybolursa açık çalışma silinmeden arayüz kilitlenir.

**Help → Check for Updates…** üzerinden sürüm kontrol edilir. Delta indirme boyutu değişen bloklara bağlıdır; sabit “2–5 MB” garantisi yoktur. Delta araçları bulunamaz veya güvenli doğrulama başarısız olursa güncelleme akışı tam indirmeye/manuel indirmeye yönlendirebilir. Yeni dosya doğrulanmadan çalışan sürümün yerini almamalıdır.

v1.2.69.48 ve önceki istemcilerden ilk geçişte çalışma dosyalarınızı kaydedip uygulamayı kapatarak yeni AppImage'ı doğrudan indirin. Yeni updater'ın güvenli staging/restart kuralları eski çalışmakta olan istemciyi geriye dönük değiştirmez.

## Linux uyumluluğu

Yeni üretim hattının hedefi **x86_64, GLIBC 2.31 ve sonrası**dır: Ubuntu 20.04 / Debian 11 tabanı. Derleme, Debian 11 container'ında yapılır; dağıtımdaki bütün ELF dosyalarının GLIBC gereksinimleri doğrulanır ve container içinde GUI hazır-olma testi çalıştırılır. Bu kapıları geçmemiş host-native derleme eski Linux desteğiyle yayımlanamaz.

Önemli: Daha önce host ortamında oluşturulan **v1.2.69.48** paketi GLIBC 2.38 gerektiriyordu; Ubuntu 20.04/Debian 11 desteği o dosya için geçerli değildir. Eski bir paketin yalnızca adını veya manifestini değiştirmek uyumluluğunu düzeltmez; baseline container'da yeniden derlenmiş sürüm gerekir.

Masaüstü Qt/OpenGL sistem kütüphaneleri ve grafik sürücüleri ayrıca uyumlu olmalıdır. `--no-splash` yalnız açılış animasyonunu kapatır; yazılımsal grafik modu değildir. Serpent hesap motoru ve lisanslı nükleer veri kütüphaneleri AppImage ile dağıtılmaz.

## Bakımcı: doğrulanan build ve release

Bu adımlar özel uygulama kaynaklarının mevcut olduğu bakımcı checkout'u içindir. Docker, Python 3, binutils (`readelf`), `unsquashfs`, `desktop-file-validate`, `rsync`, Git ve kimliği doğrulanmış `gh` gerekir. İncelenmiş `appimagetool` ve gerekiyorsa güncelleme aracı `packaging/build/tools/` altında sağlanmalıdır.

```bash
# Yalnız Dockerfile + requirements içeren geçici context; kullanıcı verisi gönderilmez.
bash packaging/build/prepare_build_image.sh
# Kaynaklar önceden incelendiyse aynı checkout'tan build; masaüstüne kurulum yapmaz.
./sync_and_build.sh --no-sync
python3 -B -m unittest discover -s packaging/ci -p 'test_*.py'
./packaging/ci/validate_distribution.sh
# VERSION/release notes önce incelenmiş ve commit edilmiş olmalı.
./publish_release.sh v1.2.69.49 'Sürüm notları' --skip-build
```

Sürüm örnektir; mevcut etiket yeniden kullanılamaz. Yayın betiği hazır paketin gömülü VERSION ve binary SHA256'sını kontrol eder. `--skip-build` eski dosyayı yeni sürüm diye etiketlemez. Önce draft ve bütün asset'ler oluşturulur, GitHub SHA256'ları doğrulanır, ardından release yayımlanır; raw manifest en son güncellenir. Hata olursa betik başarısız döner ve draft inceleme için kalır; otomatik force-tag/overwrite yapılmaz.

Canlı sunucunun `main` auto-deploy akışını tetiklememek için önceden incelenmiş bir release branch'ine geçip `SERPENT_RELEASE_BRANCH=release/v1.2.69.49 ./publish_release.sh …` kullanılabilir. Betik checkout ile belirtilen branch'in eşleşmesini zorunlu tutar; bu modda **main'e push ve raw fallback manifest değişikliği yapılmaz**. Release asset manifest'i birincil güncelleme kaynağıdır. Branch oluşturma/geçiş işlemi otomatik yapılmaz.

`--native` yalnız açık opt-in seçeneğidir; GLIBC kapısı yine zorunludur. `--install` verilmedikçe build kullanıcının masaüstü/terminal kısayollarını değiştirmez. Bağımlılık imajını sabitlemek için `SERPENT_BUILD_BASE_IMAGE=python:3.12-bullseye@sha256:…` ile incelenmiş digest kullanılabilir.

## Sunucu dağıtımı ve veri güvenliği

Render ücretsiz web hizmetinin dosya sistemi geçicidir; SQLite hesap/verileri yeniden dağıtım, yeniden başlama veya uyku sonrasında kaybolabilir. Ücretsiz Render Postgres da 30 günle sınırlıdır ve kalıcı çözüm olarak kabul edilmez. [Render ücretsiz plan sınırları](https://render.com/docs/free).

`render.yaml` ücretsiz web planını korur, hiçbir ücretli disk/veritabanı oluşturmaz ve otomatik dağıtımı kapalı tanımlar. Kalıcılık için `SERPENT_DATABASE_URL` ile harici PostgreSQL yapılandırılmalıdır. Bu adres ve yeni `SERPENT_ADMIN_PASS` yalnız Render'ın secret/environment ayarına girilir; Git'e, release notuna veya istemci paketine yazılmaz.

Mevcut canlı servis bu dosyanın yerelde değiştirilmesiyle güncellenmiş olmaz. Mevcut veriler kurtarılmadan yeniden dağıtım yapılmamalıdır. Açığa çıkmış eski yönetici parolası canlı ortamda ayrıca döndürülmelidir; Git geçmişinden metni kaldırmak tek başına yeterli değildir. Yeni backend doğrulanmadan yalnız masaüstü release dalı yayımlanabilir; `main` otomatik dağıtımı tetiklenmez.

## Lisans

Serpent Studio tescilli yazılımdır. Tüm hakları saklıdır. Serpent, VTT tarafından geliştirilen bağımsız bir hesaplama kodudur; bu arayüzün VTT ile resmi ortaklığı bulunmamaktadır.
