# Serpent Studio v1.3.73.88 (Alpha)

[Serpent.Studio.AppImage indir](https://github.com/bkbariskucuk/serpent-studio/releases/download/v1.3.73.88/Serpent.Studio.AppImage)

Linux x86_64 · Debian 11 / Ubuntu 20.04 ve üzeri · GLIBC 2.31 tabanı.

```bash
chmod +x Serpent.Studio.AppImage
./Serpent.Studio.AppImage
```

FUSE bulunmayan sistemlerde `--appimage-extract-and-run` kullanılabilir. Arayüz için Python kurulumu gerekmez; simülasyon ve kontrol çalışmaları ayrıca Serpent kurulumu gerektirir.

## Bu sürümde

- **Yenilenen çalışma alanı:** Model, Analysis, Design History ve Thermal Hydraulics sekmeleri; editörle uyumlu görünüm, kompakt araç çubukları ve yumuşak geçişler. Modelin mevcut editörleri ve pop-out işlevleri korunur.
- **Daha rahat analiz:** Sonuç kümesi seçimi ve tüm analiz çıktıları sekmeli düzende. Çıktı sekmelerinin tamamı tek ayrık pencereye taşınabilir. PPF legend/metrik kutuları sabit, fit kararlı; elle yapılan zoom ve kaydırma korunur.
- **Analiz hazırlığı ve performans:** İsteğe bağlı splash ön yüklemesi, ayrı analiz süreci, ayarlanabilir bellek bütçesi ve iptal. Eksik uygunluk kaydından doğan GUI hesaplaması ve sekme geçişlerindeki donma yolları düzeltildi. Ön yükleme gerçek sonuç dosyalarının hesaplama süresini ortadan kaldırmaz.
- **Run geçmişi:** Düğüm başına çoklu run, saklanan çıktı kopyaları, geçmiş sonuç kümeleri, kayıtlı çalışma koşulları ve referansla karşılaştırma. Tarihsel geometri canlı tasarımı değiştirmeden incelenir.
- **Girdi ve simülasyon:** Operation/önizleme senkronizasyonu; `set iter`, `set rfr`, `set rfw`; değişen satıra gitme; Stop; süre ve konsol tanılarının düzeltilmesi. Kontrol çubukları mevcut demetlere atanabilir.
- **Kontrol çalışmaları:** Kritik çubuk araması, k-eff veya k-eff + PPF banka optimizasyonu, native transient güç PID ve grup bazlı PPF düzeltmeleri. Kayıtlı konumlar tablo, CSV ve 3D görünümde sunulur.
- **3D inceleme:** Zoom, pan, döndürme, kamera yönleri, ortografik/perspektif, X/Y/Z kesitleri, düzlemsel kesit, ölçüm, banka izolasyonu ve PNG/SVG/PDF dışa aktarma. Rod hareketinde ağır önizleme güncellemeleri etkileşim sonunda birleştirilir.

## Kapsam ve geçiş bilgileri

Bağımsız dört sayaç politikası: `v1.2.72.87 → v1.3.73.88`; alt sayaçlar sıfırlanmaz.

3D görünüm kabul edilmiş demet/çubuk modelini gösterir; genel Serpent CSG plotter değildir. PPF sınırları tasarıma göre kullanıcı tarafından belirlenir. Banka araması yerel, dinamik şekil düzeltmesi heuristiktir; küresel optimum, reaktöre özgü benchmark veya güvenlik sertifikasyonu iddiası yoktur. Dinamik çalışmalarda TH geri beslemesi uygulanmaz.

Run arşivleri yereldir; otomatik kota/temizleme ve Git ile sonuç gönderme yoktur. Önceden üzerine yazılmış eski sonuçlar geri üretilemez. Dağıtım temiz çalışma alanıyla açılır; mevcut kullanıcı projelerini taşımaz veya silmez.

Dosya bazlı Git/GitLab/GitHub bağlantıları korunur. API tokenları yalnız oturum belleğindedir; uzak Git işlemleri sistem Git'ini gerektirir.

## Doğrulama

Yayın betiği regresyon testlerini, gömülü sürüm/kaynak özetini, GLIBC tabanını, temiz paket/GUI açılışını ve yüklenen asset özetlerini denetler. İndirilen dosyayı release'teki `SHA256SUMS.txt` veya `SHA512SUMS.txt` ile karşılaştırabilirsiniz.
