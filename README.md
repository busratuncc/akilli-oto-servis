# Akıllı Oto Servis

Türkçe servis anlatımlarını yapılandırılmış iş emirlerine dönüştürmek, atölyedeki servis sürecini izlemek, OBD-II kodlarını kaydetmek ve geçmiş vakalar arasında arama yapmak için geliştirilen tez uygulaması.

## Mevcut uygulama (v1.2)

- Atölye özetlerini ve iş emri dağılımını gösteren dashboard
- Anonim kodla araç kaydı ve araç servis geçmişi
- Taslak, inceleme, onarım, parça bekleme ve tamamlanma durumlarına sahip iş emirleri
- İş emri durumunu değiştirme ve usta onayı verme
- Bir iş emrine birden fazla OBD-II kodu ekleme
- Yaygın OBD-II kodları için yerel açıklama bilgi tabanı
- Türkçe anlatımdan kilometre, belirti, yapılan işlem ve OBD-II kodu çıkarma
- Anahtar kelime ve OBD-II koduyla geçmiş vaka arama
- Yapay zekâ çıktısı ve usta onayı için araştırma izi
- Tarayıcıdan ses kaydı ve yerel `faster-whisper` ile Türkçe transkripsiyon
- `multilingual-e5-small` ve pgvector ile Türkçe anlamsal/hibrit vaka araması
- Cosine benzerliği için HNSW vektör indeksi
- Ad-soyad, işletme, e-posta, ülke kodu ve telefonla kullanıcı kaydı
- Zorunlu gizlilik aydınlatması ve kullanım şartları onayı
- Geliştirme ortamında `111111` yerel koduyla giriş ve sunucu taraflı oturum
- Kalıcı açık/koyu tema seçimi
- Türkçe ve İngilizce arayüz seçimi
- Araçlar, iş emirleri, dashboard ve vaka aramaları için hesap bazlı veri izolasyonu
- Profil/iletişim tercihi güncelleme ekranı
- Giriş, profil, araç ve iş emri değişiklikleri için denetim kaydı
- İş emrinden parça, işçilik ve diğer kalemlerle fatura oluşturma
- Sunucu tarafında hassas ondalık hesaplama, indirim ve KDV kontrolü
- Nakit, harici POS, banka havalesi ve diğer yöntemlerle kısmi/tam ödeme takibi
- Faturalanan, tahsil edilen, bekleyen ve vadesi geçen tutar özeti
- Fazla ödemeyi engelleyen bakiye kontrolü ve eşzamanlı tahsilat kilidi
- Fatura ve ödeme hareketleri için hesap bazlı veri izolasyonu ve denetim kaydı
- Test kartı formu, rastgele temalı yerel test bankası ve 3D Secure doğrulama akışı
- `123456` başarılı kodu, hatalı kod/deneme sınırı, süre aşımı ve çift tahsilat koruması
- Tam kart numarası, son kullanma tarihi ve CVV'yi backend'e göndermeyen güvenli demo mimarisi
- Usta onaylı vakalardan bağımsız test sorguları oluşturulan AI değerlendirme veri seti
- Anahtar kelime, semantik ve hibrit arama için Hit@K, MRR ve gecikme karşılaştırması
- Deney geçmişi, sorgu bazlı beklenen sıra ve en iyi yöntem özeti
- Yalnızca onaylı vakalardan kanıt, güven düzeyi ve sınırlama gösteren karar desteği
- Hesaba özel parça kartları, stok kodu, kategori, marka, birim ve fiyat yönetimi
- Manuel stok giriş/çıkışı, hareket geçmişi ve kritik stok uyarıları
- Stok maliyet değeri, stokta olmayan ve kritik seviyedeki parça özetleri
- Faturada stoktan parça seçimi, otomatik açıklama/fiyat doldurma ve güvenli stok düşümü
- Yetersiz veya eksi stok girişimini engelleyen sunucu taraflı kontrol ve işlem kilidi
- Haftalık randevu takvimi, servis türü ve randevu durum yönetimi
- Aynı ustaya çakışan aktif randevu atanmasını engelleyen sunucu taraflı kontrol
- Tarih ve/veya araç kilometresiyle çalışan bakım hatırlatmaları
- Geciken ve yaklaşan bakımları önceliklendiren operasyon özeti
- Müşteri adı veya telefonu tutmadan anonim araç koduna bağlı randevu mimarisi
- İş emrine bağlı 22 maddelik dijital araç kabul ve kontrol formu
- Güvenlik, lastik, sıvı, elektrik ve gövde kategorilerinde standart değerlendirme
- İyi, dikkat, kritik ve bekliyor durumlarıyla ölçüm ve bulgu kaydı
- Kontrol kapsamı, dikkat/kritik bulgu sayıları ve 0-100 araç sağlık puanı
- Eksik kontrolü, çözülmemiş kritik bulguyu ve onaysız formu tamamlatmayan kalite kapısı
- Kontrol kilometresini daha yüksekse araç kaydına güvenli biçimde aktarma
- Masaüstü ve mobil ekranlara uyumlu React arayüzü

