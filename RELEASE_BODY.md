# Serpent Studio v1.2.72.85 (Alpha)

[Serpent.Studio.AppImage indir](https://github.com/bkbariskucuk/serpent-studio/releases/download/v1.2.72.85/Serpent.Studio.AppImage)

```bash
chmod +x Serpent.Studio.AppImage
./Serpent.Studio.AppImage
```

Linux x86_64 (Ubuntu 20.04 / Debian 11 ve üzeri). FUSE bulunmayan sistemlerde `--appimage-extract-and-run` parametresiyle çalıştırılabilir. Python veya ek bağımlılık kurulumu gerektirmez.

## v1.2.72.85 ile Gelen Yenilikler ve Düzeltmeler

* **Çatallanma Noktasının (Fork Point) Ana Dalda Sabitlenmesi & Ray Kilitleme:**
  * "Master dalındaki ikinci düğümden yeni dal açıldığında ikinci düğüm yeni dala alınıyor" sorunu giderildi (`ui/design_tree_graph.py`).
  * Soyağacı (DAG) ray kilitleme algoritması (`_recompute_node_rails`): Ana gövde (master/main) aşamaları ilk sırada taranarak daima Ray 0'a sabitlenir.
  * Temel kural: Bir ana dal düğümü (çatallanma noktası) asla çocuk dal tarafından gasp edilmez. İkinci düğüm master üzerinde sabit kalır; yeni dal o düğümden türeyerek kendi yatay düzlemine (Ray 1) bağlanır ve kendi rayında dümdüz akar.
* **Tam Türkçe ve Unicode Dal İsmi Desteği (`core/version_control.py`, `ui/design_tree_dialog.py`):**
  * ASCII-only kısıtlaması kaldırıldı (`sanitize_branch_name`); Türkçe karakterler (`ç, ğ, ı, ö, ş, ü, Ç, Ğ, İ, Ö, Ş, Ü`), sayılar, altçizgi ve tireler tam korunur.
  * Git ref standartlarına uygun olarak geçersiz karakterler ve boşluklar normalize edilir.
* **Gerçek Dal Uzaması ve Oyun Tarzı "Achievement" Büyüme Animasyonu (`ui/design_tree_graph.py`, `ui/theme.py`, `ui/design_tree_dialog.py`):**
  * De Casteljau kübik Bezier alt-eğri algoritması (`sub_bezier`) ile dallar zaman çizelgesi boyunca ana kökten çocuklara doğru organik biçimde uzar.
  * Aktif uzayan dal ucunda yüksek ışıltılı enerji kıvılcımı (radyal aura + çekirdek parçacık) yolu takip eder.
  * Dal yeni bir düğüme ulaştığında oyunlardaki başarım kilit açılışı ("Achievement Unlocked") benzeri genişleyen ve sönen halka şok dalgası (shockwave pulse ring) belirir.
  * Araç çubuğuna "Canlandır" butonu (`btn_animate`, `F6`, `Boşluk`) eklendi.
  * Erişilebilirlik kuralına (Rule 7) tam uyum: `reduced_motion` aktifken animasyon anında tamamlanır, 0 ms gecikme sağlanır.

## v1.2.72.84 ile Gelen Yenilikler ve Düzeltmeler

* **Tasarım Versiyon Ağacından Git Dahili refs/stash Referanslarının Filtrelenmesi:**
  * Dallar arası geçiş esnasında çalışma alanı dosyalarını korumak amacıyla Git tarafından arka planda açılan geçici `refs/stash` ve `Auto-stash` kayıtları tasarım ağacı grafiğinden filtrelendi (`core/version_control.py`, `ui/design_tree_graph.py`).
  * `git log` parametresi `--all` yerine `--branches --tags HEAD` standardına çekilerek sadece kullanıcının fiilen oluşturduğu gerçek tasarım dalları (`master`, `asx`, `18_cr_test` vb.) listelenir.
  * Tasarım Ağacı görsel kulvarlarında dahili Git mekanizmaları yerine yalnızca saf model dalları görünür, görsel kalabalık ve kafa karışıklığı önlenir.

## v1.2.72.83 ile Gelen Yenilikler ve Düzeltmeler

* **Tasarım Ağacı Tuvalinde Çift Yönlü Serbest Kaydırma (Pan & Multi-Directional Scroll):**
  * Fare ile Tuval Sürükleme (Drag-to-Pan): Boş tuval alanına sol tıklayarak veya herhangi bir noktada orta tuşla sürükleyerek tuvali yatay ve dikey yönde serbestçe kaydırma imkanı (Figma/Miro/GitKraken tarzı akıcı pan desteği).
  * Akıllı Fare Tekerleği & Dokunmatik Yüzey: Dikey eksende dal biriktiğinde normal tekerlek dikey kaydırır; dallar dikeyde sığıyorsa veya `Shift + Tekerlek` yapıldığında otomatik olarak yatay zaman çizelgesini kaydırır.
  * Klavye Yön Tuşları: Sol/Sağ/Yukarı/Aşağı ok tuşları ile hassas kaydırma; `Home` tuşu ile başlangıç köküne, `End` tuşu ile en güncel commit düğümüne anında atlama.
  * Aktif Commit Düğümüne Otomatik Odaklanma: Diyalog açıldığında veya dal değiştirildiğinde en güncel aktif HEAD commit düğümünü görünür alanın merkezine getiren yumuşak auto-scroll mekanizması.

* **Yapışkan (Sticky) Dal Başlıkları & Dal Ezilmesini Önleme:**
  * Sağa doğru ne kadar kaydırılırsa kaydırılsın, sol taraftaki dal rozetleri (`master (Trunk)`, `feature_a` vb.) görünür pencere sol kenarında sabit (pinned) kalır; kullanıcının baktığı kulvarın hangi dala ait olduğu her zaman görünür.
  * Cömert tuval payı (+360 px yatay, +120 px dikey) ile son düğümlerin ve dal çizgilerinin sağ panel sınırına dayanıp ezilmesi engellendi.
  * Hover HUD Bilgi Kartı pencere sınırına kilitlendi: Sağ panel yakınına gelindiğinde kart otomatik olarak imlecin soluna ters döner; panel altına girip ezilme sorunu tamamen giderildi.

* **Katlanabilir / Boyutlandırılabilir Sağ Detay Paneli (`Ctrl+D`):**
  * "Dallar sağ panel tarafından eziliyor" geri bildirimi doğrultusunda sağ detay panelinin minimum genişliği 240 piksele düşürüldü ve başlangıç bölme oranı grafik lehine 900:260 olarak ayarlandı.
  * Araç çubuğuna ve detay paneli başlığına aç/kapa butonu (`btn_toggle_details`, `Ctrl+D`, `✕`) eklendi; istenildiğinde detay paneli gizlenerek tüm ekran (%100 genişlik) dal grafiğine ayrılabilir.

* **Tasarım Versiyon Ağacı Geri Al ve Yinele Desteği (Ctrl+Z / Ctrl+Y / Ctrl+Shift+Z):**
  * Çift motorlu (Sistem Git CLI ve Saf Python VCS) derin undo/redo mimarisi (`core/version_control.py`).
  * Dal açma (`create_branch`), dal silme (`delete_branch`), dal yeniden adlandırma (`rename_branch`), dal değiştirme (`switch_branch`), aşama kaydetme (`commit_design`) ve dal birleştirme (`merge_branch`) işlemleri eksiksiz geri alınabilir ve yinelenebilir.
  * Çalışma alanındaki model dosyaları korunarak yumuşak geri alma (`git reset --soft` / `reset_to_commit`) uygulanır; veri kaybı yaşanmaz.
  * Klavyeden `Ctrl+Z` (Geri Al), `Ctrl+Y` / `Ctrl+Shift+Z` (Yinele) ve `F5` (Yenile) kısayolları doğrudan stüdyo penceresine bağlandı. Arama kutusu odaklıyken metin geri alma ile çakışması engellendi.

* **Araç Çubuğu (Toolbar) Yerleşim ve Taşma Çözümü (`ui/design_tree_dialog.py`):**
  * "Butonlar sığmamış yerlerine" geri bildirimi ve dar ekranlarda butonların üst üste binmesi sorunu kökten çözüldü.
  * Geri Al (`btn_undo`), Yinele (`btn_redo`), Yenile (`btn_refresh`) ve Detay Paneli (`btn_toggle_details`) butonları 28×28 piksel kompakt HiDPI vektörel SVG ikon butonlarına dönüştürüldü.
  * Dinamik açıklayıcı ipucu (tooltip): Butonun üzerine gelindiğinde bir sonraki geri alınacak/yinelenecek somut işlem adı ve kısayolu (`Geri Al: '18_cr_test' dalını oluşturma (Ctrl+Z)`) dinamik olarak gösterilir.
  * Minimum pencere boyutu 960×560 px olarak sabitlendi. Hem Türkçe hem İngilizce dil modlarında tüm buton ve girişlerin 0 px çakışmayla ferah oturması garanti edildi.

## İndirme ve Doğrulama

| Dosya | Açıklama |
|---|---|
| `Serpent.Studio.AppImage` | Taşınabilir bağımsız uygulama paketi |
| `SHA256SUMS.txt` | Kriptografik doğrulama özeti |
