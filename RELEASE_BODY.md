# Serpent Studio v1.2.72.79 (Alpha)

[Serpent.Studio.AppImage indir](https://github.com/bkbariskucuk/serpent-studio/releases/download/v1.2.72.79/Serpent.Studio.AppImage)

```bash
chmod +x Serpent.Studio.AppImage
./Serpent.Studio.AppImage
```

Linux x86_64 (Ubuntu 20.04 / Debian 11 ve üzeri). FUSE bulunmayan sistemlerde `--appimage-extract-and-run` parametresiyle çalıştırılabilir. Python veya ek bağımlılık kurulumu gerektirmez.

## v1.2.72.79 ile Gelen Yenilikler ve Düzeltmeler

* **Analysis Outputs Excel & CSV Dışa Aktarımı (`core/analysis_csv_exporter.py`, `ui/analysis_outputs.py`):**
  * Dinamik Yatay Eksen Duyarlılığı: keff, beta_eff, CR, eksenel akı/güç ve tükenme çıktılarında seçilen eksene göre birinci sütun ve koordinat sistemi dinamik olarak değişir.
  * İstatistiksel Sapma Raporlama: Nominal değer, 1-sigma mutlak hata (`Absolute_Uncertainty_1sigma`), Monte Carlo bağıl hatası (`Relative_Error`) ve keff için `Uncertainty_pcm` ayrı sütunlarda sunulur.
  * Türkçe ve Avrupa Excel Ondalık Ayracı Düzeltmesi: tr_TR yerel ayarında noktalı sayıların (örneğin 20.886 -> 20886) binlik ayracı sanılarak bozulması giderildi; bölgesel noktalı virgül (;) ve ondalık virgül (,) standardı sağlandı.
  * Sütun Tekrarlama (Duplicate Column) Düzeltmesi: `Cumulative Time (days)` ile `Burn_Days_d` sütunlarının aynı anda bulunması engellendi; seçilen eksen daima birinci sütun olup diğer koordinatlar tekrarsız listelenir.
  * Termal Hidrolik Rod-Power Isı Çıktıları: "Thermal Hydraulic Code for Fuel Heat Removal" iş akışına tam uyumlu olarak radyal PPF ve det ısı çıktılarında yakıt çubuğu bazlı `Konum_X_cm`, `Konum_Y_cm`, `Konum_Z_cm`, `Fisyon_Gucu_W`, `Bagil_Hata`, `Mutlak_Hata_W`, `PPF_Fxy` kolonları eksiksiz üretilir.

* **Arayüz ve Buton Düzeni (`ui/analysis_outputs.py`, `ui/theme.py`, `core/i18n.py`):**
  * "Export CSV" butonu hem ana sayfada hem ayrık pencerede "Pop-out" ile "Export PNG" arasına yerleştirildi.
  * Vektörel "csv" SVG ikonu, TR ve EN çeviriler ve Komut Paleti kaydı tamamlandı.

## İndirme ve Doğrulama

Yalnızca `Serpent.Studio.AppImage` dosyasını indirmeniz yeterlidir. `.zsync` dosyaları uygulama içi otomatik güncelleyici içindir.

İndirdiğiniz dosyanın bütünlüğünü `SHA256SUMS.txt` ile karşılaştırabilirsiniz.
