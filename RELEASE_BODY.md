# Serpent Studio v1.4.76.91

- PySide6 ana arayüz ve dağıtım bağı oldu; eski PyQt6 çalışma kopyası ayrı korunur.
- Resmî Serpent Plotter seçilen kaynak uygulamasını değiştirmeden kendi panelinde çalıştırır. Linux X11/XWayland gömme, aynı oturumla ayır/geri yerleştir, yeniden bağlantı ve süreç temizliği desteklenir. Serpent 2.2.4+ notu görünür; gerçek motor doğrulaması 2.2.5 ile yapıldı.
- Plotter bağlantısı etkin, doğrulanmış belgeyi ve include anlık görüntüsünü kullanır; kaynak yolu görünür, geçici girdide özgün dosya adı korunur. Eksik/geçersiz/bekleyen girdide eski veya örnek model başlatılmaz. Oturum açıkken belge değişirse yenileme gereği belirtilir.
- Bağımsız Studio Plotter, Assembly Inspector ve malzeme/kesit denetimleri geliştirildi; tekrarlanan kesit ve renk işlemlerinde önbellek/toplu çizim optimizasyonları yapıldı.
- Sekme geçişi native çökmesi, önizleme çerçeve titremesi, Definition Preview konum sıçraması ve pop-out odak yarışı düzeltildi. Run logları yoğun kullanımda sınırlı dilimlerle çizilir.
- Erişilebilirliğe Panel Boyutlarını Varsayılana Döndür komutu eklendi; komut paleti/global aramadan bulunabilir.
- Son Plotter/başlatma regresyonunda 134 tekil test geçti; gerçek PPF modeli, gömülü pencere ebeveynliği, üç pop-out turu, yeniden bağlantı ve doğal kapanış doğrulandı. Bu sonuç tam fiziksel validasyon veya GPU/FPS garantisi değildir.
- Geliştirici workspace’i, gerçek hesap çıktıları ve nükleer veri kütüphaneleri dağıtıma alınmaz.