## Başlangıç kapsamı

- Araç kaydı
- Servis iş emri kaydı
- OBD-II kodu kaydı
- Metinden örnek yapılandırılmış kayıt çıkarma
- Geçmiş vaka arama
- PostgreSQL + pgvector veri altyapısı
- FastAPI API ve React/Vite arayüzü
- Alembic veritabanı migration'ları
- Docker Compose ile tek komut kurulum

LLM tabanlı şema çıkarımı, deney/evaluasyon ekranı ve kanıta dayalı RAG sonraki iterasyonlarda mevcut servis arayüzlerinin arkasına eklenecektir. Arayüzdeki kural motoru ve benzerlik araması kesin teşhis üretmez; kayıt usta tarafından doğrulanmalıdır.

## Çalıştırma

1. `.env.example` dosyasını `.env` adıyla kopyalayın.
2. Proje kökünde çalıştırın:

```bash
docker compose up --build
```

Windows için aynı işlemi yapan yardımcı komut:

```powershell
.\scripts\dev.ps1
```

3. Arayüz: http://localhost:5174
4. API dokümantasyonu: http://localhost:8000/docs
5. Sağlık kontrolü: http://localhost:8000/api/health
6. Geliştirme e-posta kutusu (Mailpit): http://localhost:8026

Uygulama menüsü on bölümden oluşur: **Gösterge paneli**, **Araçlar**, **İş emirleri**, **Randevu & bakım**, **Araç kontrolü**, **Stok**, **Finans**, **Akıllı asistan**, **AI deneyleri** ve **Hesap ayarları**.

### Dijital araç kontrolü ve kalite kapısı

Her iş emri için tek bir dijital araç kontrol formu açılabilir. Form; fren ve güvenlik, lastikler, sıvılar ve kaçaklar, elektrik ve aydınlatma, gövde ve görsel kontrol olmak üzere beş kategoride 22 standart madde içerir. Her madde **iyi**, **dikkat**, **kritik** veya **bekliyor** olarak işaretlenebilir; ölçüm değeri ve bulgu notu ayrıca saklanır.

Araç sağlık puanı yalnızca gerçekten kontrol edilmiş maddeler üzerinden sunucuda hesaplanır: iyi durum 100, dikkat durumu 55, kritik durum 0 puan ağırlığı taşır. Bu puan kesin teknik teşhis değildir; atölyenin standart kabul kontrolünü tutarlı ve ölçülebilir hale getiren bir kalite göstergesidir.

Formun tamamlanması için bütün maddelerin değerlendirilmesi, kritik bulguların giderildi veya usta tarafından ele alındı olarak işaretlenmesi ve usta onayı gerekir. Aynı doğrulamalar arayüzden bağımsız olarak API katmanında da uygulanır. Kontrol sırasında girilen kilometre aracın mevcut kilometresinden yüksekse araç kaydı güncellenir. Form oluşturma, taslak kaydetme ve tamamlama hareketleri sağlık puanı ve kritik bulgu sayısıyla birlikte denetim kaydına yazılır.

### Randevu ve bakım planı

**Randevu & bakım** ekranı haftayı pazartesiden pazara sütunlar halinde gösterir. Her randevu anonim araç kodu, servis türü, başlangıç/bitiş zamanı ve isteğe bağlı usta atamasıyla kaydedilir. Planlanan, onaylanan, araç geldi, serviste, tamamlandı, iptal ve gelmedi durumları takvim üzerinden değiştirilebilir.

Aynı usta adına birbiriyle kesişen iki aktif zaman aralığı girilirse API ikinci randevuyu reddeder. Tamamlanan, iptal edilen veya gelmedi durumundaki randevular kapasiteyi bloke etmez. Bu kontrol yalnızca arayüzde değil veritabanına yazmadan önce sunucuda yapılır.

