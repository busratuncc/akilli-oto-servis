# Akıllı Oto Servis

Türkçe servis anlatımlarını yapılandırılmış iş emirlerine dönüştürmek, atölyedeki servis sürecini izlemek, OBD-II kodlarını kaydetmek ve geçmiş vakalar arasında arama yapmak için geliştirilen tez uygulaması.

## Mevcut uygulama (v0.3)

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

Uygulama menüsü dört bölümden oluşur: **Gösterge paneli**, **Araçlar**, **İş emirleri** ve **Akıllı asistan**.

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
        |
        v
FastAPI REST API
        |
        v
PostgreSQL + pgvector
```

## Gizlilik

Araştırma verisinde müşteri adı, telefon ve açık plaka saklanmamalıdır. Araçlar anonim kodlarla temsil edilmelidir. Ses kaydı için açık rıza alınmalıdır. Uygulama ham sesi varsayılan olarak transkripsiyondan hemen sonra siler ve yalnızca kullanıcı tarafından doğrulanacak metni arayüze döndürür.

