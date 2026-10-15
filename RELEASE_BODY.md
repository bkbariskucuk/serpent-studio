# Serpent Studio v1.2.70.57 (Alpha)

[Serpent.Studio.AppImage indir](https://github.com/bkbariskucuk/serpent-studio/releases/download/v1.2.70.57/Serpent.Studio.AppImage)

```bash
chmod +x Serpent.Studio.AppImage
./Serpent.Studio.AppImage
```

Linux x86_64 (Ubuntu 20.04 / Debian 11 ve üzeri). FUSE bulunmayan sistemlerde `--appimage-extract-and-run` parametresiyle çalıştırılabilir. Python veya ek bağımlılık kurulumu gerektirmez.

## v1.2.70.57 ile Gelen Güvenlik İyileştirmeleri ve Zafiyet Kapatmaları

* **Token Hashleme (Token Hashing at Rest):** Oturum token'ları veri tabanında (SQLite / PostgreSQL) artık düz metin yerine SHA-256 özetiyle saklanır. Olası veri tabanı sızıntılarında token'lar saldırganlar tarafından doğrudan taklit edilemez; geriye dönük sorgu desteği ile mevcut oturumlar kesilmeden güvenliğe kavuşturuldu.
* **Fail-Closed TLS Güvencesi:** Uzak PostgreSQL bağlantılarında işletim sistemi CA sertifika demeti bulunamadığında sessizce güvensiz bağlantıya (`sslmode=require`) düşülmeyip fail-closed prensibiyle bağlantı reddedilir; böylece ortadaki adam (MITM) saldırıları engellendi.
* **Zamanlama Analizi (Timing Attack) Koruması:** `/v1/auth/login` ve `/admin/api/login` uç noktalarında var olmayan kullanıcı adları için de sahte PBKDF2 doğrulaması (`_DUMMY_HASH`) çalıştırılarak yanıt sürelerinin eşitlenmesi sağlandı; kullanıcı adı keşfi (enumeration) önlendi.
* **İstemci IP Sahteciliği (IP Spoofing) Savunması:** `_client_ip` çözümleyicisi, ters vekil (reverse proxy) başlıklarını (`X-Forwarded-For`, `CF-Connecting-IP`, `True-Client-IP`) yalnızca doğrudan bağlantı yerel güvenilir bir proxy (loopback) olduğunda işler; doğrudan dış istemcilerin sahte başlıklarla hız sınırlarını (rate limiting) baypas etmesi önlendi.
* **Telemetri DoS & Hız Sınırlandırması (Telemetry Rate Limiter):** `/v1/telemetry/errors` ve `/v1/telemetry/scripts` uç noktalarına kullanıcı bazlı kayan pencere hız sınırlayıcı entegre edilerek kötü niyetli veya döngüye girmiş istemcilerin veritabanını şişirmesi engellendi.
* **24 Saatlik Çevrimdışı Kullanım Toleransı (Offline Grace Period):** Kullanıcı aktif bile olsa sunucuyla 24 saatten uzun süre iletişim kurulamazsa oturum kilitlenir; böylece ağ bağlantısını keserek yönetici askıya alma/kill-switch kilidinden süresiz kaçınma açığı kapatıldı.
* **Güvenlik Başlıkları (Security Headers) ve Web Yönetim Paneli Şifre Güvenliği:** Tüm JSON ve HTML yanıtlarına `Strict-Transport-Security`, `Content-Security-Policy`, `X-Content-Type-Options`, `X-Frame-Options` başlıkları eklendi. Web yönetim panelinde düz metin `prompt()` yerine şifreyi maskeleyen güvenli `<dialog>` modalı ve en az 12 karakterlik şifre kuralı getirildi. `tools/manage_users.py` araçlarındaki import hatası düzeltildi ve 12 karakter kuralı bağlandı.

## İndirme ve Doğrulama

Yalnızca `Serpent.Studio.AppImage` dosyasını indirmeniz yeterlidir. `.zsync` dosyaları uygulama içi otomatik güncelleyici içindir.

İndirdiğiniz dosyanın bütünlüğünü `SHA256SUMS.txt` ile karşılaştırabilirsiniz.
