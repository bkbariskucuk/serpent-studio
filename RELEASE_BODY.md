# Serpent Studio v1.4.74.89 (Alpha)

[Serpent.Studio.AppImage indir](https://github.com/bkbariskucuk/serpent-studio/releases/download/v1.4.74.89/Serpent.Studio.AppImage)

Linux x86_64 · Debian 11 / Ubuntu 20.04 ve üzeri · GLIBC 2.31 tabanı.

```bash
chmod +x Serpent.Studio.AppImage
./Serpent.Studio.AppImage
```

FUSE bulunmayan sistemlerde `--appimage-extract-and-run` kullanılabilir. Arayüz için Python kurulumu gerekmez; simülasyon ve kontrol çalışmaları ayrıca Serpent kurulumu gerektirir.

## Bu sürümde

- **Seçilebilir birleştirme:** Kaynak/hedef dalları ve checkpoint'leri seçme; native Git ort ve gömülü üç yönlü birleştirme. Gömülü motorda çoklu ortak ata desteği. Çakışmalar numaralı Base/Mevcut/Gelen/Sonuç alanlarında, yalnız ilgili satırlar vurgulanarak incelenir.
- **Daha anlaşılır kayıt:** Yeni dal seçilen eski kayıttan başlayabilir ve dal adıyla başlangıç checkpoint'i alır. Normal Kaydet yeni düğüm oluşturmaz. Merge öncesinde bekleyen değişiklikler karşılaştırılır; kullanıcı isterse checkpoint oluşturup devam eder.
- **Geçmişi inceleme:** Eski checkpoint'in modeli ve kayıtlı analiz sonuçları açılabilir; düzenleme için yeni dala yönlendirilir. Güncel dal ucunda çalışırken gereksiz yeni dal uyarısı kaldırıldı. Üst göstergede checkpoint adı bulunur.
- **Geçmiş araçları:** Doğrudan checkpoint silme incelemesi, taslaklar, cherry-pick/rebase, etiketler ve uzak ayrışmayı çözme akışları. GitLab/GitHub ekip yorumları, onaylar ve CI durumu uygulama içinden incelenebilir.
- **Okunabilir dal grafiği:** 60 kayıt sınırı kaldırıldı; uzun geçmişte etkin dallar korunur. Kavisli bağlantılar ve yoğun dallanma yerleşimi iyileştirildi. Dal silme penceresinin tema uyumu düzeltildi.
- **Kontrol çubuğu düzenleme:** Banka/demet atamasında yakıt, kılavuz halkaları ve mevcut kartlar korunur. Asimetrik kor sınırları doğru geri yüklenir. Desteklenmeyen dönüşümlü/çok parçalı geometrilerde açıklamalı kapsam denetimi bulunur.
- **Anlık syntax geri bildirimi:** Çubuk düzenlemelerinde gerçek değişen satır ve değer sarı vurgulanır; ilgili önizleme konuma gider. Çelişen yinelenen tanımlar doğrudan gösterilir. Atama değişiklikleri lattice satırlarında da izlenir.
- **Güncelleme bildirimi:** Kompakt sağ alt karta tıklamak Help → Check Updates penceresini açar.

## Kapsam ve geçiş bilgileri

Bağımsız dört sayaç politikası: `v1.3.73.88 → v1.4.74.89`; MINOR/PATCH/BUILD +1, alt sayaçlar sıfırlanmaz.

Mevcut eski kare dal referansları otomatik checkpoint'e dönüştürülmez; kullanıcı Checkpoint eylemini kullanabilir. Eski hedef kayda merge, sonraki geçmişi korumak üzere ayrı sonuç dalında yürür. Bazı geçmiş silme/rebase işlemleri native Git gerektirir ve yayımlanmış/karmaşık geçmişte sınırlanır. Gömülü motorun rename/özel merge driver desteği native Git ile tam eşdeğer değildir.

Uzak Git işlemleri sistem Git'ini; API işlemleri sunucu izinlerini gerektirir. GitLab/GitHub ürünlerinin tamamının eşdeğeri değildir. API tokenları oturum belleğindedir. Run arşivleri yereldir; otomatik Git aktarımı veya temizleme yapılmaz. Dağıtım kullanıcı projesi içermez, mevcut çalışma dosyaları korunur.

Basit çubuk editörü üstten girişli iki bölgeli pz modeli içindir. Tam trans koordinat bileşimi, sonlu/çok parçalı çubuk düzenleme ve genel CSG görüntüleyici desteği eklenmemiştir. Kontrol çalışmaları ve PPF sınırları reaktöre özgü doğrulama gerektirir; dinamik PID'de TH geri beslemesi uygulanmaz.

## Doğrulama

Çubuk akışları için 107 regresyon testi ve gerçek Serpent 2.2.3 ile beş sentetik iki-bankalı statik transport koşusu geçti. ANA_KEFF/IMP_KEFF değerleri ve bağıl belirsizlikleri bağımsız serpentTools okuyucusuyla eşleşti. Bu kontroller gerçek reaktör veya dinamik PID fiziksel validasyonu değildir.

Yayın betiği regresyon testlerini, gömülü sürüm/kaynak özetini, GLIBC tabanını, temiz paket/GUI açılışını ve yüklenen asset özetlerini denetler. İndirilen dosyayı release'teki SHA256SUMS.txt veya SHA512SUMS.txt ile karşılaştırabilirsiniz.
