# Serpent Studio v1.2.72.83 (Alpha)

[Serpent.Studio.AppImage indir](https://github.com/bkbariskucuk/serpent-studio/releases/download/v1.2.72.83/Serpent.Studio.AppImage)

```bash
chmod +x Serpent.Studio.AppImage
./Serpent.Studio.AppImage
```

Linux x86_64 (Ubuntu 20.04 / Debian 11 ve üzeri). FUSE bulunmayan sistemlerde `--appimage-extract-and-run` parametresiyle çalıştırılabilir. Python veya ek bağımlılık kurulumu gerektirmez.

## v1.2.72.83 ile Gelen Yenilikler ve Düzeltmeler

* **Tasarım Versiyon Ağacı Geri Al ve Yinele Desteği (Ctrl+Z / Ctrl+Y / Ctrl+Shift+Z):**
  * Çift motorlu (Sistem Git CLI ve Saf Python VCS) derin undo/redo mimarisi (`core/version_control.py`).
  * Dal açma (`create_branch`), dal silme (`delete_branch`), dal yeniden adlandırma (`rename_branch`), dal değiştirme (`switch_branch`), aşama kaydetme (`commit_design`) ve dal birleştirme (`merge_branch`) işlemleri eksiksiz geri alınabilir ve yinelenebilir.
  * Çalışma alanındaki model dosyaları korunarak yumuşak geri alma (`git reset --soft` / `reset_to_commit`) uygulanır; veri kaybı yaşanmaz.
  * Klavyeden `Ctrl+Z` (Geri Al), `Ctrl+Y` / `Ctrl+Shift+Z` (Yinele) ve `F5` (Yenile) kısayolları doğrudan stüdyo penceresine bağlandı. Arama kutusu odaklıyken metin geri alma ile çakışması engellendi.

* **Araç Çubuğu (Toolbar) Yerleşim ve Taşma Çözümü (`ui/design_tree_dialog.py`):**
  * "Butonlar sığmamış yerlerine" geri bildirimi ve dar ekranlarda butonların üst üste binmesi sorunu kökten çözüldü.
  * Geri Al (`btn_undo`), Yinele (`btn_redo`) ve Yenile (`btn_refresh`) butonları 28×28 piksel kompakt HiDPI vektörel SVG ikon butonlarına dönüştürüldü.
  * Dinamik açıklayıcı ipucu (tooltip): Butonun üzerine gelindiğinde bir sonraki geri alınacak/yinelenecek somut işlem adı ve kısayolu (`Geri Al: '18_cr_test' dalını oluşturma (Ctrl+Z)`) dinamik olarak gösterilir.
  * Minimum pencere boyutu 960×560 px olarak sabitlendi. Hem Türkçe hem İngilizce dil modlarında tüm buton ve girişlerin 0 px çakışmayla ferah oturması garanti edildi.

* **Git Tabanlı Reaktör Tasarım Ağacı (Design Version Tree) & Dal Stüdyosu:**
  * Sıfır harici bağımlılık: Sistemde Git kuruluysa yerel CLI hızlandırması, kurulu değilse gömülü saf Python motoru kesintisiz çalışır.
  * EISquare GitFlow tarzı yüzme kulvarları (swimlanes), kübik bezier bağlantıları ve parlayan aktif HEAD düğümü.
  * Hover Preview HUD: Fare kontrol noktası üzerine geldiğinde reaktör semantik nükleer farklarını (Malzeme, Pin, Lattice, Yüzey, Dedektör) anlık gösterir.
  * Çalışma alanı klasör bazlı dal butonu (`[Tasarım Dalları / Design Branches]`) ve Ctrl+S dal rozetli popout bildirimi (`BranchSaveToast`).

## İndirme ve Doğrulama

| Dosya | Açıklama |
|---|---|
| `Serpent.Studio.AppImage` | Taşınabilir bağımsız uygulama paketi |
| `SHA256SUMS.txt` | Kriptografik doğrulama özeti |
