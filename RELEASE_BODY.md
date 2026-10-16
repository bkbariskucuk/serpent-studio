# Serpent Studio v1.2.71.63 (Alpha)

[Serpent.Studio.AppImage indir](https://github.com/bkbariskucuk/serpent-studio/releases/download/v1.2.71.63/Serpent.Studio.AppImage)

```bash
chmod +x Serpent.Studio.AppImage
./Serpent.Studio.AppImage
```

Linux x86_64 (Ubuntu 20.04 / Debian 11 ve üzeri). FUSE bulunmayan sistemlerde `--appimage-extract-and-run` parametresiyle çalıştırılabilir. Python veya ek bağımlılık kurulumu gerektirmez.

## v1.2.71.63 ile Gelen Yeni Yetenekler ve İyileştirmeler

* **Pin Tanımlama Akışı ve Ctrl+S Desteği:** Pin Düzenleyici (`PinCustomizerDialog`) içinde Ctrl+S kısayolu ile pencereyi kapatmadan anında hızlı kayıt imkânı getirildi. "Save & Apply Pin" varsayılan butona bağlandı; pinler arası geçişlerdeki gereksiz uyarı pencereleri kaldırıldı ve çıkış onayı yalnızca kritik kapatma işlemlerine (X, Cancel, Esc) sınırlandı.
* **Pin Diyalogu ve Panel Kaydırma İyileştirmesi:** Pin diyalog form alanı `QScrollArea` içine alınarak düşük çözünürlüklü ve kısa ekranlarda tüm katman ve renk kontrolleri erişilebilir hale getirildi; dikey kaydırma çubukları optimize edildi.
* **Core Demet Silme ve Hücre Temizleme:** Core Controls paneline onay ve undo/redo destekli "Demeti Sil" butonu eklendi; silinen demetin core matrisindeki hücreleri doldurucu malzeme ile güvenli biçimde temizlenerek tombstone renk kalıntıları önlendi. Core Canvas sağ-tık menüsüne tek hücre temizleme ("Clear Cell") özelliği eklendi.
* **Ayrılabilir Syntax Paneli (Popout Syntax Dialog):** Material Definition ve Control Rods önizleme başlıklarına Popout butonu eklendi; syntax paneli bağımsız bir pencereye (`PopoutSyntaxDialog`) taşınabilir, F11 ile tam ekran yapılabilir ve tek tıkla ana pencereye geri yerleştirilebilir (dock).
* **Kapsamlı Geri Al/İleri Al (Undo/Redo) & Renk Kurtarma:** Reflektör iç yarıçap değişimleri (`chk_auto_core_radius`), demet ekleme/silme ve pin renk düzenlemeleri tam geri alınabilir hale getirildi; `_capture_canvas_state` fonksiyonuna malzeme ve pin renk durumları dahil edilerek Ctrl+Z ile renk bozulmalarının anında geri döndürülmesi sağlandı.

## İndirme ve Doğrulama

Yalnızca `Serpent.Studio.AppImage` dosyasını indirmeniz yeterlidir. `.zsync` dosyaları uygulama içi otomatik güncelleyici içindir.

İndirdiğiniz dosyanın bütünlüğünü `SHA256SUMS.txt` ile karşılaştırabilirsiniz.
