# Serpent Studio v1.2.72.82 (Alpha)

[Serpent.Studio.AppImage indir](https://github.com/bkbariskucuk/serpent-studio/releases/download/v1.2.72.82/Serpent.Studio.AppImage)

```bash
chmod +x Serpent.Studio.AppImage
./Serpent.Studio.AppImage
```

Linux x86_64 (Ubuntu 20.04 / Debian 11 ve üzeri). FUSE bulunmayan sistemlerde `--appimage-extract-and-run` parametresiyle çalıştırılabilir. Python veya ek bağımlılık kurulumu gerektirmez.

## v1.2.72.82 ile Gelen Yenilikler ve Düzeltmeler

* **Git Tabanlı Tasarım Versiyon Ağacı (Design Version Tree & Branch Studio):**
  * Sıfır ek bağımlılık: Sistemde `git` kuruluysa yerel CLI hızlandırması, kurulu değilse gömülü saf Python `EmbeddedDesignVCS` motoru kesintisiz çalışır.
  * GitLab Network / EISquare GitFlow tarzı paralel yüzme kulvarları (swimlanes), yumuşak kübik bezier bağlantıları ve parlayan aktif HEAD düğümü.
  * Tasarım Değişiklik Önizleme Kartı (Hover Preview HUD): Fare kontrol noktası üzerine geldiğinde commit mesajı, dal adı ve reaktör semantik nükleer farklarını (Malzeme, Pin, Lattice, Yüzey, Dedektör kartları) anlık gösterir.
  * Dal Yönetimi: Dala çift tıklamayla anında geçiş (checkout), dal silme, dal yeniden adlandırma, dal birleştirme (merge) ve çakışma durumunda otomatik rollback koruması.

* **Çalışma Alanı Ağacı (Workspace Tree) Klasör Bazlı Dal Butonu / Öğesi:**
  * Eski snapshot klasörünün yerini alan, her çalışma alanı ve proje klasörünün en üstünde yer alan `[Tasarım Dalları / Design Branches]` öğesi geri getirildi.
  * Çift tıklama ve Enter tuşu ile doğrudan ilgili klasörün Tasarım Ağacı penceresini açar; sağ tık menüsünden doğrudan dal yönetimine erişilir.

* **Vektörel SVG İkon Seti ve Glif / Tofu Hatası Giderimi:**
  * Karakter emojileri yerine HiDPI vektörel SVG ikon seti (`branch`, `branch_new`, `branch_edit`, `branch_delete`, `commit`, `merge`, `switch`, `diff`).
  * Toolbar genişlik çakışması (1264px -> 871px) giderildi; buton metinleri ve dolguları kompaktlaştırılarak ferah bir yerleşim sağlandı.

* **Ctrl+S ve Farklı Kaydet Dal Popout Bildirimi (Branch Save Toast):**
  * Kaydetme yapıldığında ekranın sağ alt köşesinde beliren, aktif dal renginde vektörel dal simgesi, aktif dal adı (`[  master ]`), dosya adı ve Tasarım Ağacı kısayolu sunan modern toast bildirimi.
  * Tek tıkla Tasarım Ağacı'nı açma, fare üzerine gelindiğinde otomatik kapanmayı duraklatma (hover pause), hızlı kapatma ve dinamik istifleme.
  * §7 Erişilebilirlik (reduced_motion) standardına tam uyum: Animasyonları Durdur tercihi etkinken animasyonlar atlanır, anında açılıp kapanır.

* **Eski Snapshot Kurgusunun Emekliye Ayrılması:**
  * Diskte kopyalama yapan eski `snapshots/` klasörleri kaldırıldı; elektrik kesintisi ve çökme koruması sunan Auto-Recovery Draft mekanizması gizli `.recovery_draft.json` üzerinde izole edildi.

## İndirme ve Doğrulama

Yalnızca `Serpent.Studio.AppImage` dosyasını indirmeniz yeterlidir. `.zsync` dosyaları uygulama içi otomatik güncelleyici içindir.

İndirdiğiniz dosyanın bütünlüğünü `SHA256SUMS.txt` ile karşılaştırabilirsiniz.
