# Serpent Studio v1.2.71.58 (Alpha)

[Serpent.Studio.AppImage indir](https://github.com/bkbariskucuk/serpent-studio/releases/download/v1.2.71.58/Serpent.Studio.AppImage)

```bash
chmod +x Serpent.Studio.AppImage
./Serpent.Studio.AppImage
```

Linux x86_64 (Ubuntu 20.04 / Debian 11 ve üzeri). FUSE bulunmayan sistemlerde `--appimage-extract-and-run` parametresiyle çalıştırılabilir. Python veya ek bağımlılık kurulumu gerektirmez.

## v1.2.71.58 ile Gelen Yeni Yetenekler ve İyileştirmeler

* **Özel Konsantrik Pin Katmanı Tasarımcısı (Concentric Pin Layer Designer):** Visual Pin Inspector (`PinCustomizerDialog`) içinde standart katman düzenleyiciye ek olarak Dinamik Özel Katman Modu eklendi. Kullanıcılar bir anahtar butonu ile Standart ve Özel modlar arasında geçiş yapabilir.
* **Sınırsız ve Serbest Katman Tanımlama (Arbitrary Layer Stack):** Eski pin katmanı üzerine "➕ Katman Ekle" butonu ile merkeze yakıt, ardından boşluk, ardından tekrar yakıt veya istenen herhangi bir katman sırası eklenebilir. Projede tanımlı tüm malzemeler kısıtlanmaksızın seçilebilir ve serbest metin olarak malzeme girilebilir.
* **Katman Parametresi ve Rol İsimlendirme:** Yakıt peleti, boşluk, gömlek vb. her katmanın parametre/rol ismi (`QLineEdit`) kullanıcı tarafından tamamen özelleştirilebilir.
* **Otomatik Yarıçap İlerlemesi (Smart Auto-Radius Progression):** Yeni bir katman eklendiğinde son katman yarıçapı üzerinden otomatik ve akıllı yarıçap değeri hesaplanarak atanır (yakıt 0.381 -> boşluk 0.411 -> gömlek 0.452 -> +0.050 cm). İsteğe göre katman sınırsız (unbounded) dış ortam olarak da işaretlenebilir.
* **Katman Sıralama ve Canlı Renk Ataması (Interactive Cross-Section & Ordering):** Katmanlar ▲/▼ butonlarıyla anında yeniden sıralanabilir veya silinebilir. Canlı kesit önizlemesinde (Pin Preview) halkalara veya dış ortama tıklandığında ilgili katmanın renk seçicisi açılarak GUI içi görsel renk atanabilir.
* **Saf Serpent Sözdizimi Desteği (Syntax Independence & Clean Output):** Renk atamaları yalnızca GUI görselleştirmesi için parametrik olarak tutulur; üretilen Serpent input syntax metnine asla `rgb` komutu yazılmaz, standart Serpent pin kartı sözdizimi korunur.
* **Yönetim Paneli İstemci Sürüm Algılama ve Kalp Atışı Güncellemesi (Heartbeat Version Tracking Fix):** Arka planda çalışan oturum koruyucunun (`SessionGuard`) kalp atışı (`/v1/telemetry/heartbeat`) isteği üzerinden gönderilen `client_version` ve `platform` verileri sunucu veri tabanında oturum kaydına (`sessions.client_version`) anlık olarak işlenir; böylece kullanıcılar yeniden giriş yapmasalar bile kullandıkları güncel sürüm yönetim panelinde ve telemetri istatistiklerinde doğru olarak algılanır. Yönetim paneli HTML'indeki sürüm kontrolü dinamik sunucu sürüm karşılaştırmasına geçirildi.

## İndirme ve Doğrulama

Yalnızca `Serpent.Studio.AppImage` dosyasını indirmeniz yeterlidir. `.zsync` dosyaları uygulama içi otomatik güncelleyici içindir.

İndirdiğiniz dosyanın bütünlüğünü `SHA256SUMS.txt` ile karşılaştırabilirsiniz.
