# Serpent Studio

[En Güncel Sürüm](https://github.com/bkbariskucuk/serpent-studio/releases/latest) · Linux x86_64 · AppImage

Serpent 2 Monte Carlo nötronik hesaplamaları için modern grafiksel kullanıcı arayüzü, gelişmiş reaktör geometri görselleştirme ve simülasyon analiz platformu.

---

## İndirme ve Hızlı Başlangıç

En güncel sürümü [GitHub Releases](https://github.com/bkbariskucuk/serpent-studio/releases/latest) sayfasından veya terminalden tek komutla indirebilirsiniz:

```bash
# AppImage dosyasını indirin
curl -fL -o Serpent.Studio.AppImage \
  https://github.com/bkbariskucuk/serpent-studio/releases/latest/download/Serpent.Studio.AppImage

# Çalıştırma yetkisi verin ve başlatın
chmod +x Serpent.Studio.AppImage
./Serpent.Studio.AppImage
```

> **İpucu:** Sisteminizde FUSE yapılandırması bulunmuyorsa uygulamayı doğrudan şu komutla çalıştırabilirsiniz:
> ```bash
> ./Serpent.Studio.AppImage --appimage-extract-and-run
> ```

---

## Öne Çıkan Yetenekler

* **Reaktör Çekirdek ve Geometri Görselleştirme:** Altıgen ve kare kafes yapılarında çekirdek, yakıt demeti ve pin düzeyinde etkileşimli görselleştirme.
* **Serpent Girdi Düzenleyici & Doğrulama:** Sözdizimi vurgulama, gerçek zamanlı hata kontrolü ve otomatik tamamlama.
* **Kapsamlı Analiz ve Grafik Çıktıları:** Akı (flux) dağılımları, güç pik faktörleri (PPF), yanma (depletion) ve reaktivite katsayısı görselleştirmeleri.
* **Termal-Hidrolik Şablonlama:** D6 altıgen simetrisi destekli kanal eşleme ve malzeme durum yönetimi.

---

## Sistem Gereksinimleri

* **İşletim Sistemi:** Linux x86_64 (Ubuntu 20.04+, Debian 11+, Fedora, Arch Linux ve türevleri).
* **Bağımlılıklar:** Herhangi bir Python, Conda veya ek kütüphane kurulumu gerekmez; tek bir bağımsız binary olarak çalışır.
* **Hesaplama Motoru:** Serpent 2 hesaplama motoru ve nükleer veri kütüphaneleri (ENDF/B, JEFF vb.) güvenlik ve lisans nedeniyle pakete dahil değildir.

---

## Hesap Erişimi

Serpent Studio kurumsal güvenlik ve erişim standartlarına sahiptir. Uygulama ilk açıldığında sistem yöneticisi tarafından tanımlanmış kullanıcı adı ve parolanızla giriş yapmanız gerekir. Yeni hesap tanımlamaları ve panel yetkilendirmeleri yönetici tarafından gerçekleştirilir.

---

## Doğrulama (Opsiyonel)

İndirdiğiniz dosyanın bütünlüğünü sürümle birlikte sunulan `SHA256SUMS.txt` dosyasıyla teyit edebilirsiniz:

```bash
sha256sum -c SHA256SUMS.txt
```

---

## Lisans ve Yasal Uyarı

Serpent Studio tescilli bir yazılımdır. Tüm hakları saklıdır.  
Serpent, VTT Technical Research Centre of Finland tarafından geliştirilen bağımsız bir Monte Carlo reaktör fiziği kodudur. Serpent Studio bağımsız bir kullanıcı arayüzü olup VTT ile resmi bir ortaklığı bulunmamaktadır.
