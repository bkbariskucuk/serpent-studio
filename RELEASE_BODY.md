# Serpent Studio v1.2.70.53 (Alpha)

[Serpent.Studio.AppImage indir](https://github.com/bkbariskucuk/serpent-studio/releases/download/v1.2.70.53/Serpent.Studio.AppImage)

```bash
chmod +x Serpent.Studio.AppImage
./Serpent.Studio.AppImage
```

Linux x86_64 (Ubuntu 20.04 / Debian 11 ve üzeri). FUSE bulunmayan sistemlerde `--appimage-extract-and-run` parametresiyle çalıştırılabilir. Python veya ek bağımlılık kurulumu gerektirmez.

## v1.2.70.53 ile Gelen İyileştirmeler

* **Radar Minimap Silinme ve Kaydırma Güvenliği (RuntimeError Çözümü):** Popout ve çekirdek kanvaslarında minimap kapatıldığında/ayrıldığında kaydırma çubuğu dinleyicilerinin askıda kalması nedeniyle oluşan `RuntimeError: wrapped C/C++ object of type CanvasRadarMinimap has been deleted` hatası giderildi. `@pyqtSlot()`, `self.destroyed` bağlantısı ve korumalı temizleme rutini entegre edildi.
* **Oturum Denetleyici Uygulama Kapanış Koruması:** `SessionAccessController` nesnesinin `QApplication` üzerinde event filter olarak asılı kalmasından ötürü pencere kapatıldığında SIP bellek temizliğinde yaşanan `SIGSEGV` (Signal 11 / `sip_api_get_address`) hatası giderildi. Çıkışta tüm event filtreleri kaldırılarak uygulamanın temiz kapanması sağlandı.
* **Editöre Dön Butonu Açık Tema Uyumu:** Analiz çıktılarındaki "Back to Editor" butonu açık temada yumuşak buz mavisi arka plan (`#F0F9FF`) ve okyanus mavisi çerçeve (`#0284C7`) ile temaya tam uyumlu hale getirildi.
* **Sağ Alt Oturum Doğrulama Bildirimi:** Ağ kesintileri ve geçici kalp atışı hatalarında kullanıcı ekranını kilitleyen modal pencereler kaldırıldı. Sağ altta konumlanan, otomatik kapanan `SessionNotificationPopup` eklendi; kullanıcı aktifken arka planda otomatik onaylanır ve çalışma asla kilitlenmez.
* **Kapsamlı Serpent ve Nükleer Kütüphane Doğrulayıcısı:** Standart olmayan ortamlarda Serpent ikili dosyası (`sss2`) ve nükleer veri kütüphanelerini (`acelib`, `declib`, `nfylib`, `photonlib`) tespit eden derin tarayıcı ve doğrulayıcı geliştirildi.
* **İçe Aktarma Masaüstü Kısayolu:** Dosya içe aktarma diyaloğu sol çubuğuna doğrudan "Masaüstü / Desktop", "Çalışma Alanı / Workspace" ve "Ev Dizini / Home" kısayol butonları entegre edildi.
* **Yönetim Paneli Hata Tekilleştirme:** `/admin` kontrol panelinde sürekli tekrar eden hatalar tekilleştirildi (`occurrence_count`, `call_site`, `fingerprint`), "Benzersiz Hatalar" görünümü ve detaylı hata inceleme modalı eklendi.

## İndirme ve Doğrulama

Yalnızca `Serpent.Studio.AppImage` dosyasını indirmeniz yeterlidir. `.zsync` dosyaları uygulama içi otomatik güncelleyici içindir.

İndirdiğiniz dosyanın bütünlüğünü `SHA256SUMS.txt` ile karşılaştırabilirsiniz.
