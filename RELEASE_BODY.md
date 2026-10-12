# Serpent Studio v1.2.70.52 (Alpha)

[Serpent.Studio.AppImage indir](https://github.com/bkbariskucuk/serpent-studio/releases/download/v1.2.70.52/Serpent.Studio.AppImage)

```bash
chmod +x Serpent.Studio.AppImage
./Serpent.Studio.AppImage
```

Linux x86_64 (Ubuntu 20.04 / Debian 11 ve üzeri). FUSE bulunmayan sistemlerde `--appimage-extract-and-run` parametresiyle çalıştırılabilir. Python veya ek bağımlılık kurulumu gerektirmez.

## v1.2.70.52 ile Gelen İyileştirmeler

* **Sağ Alt Oturum Doğrulama Bildirimi:** Ağ kesintileri ve geçici kalp atışı hatalarında kullanıcı ekranını kilitleyen modal pencereler kaldırıldı. Sağ altta konumlanan, otomatik kapanan `SessionNotificationPopup` eklendi; kullanıcı aktifken arka planda otomatik onaylanır ve çalışma asla kilitlenmez.
* **Kapsamlı Serpent ve Nükleer Kütüphane Doğrulayıcısı:** Standart olmayan ortamlarda Serpent ikili dosyası (`sss2`) ve nükleer veri kütüphanelerini (`acelib`, `declib`, `nfylib`, `photonlib`) tespit eden derin tarayıcı ve doğrulayıcı geliştirildi. ELF başlık denetimi, kesin sürüm çıkarımı, `.xsdata` izotop sayımı ve Ayarlar sekmesinde görsel tanı paneli eklendi.
* **Analiz Çıktıları Editöre Dön Butonu:** Analiz sayfasındaki "Back to Editor" butonu açık ve koyu temalara tam uyumlu, belirgin çerçeveli ve yüksek kontrastlı hale getirildi.
* **İçe Aktarma Masaüstü Kısayolu:** Dosya içe aktarma diyaloğu sol çubuğuna doğrudan "Masaüstü / Desktop", "Çalışma Alanı / Workspace" ve "Ev Dizini / Home" kısayol butonları entegre edildi.
* **Yönetim Paneli Hata Tekilleştirme & Zengin Telemetri:** `/admin` kontrol panelinde sürekli tekrar eden hatalar tekilleştirildi (`occurrence_count`, `call_site`, `fingerprint`), "Benzersiz Hatalar" görünümü ve detaylı hata inceleme modalı eklendi.

## İndirme ve Doğrulama

Yalnızca `Serpent.Studio.AppImage` dosyasını indirmeniz yeterlidir. `.zsync` dosyaları uygulama içi otomatik güncelleyici içindir.

İndirdiğiniz dosyanın bütünlüğünü `SHA256SUMS.txt` ile karşılaştırabilirsiniz.