Bakım hatırlatmaları bir hedef tarih, hedef kilometre veya ikisi birlikte kullanılarak oluşturulur. Sistem aracın kayıtlı güncel kilometresini hedefle karşılaştırır; hedefe 500 km veya 7 gün kaldığında “yaklaşıyor”, hedef geçildiğinde “gecikti” durumunu üretir. Randevu ve hatırlatma değişiklikleri hesap bazında izole edilir ve denetim geçmişine yazılır. Gizlilik yaklaşımı gereği bu modülde müşteri adı, telefon veya açık plaka tutulmaz.

### AI deney ve değerlendirme laboratuvarı

Önce tamamlanmış iş emri usta onaylı vaka olarak işaretlenir. **AI deneyleri** ekranında bu vaka beklenen doğru cevap seçilir ve aynı arızayı anlatan bağımsız bir müşteri sorgusu yazılır. Beklenen vakanın kayıt metnini doğrudan sorguya kopyalamak veri sızıntısı oluşturacağı için arayüz bunu özellikle uyarır.

Deney çalıştırıldığında aynı veri seti anahtar kelime, semantik ve hibrit aramayla değerlendirilir:

- **Hit@K:** Beklenen doğru vakanın ilk K sonuç içinde bulunma oranı.
- **MRR:** Doğru vakanın sonuç listesindeki sırasını ödüllendiren ortalama ters sıra değeri.
- **Ortalama gecikme:** Bir sorgunun sonuçlanma süresi.

Sonuçlar yöntem ve sorgu bazında veritabanında saklanır. Akıllı asistandaki **Kanıtlı öneri oluştur** seçeneği yalnızca usta onaylı vakaları getirir; en güçlü vakanın doğrulanmış arıza, işlem ve sonuç bilgisini kaynak olarak gösterir. Güven düzeyi vaka sayısı ve benzerlik puanına göre hesaplanır. Çıktı kesin teşhis değildir ve fiziksel kontrol gerektirir.

### Stok ve parça yönetimi

Her parça hesap içinde benzersiz bir stok koduna sahiptir. Başlangıç miktarı, alış/satış fiyatı, ölçü birimi ve kritik stok sınırı kaydedilir. Manuel stok giriş ve çıkışları hareket geçmişinde izlenir; stok eksiye düşürülemez. Faturada stok kartına bağlı bir parça kullanıldığında gerekli miktar eşzamanlı işlemlere karşı kilitlenerek kontrol edilir, fatura ile stok hareketi aynı veritabanı işlemi içinde kaydedilir. Fatura oluşmazsa stok değişikliği de geri alınır.

### Fatura ve ödeme takibi

Finans ekranında bir iş emri için parça, işçilik ve diğer maliyet kalemleri eklenir. Ara toplam, indirim, KDV ve genel toplam sunucuda yeniden hesaplanır. Bir faturaya birden fazla kısmi ödeme girilebilir; bakiye sıfıra ulaştığında fatura otomatik olarak ödendi durumuna geçer. Kalan bakiyeyi aşan ödeme kabul edilmez.

`Kart / harici POS` yöntemi gerçek kart çekimi yapmaz; yalnızca ayrı bir POS cihazında alınmış ödemenin muhasebe kaydını tutar. `3D Secure test kartıyla öde` seçeneği ise eğitim amaçlı kart formunu ve yerel test bankası ekranını açar.

### Test kartı ve 3D Secure simülasyonu

- Test kartı: `4242 4242 4242 4242`
- Son kullanma tarihi: `12/30`
- CVV: `123`
- Başarılı 3D Secure kodu: `123456`
- Diğer 6 haneli kodlar: hatalı
- İşlem süresi: varsayılan 5 dakika
- Hatalı kod sınırı: varsayılan 3 deneme

Kart numarası, son kullanma tarihi ve CVV yalnızca React sayfasının geçici belleğinde doğrulanır; API'ye yalnızca tutar ve test kartının son dört hanesi gönderilir. 3D bağlantı anahtarının kendisi yerine SHA-256 hash'i veritabanında saklanır. Başarılı doğrulama ödemeyi faturaya yalnızca bir kez ekler; tekrar gönderilen aynı başarılı istek çift tahsilat oluşturmaz.

Bu özellik gerçek banka/ödeme kuruluşu entegrasyonu değildir. Üretimde gerçek kart alanları uygulamanın kendi backend'inden geçirilmemeli; PCI uyumlu bir ödeme sağlayıcısının barındırdığı form veya tokenizasyon çözümü kullanılmalıdır. Finans kayıtları resmi e-Fatura/e-Arşiv yerine geçmez.

### Kayıt ve yerel kodla giriş

