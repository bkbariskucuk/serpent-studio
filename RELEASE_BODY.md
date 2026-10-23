# Serpent Studio v1.2.72.78 (Alpha)

[Serpent.Studio.AppImage indir](https://github.com/bkbariskucuk/serpent-studio/releases/download/v1.2.72.78/Serpent.Studio.AppImage)

```bash
chmod +x Serpent.Studio.AppImage
./Serpent.Studio.AppImage
```

Linux x86_64 (Ubuntu 20.04 / Debian 11 ve üzeri). FUSE bulunmayan sistemlerde `--appimage-extract-and-run` parametresiyle çalıştırılabilir. Python veya ek bağımlılık kurulumu gerektirmez.

## v1.2.72.78 ile Gelen Yenilikler ve Düzeltmeler

* **Kullanıcı Sözleşmesi Dil Desteği ve Giriş Ekranı Butonları (`core/legal.py`, `ui/legal_dialog.py`, `ui/splash_screen.py`, `ui/login_dialog.py`):**
  * Kullanıcı sözleşmesi hem Türkçe hem İngilizce tam metin ve dinamik canlı dil geçişiyle yenilendi.
  * Eski korkutucu teknik ve bürokratik DRM ifadeleri kaldırılarak sade, güven veren ve şeffaf 4 temel madde oluşturuldu.
  * Splash ve yedek giriş ekranlarına doğrudan gömülü zarif sözleşme butonları eklendi.

* **Model Geliştirme Amaçlı Betik/Tasarım Senkronizasyonu (`core/telemetry.py`, `ui/main_window.py`, `server/control_plane.py`):**
  * Platformun hesaplama ve AI modellerini iyileştirmek amacıyla girdi betikleri ve model şablonları sunucu kontrol düzlemine aktarılacak şekilde yapılandırıldı.
  * Girdi kaydetme (Ctrl+S / Farklı Kaydet), simülasyon başlatma ve geometri derleme anında tam girdi kartları ve betikler arka planda (0 ms UI gecikmesi) senkronize edilir.
  * SHA-256 istemci tabanlı tekilleştirme ve çevrimdışı spooling ile sıfır veri kaybı sağlandı.
  * Yönetici web panelindeki "Çalıştırılan Serpent Betikleri" sekmesi üzerinden tüm girdi ve modeller listelenebilir, filtrelenebilir, CSV/JSON indirilebilir ve tam metin görüntülenebilir.

* **Assembly ve Core Panellerinde Ergonomik Kaydırma Çubuğu & Saç Teli Ayırıcı (`ui/theme.py`, `ui/main_window.py`):**
  * Kontrol paneli ile kanvas arasındaki ~22 px'lik hantal çift-oluk kaldırıldı; 2 px saç teli ayırıcı (SplitHCursor) uygulandı (%65 alan tasarrufu).
  * Kaydırma çubuğu 8 px genişliğinde, 4 px kapsül radyuslu, şeffaf yüzen modern overlay olarak dengelendi; açık ve koyu tema kontrastı artırıldı.

* **Tek Satırlı Kompakt Başlık Düzenleri & Akıcı Animasyonlar (`ui/main_window.py`, `ui/control_rods.py`):**
  * Serpent Input Preview başlık alanı tek bir kompakt satıra dönüştürüldü; kontroller dikey merkezlendi.
  * Control Rods Definition Preview (CRDP) başlığı ve butonları tek satıra indirildi, InOutCubic 200 ms animasyon eğrisi ile açılış/kapanış takılmaları giderildi.
  * CRS Tab slider bar'ı ARI/MID/ARO butonlarıyla senkron akıcı animasyona kavuşturuldu.

## İndirme ve Doğrulama

Yalnızca `Serpent.Studio.AppImage` dosyasını indirmeniz yeterlidir. `.zsync` dosyaları uygulama içi otomatik güncelleyici içindir.

İndirdiğiniz dosyanın bütünlüğünü `SHA256SUMS.txt` ile karşılaştırabilirsiniz.
