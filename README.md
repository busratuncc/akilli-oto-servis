# Akıllı Oto Servis

Türkçe servis anlatımlarını yapılandırılmış iş emirlerine dönüştürmek, atölyedeki servis sürecini izlemek, OBD-II kodlarını kaydetmek ve geçmiş vakalar arasında arama yapmak için geliştirilen tez uygulaması.

## Mevcut uygulama (v0.5)

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

Uygulama menüsü dört bölümden oluşur: **Gösterge paneli**, **Araçlar**, **İş emirleri** ve **Akıllı asistan**.

### Kayıt ve yerel kodla giriş

Yeni kullanıcı önce kayıt ekranında profil ve iletişim bilgilerini girer. Telefon numarası ülke kodundan ayrı tutulur ve yalnızca 6-15 rakam kabul eder. Gizlilik aydınlatması ile kullanım şartları onaylanmadan kayıt tamamlanmaz.

- Geliştirme giriş kodu: `111111`
- Kod yalnızca daha önce kayıt olmuş bir e-posta adresiyle kullanılabilir.
- Başarılı girişte rastgele oturum anahtarı `HttpOnly` çerezle taşınır; veritabanında yalnızca anahtarın hash'i saklanır.
- `LOCAL_AUTH_ENABLED=true` ve sabit kod yalnızca yerel geliştirme içindir. Gerçek ortamda kapatılmalıdır.
- Gerçek ortamda `AUTH_SECRET` uzun ve rastgele bir değere, `AUTH_COOKIE_SECURE=true` olarak ayarlanmalı; `SMTP_*` değerleri gerçek e-posta sağlayıcısıyla değiştirilmelidir.

Mailpit servisi ileride gerçek e-posta OTP akışı yeniden etkinleştirildiğinde test posta kutusu olarak kullanılmak üzere yapılandırmada korunur. Yerel `111111` akışında e-posta gönderilmez.

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