Yeni kullanıcı önce kayıt ekranında profil ve iletişim bilgilerini girer. Telefon numarası ülke kodundan ayrı tutulur ve yalnızca 6-15 rakam kabul eder. Gizlilik aydınlatması ile kullanım şartları onaylanmadan kayıt tamamlanmaz.

- Geliştirme giriş kodu: `111111`
- Kod yalnızca daha önce kayıt olmuş bir e-posta adresiyle kullanılabilir.
- Başarılı girişte rastgele oturum anahtarı `HttpOnly` çerezle taşınır; veritabanında yalnızca anahtarın hash'i saklanır.
- `LOCAL_AUTH_ENABLED=true` ve sabit kod yalnızca yerel geliştirme içindir. Gerçek ortamda kapatılmalıdır.
- Gerçek ortamda `AUTH_SECRET` uzun ve rastgele bir değere, `AUTH_COOKIE_SECURE=true` olarak ayarlanmalı; `SMTP_*` değerleri gerçek e-posta sağlayıcısıyla değiştirilmelidir.

Mailpit servisi ileride gerçek e-posta OTP akışı yeniden etkinleştirildiğinde test posta kutusu olarak kullanılmak üzere yapılandırmada korunur. Yerel `111111` akışında e-posta gönderilmez.

### Hesap bazlı veri yönetimi

Her yeni araç `owner_id` ile oturum açmış hesaba bağlanır. Araç listeleri, iş emirleri, dashboard istatistikleri ve benzer vaka araması sunucu tarafında bu sahiplik bilgisine göre filtrelenir. Aynı anonim araç kodu farklı servis hesaplarında kullanılabilir; aynı hesap içinde tekrar kullanılamaz.

Hesap, giriş, profil, araç ve iş emri işlemleri `audit_events` tablosuna kaydedilir. Denetim geçmişinin son kayıtları **Hesap ayarları** ekranında görülebilir. Gizli giriş kodu veya oturum anahtarı denetim verisine yazılmaz.

### Yerel yapay zekâ modelleri

- Ses modeli: `faster-whisper/small`, CPU üzerinde INT8
- Embedding modeli: `intfloat/multilingual-e5-small`, 384 boyut
- Vektör veritabanı: PostgreSQL + pgvector, cosine HNSW indeksi

Modeller ilk kullanımda `model_cache` Docker volume'üne indirilir ve sonraki açılışlarda yeniden indirilmez. İlk model indirmesi internet hızına göre birkaç dakika sürebilir. Mevcut iş emirlerinin embedding alanını yeniden üretmek için:

```powershell
docker compose exec -T backend python -m app.backfill_embeddings
```

Embedding modeli geçici olarak yüklenemezse uygulama bunu anlamsal model olarak göstermeden deterministik bir metin-vektörü yedeğine düşer.

PostgreSQL, bilgisayardaki mevcut servislerle çakışmaması için dışarıya `localhost:55432` üzerinden açılır. Docker içindeki servisler kendi aralarında standart 5432 portunu kullanır. Arayüz de aynı nedenle 5174 portundadır.
Bu projeye ait Mailpit arayüzü, bilgisayardaki diğer geliştirme servisleriyle çakışmaması için 8026 portundadır.

## Durdurma

```bash
docker compose down
```

Veritabanını da sıfırlamak için yalnızca gerçekten gerektiğinde:

```bash
docker compose down -v
```

Bu komut geliştirme veritabanındaki tüm kayıtları siler.

## VS Code

Klasörü VS Code ile açın:

```bash
code .
```

Önerilen eklentiler `.vscode/extensions.json` içinde listelenmiştir.

## Kontroller

Çalışan Docker servisleri üzerinde backend testleri, frontend lint ve production build kontrolü:

```powershell
.\scripts\check.ps1
```

Komut; backend testlerini, frontend lint kontrolünü, TypeScript production derlemesini ve canlı API sağlık kontrolünü birlikte çalıştırır.

## Mimari

```text
React/Vite arayüzü
        |  HttpOnly oturum çerezi
        v
FastAPI REST API ----> Mailpit / SMTP
        |
        v
PostgreSQL + pgvector (kullanıcı, OTP hash'i, oturum hash'i ve servis verisi)
```

## Gizlilik

Araştırma verisinde müşteri adı, telefon ve açık plaka saklanmamalıdır. Araçlar anonim kodlarla temsil edilmelidir. Ses kaydı için açık rıza alınmalıdır. Uygulama ham sesi varsayılan olarak transkripsiyondan hemen sonra siler ve yalnızca kullanıcı tarafından doğrulanacak metni arayüze döndürür.

