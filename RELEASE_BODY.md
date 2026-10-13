# Serpent Studio v1.2.70.55 (Alpha)

[Serpent.Studio.AppImage indir](https://github.com/bkbariskucuk/serpent-studio/releases/download/v1.2.70.55/Serpent.Studio.AppImage)

```bash
chmod +x Serpent.Studio.AppImage
./Serpent.Studio.AppImage
```

Linux x86_64 (Ubuntu 20.04 / Debian 11 ve üzeri). FUSE bulunmayan sistemlerde `--appimage-extract-and-run` parametresiyle çalıştırılabilir. Python veya ek bağımlılık kurulumu gerektirmez.

## v1.2.70.55 ile Gelen İyileştirmeler

* **Çekirdek Kanvası Reflektör Geri/İleri Alma (Ctrl+Z / Ctrl+Y) Entegrasyonu:** Core Canvas üzerinde reflektör malzemesi önayarı (`reflector_combo`), sınır kabı geometrisi (`reflector_shape_combo`), radyal kalınlık (`ref_rad_thick_spin`), eksenel kalınlık (`ref_ax_thick_spin`) ve çekirdek latis şekli (`shape_combo`) değişiklikleri geri alma/yineleme (undo/redo) motoruna tam entegre edildi.
* **Çekirdek Silinme (Core Wiping) Hatasının Kesin Çözümü:** Öncesinde reflektör kontrolleri undo durum kaydetmediği için, reflektör değiştirildikten sonra Ctrl+Z basıldığında yığındaki eski boş durum tetikleniyor ve tüm çekirdek matrisi siliniyordu. Artık çekirdek matrisi ve reflektör konfigürasyonu atomik olarak saklanmakta; `_restoring_undo_state` koruması ve sinyal bloklamaları ile geri alma sırasında yığının bozulması veya çekirdeğin sıfırlanması tamamen önlendi.
* **Debounced Spinbox Oturumu ve Çift Durum Koruması:** Radyal ve eksenel kalınlık spinbox değişimleri 800 ms zamanlayıcı ile debounced spin undo oturumuna bağlandı; yinelenen veya boş durumların yığına eklenmesi ve redo yığınının bozulması engellendi.
* **FreeType Font Önbelleği Segfault Koruması (`QT_NO_FT_CACHE=1`):** Linux/Wayland ortamlarında FreeType 2.14+ ve Qt 6.7 kombinasyonunda glif önbelleğe alma aşamasında tetiklenen çökme (`Signal 11 SEGV`) engellendi.
* **Çekirdek Kanvası Metin ve Ölçekleme Güvenliği:** Kanvas henüz gösterilmemişken dejenere ölçek matrisi (`m11=0, m22=0`) oluşması önlendi; çekirdek hücre etiketleri için güvenli font alt sınırı uygulandı.

## İndirme ve Doğrulama

Yalnızca `Serpent.Studio.AppImage` dosyasını indirmeniz yeterlidir. `.zsync` dosyaları uygulama içi otomatik güncelleyici içindir.

İndirdiğiniz dosyanın bütünlüğünü `SHA256SUMS.txt` ile karşılaştırabilirsiniz.
