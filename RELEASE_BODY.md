# Serpent Studio v1.2.71.74 (Alpha)

[Serpent.Studio.AppImage indir](https://github.com/bkbariskucuk/serpent-studio/releases/download/v1.2.71.74/Serpent.Studio.AppImage)

```bash
chmod +x Serpent.Studio.AppImage
./Serpent.Studio.AppImage
```

Linux x86_64 (Ubuntu 20.04 / Debian 11 ve üzeri). FUSE bulunmayan sistemlerde `--appimage-extract-and-run` parametresiyle çalıştırılabilir. Python veya ek bağımlılık kurulumu gerektirmez.

## v1.2.71.74 ile Gelen Yenilikler ve Düzeltmeler

* **Yeni Reaktör Kalbi Sihirbazı (New Core Wizard):**
  * Eşmerkezli halka geometrisi, kademeli dairesel (PWR) ve Chebyshev halka desenleri ile dinamik aktif demet sayısı hesabı.
  * Serpent 2 CSG Yüzey ve Hücre Üretimi: Aktif kalp sınırı (`surf 1`, `cell 1 0 fill`), yan reflektör (`surf 4`, `cell 5`), eksenel üst/alt reflektörler (`surf 8`, `surf 9`, `cell 6`, `cell 7`) ve dış uzay hücreleri (`outside`) eksiksiz CSG kart hiyerarşisiyle otomatik üretilir.
  * Yarıçapsız soğutucu pini doldurma ve sihirbaz içerisinden doğrudan soğutucu/baypas pini oluşturma (`CreateCoolantPinDialog`).
  * Tuval üzerinde sürekli ve kesintisiz sıvı hacmi çizimi, parıldayan aktif kalp sınırı, fare ile sürükleme (pan) ve çift yönlü düzenlenebilir Serpent betik editörü.

* **Assembly & Core Sihirbazlarında Ctrl+Z ve Ctrl+Y (Undo/Redo):**
  * Her iki sihirbaz penceresine tam durum denetimli geçmiş yığıtı (`_undo_stack`, `_redo_stack`) eklendi.
  * Hücre tıklamaları, palet değişimleri, halka demet sayısı ($E$), demet adımı, yükseklik ve reflektör değişimleri geçmişe kaydedilir.
  * Metin kutuları (`QLineEdit`, `QPlainTextEdit`, `QTextEdit`) aktifken kısayollar yerel metin düzenleyicisine devredilerek harf bazlı geri alma korunur.

* **3 Seviyeli Termal-Hidrolik (T/H) Mimarisi:**
  * **Mod 0 (Homojen Soğutucu / CZP):** Düşük hesaplama maliyetli soğuk sıfır güç (CZP) kıyaslamaları için tek tip soğutucu pini dolgusu.
  * **Mod 1 (Çift Zonlu Radyal Ayrım):** Demet montaj aralığı sıcak suyu ($T_{avg} \approx 310^\circ\text{C}$) ile çevre soğuk baypas suyu ($T_{in} \approx 290^\circ\text{C}$) bağımsız pinlere ayrılır; çevre reflektör $N_{\text{shells}}$ (1..5) eşmerkezli kabuklara bölünür.
  * **Mod 2 (Tam 3B Termal-Hidrolik Mesh):** Reaktör aktif boyu $N_z$ (2..20) eksenel dilime bölünür; Lineer veya PWR Kosinüs akı ağırlıklı eksenel yoğunluk profili ($\rho(z)$) hesaplanır; her kot için çok katmanlı `pz` yüzeyleri ve `cell ... fill` CSG kartları üretilir.
  * Canlı T/H Özet Kartı (Mesh Card) anlık dilim kalınlıklarını ve yoğunluk aralıklarını raporlar.

* **Gelişmiş Soğutucu Pini Oluşturucu:**
  * PWR Soğuk Kol (290°C), Kalp Ortalaması (310°C), Sıcak Kol (325°C) ve CZP (20°C) hazır termal önayarları.
  * Sıcaklığa bağlı doymuş su yoğunluğunu ($\rho(T)$) anlık hesaplayan çift yönlü senkronizasyon.

* **Spinbox Ezilmesi ve Taşma Kök Neden Çözümü:**
  * Mod seçici metinleri sadeleştirilerek sol panel konteynerinin sağa taşması tamamen ortadan kaldırıldı; yatay kaydırma çubuğu iptal edildi (`ScrollBarAlwaysOff`).
  * T/H parametreleri dengeli 2 sütunlu ızgaraya yerleştirilerek yukarı/aşağı stepper butonları ve kenarlıklar korundu.
  * `ModernSpinBox` iç bileşenlerine özel QSS izolasyonu getirilerek çift çerçeve ve buton ezilmeleri tamamen giderildi.

## İndirme ve Doğrulama

Yalnızca `Serpent.Studio.AppImage` dosyasını indirmeniz yeterlidir. `.zsync` dosyaları uygulama içi otomatik güncelleyici içindir.

İndirdiğiniz dosyanın bütünlüğünü `SHA256SUMS.txt` ile karşılaştırabilirsiniz.
