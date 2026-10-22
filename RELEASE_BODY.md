# Serpent Studio v1.2.72.77 (Alpha)

[Serpent.Studio.AppImage indir](https://github.com/bkbariskucuk/serpent-studio/releases/download/v1.2.72.77/Serpent.Studio.AppImage)

```bash
chmod +x Serpent.Studio.AppImage
./Serpent.Studio.AppImage
```

Linux x86_64 (Ubuntu 20.04 / Debian 11 ve üzeri). FUSE bulunmayan sistemlerde `--appimage-extract-and-run` parametresiyle çalıştırılabilir. Python veya ek bağımlılık kurulumu gerektirmez.

## v1.2.72.77 ile Gelen Yenilikler ve Düzeltmeler

* **Cihaz Bağlama ve Cihaz Güvenliği (`core/device_identity.py`, `core/auth.py`):**
  * Donanım tabanlı parmak izi: `/etc/machine-id`, kök dosya sistemi UUID ve tek yönlü hashlenmiş MAC birleşimiyle SHA-256 cihaz özeti.
  * Hesap başına tam 2 cihaz sınırı ve üçüncü cihaz giriş engellemesi (`device_limit`).
  * İstemci tarafında oturum ve lisans dosyalarının yabancı donanımda çalıştırılmasını engelleyen katı makine doğrulaması.

* **Ed25519 İmzalı Otomatik Lisans & 90 Günlük Oturum (`core/licensing.py`, `server/licensing.py`):**
  * 30 günlük, hesaba ve cihaza bağlı Ed25519 dijital imzalı lisans altyapısı.
  * Oturum üst sınırı 90 gün, 6 saatlik sessiz arka plan nabzı (heartbeat) ile otomatik yenileme.
  * 20 dakikalık yeniden doğrulama ve yapay kilitler kaldırıldı; tek, kesintisiz uzun oturum deneyimi.
  * Lisans süresi boyunca tam çevrimdışı çalışma desteği.

* **Türkçe Kullanıcı Sözleşmesi (`core/legal.py`, `ui/legal_dialog.py`):**
  * Giriş penceresi, Hakkında ve Yardım menülerinden erişilebilen Türkçe Kullanıcı Sözleşmesi ve lisans bilgilendirmesi.

* **Yönetim Paneli Geliştirmeleri (`server/control_plane.py`):**
  * Cihaz sayacı, kapasite ve lisans imzalama göstergeleri.
  * Tekil cihaz ve tüm cihazları sıfırlama butonları, kullanıcı detayında cihaz/lisans bilgisi, CSV/JSON dışa aktarımlarda yeni alanlar.

## İndirme ve Doğrulama

Yalnızca `Serpent.Studio.AppImage` dosyasını indirmeniz yeterlidir. `.zsync` dosyaları uygulama içi otomatik güncelleyici içindir.

İndirdiğiniz dosyanın bütünlüğünü `SHA256SUMS.txt` ile karşılaştırabilirsiniz.
