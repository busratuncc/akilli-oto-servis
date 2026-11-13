# Akıllı Oto Servis

Türkçe servis anlatımlarını yapılandırılmış iş emirlerine dönüştürmek, OBD-II kodlarını kaydetmek ve geçmiş vakalar arasında arama yapmak için hazırlanmış tez projesi temeli.

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

Konuşma tanıma, LLM tabanlı yapılandırılmış çıkarım, embedding üretimi ve kanıta dayalı RAG sonraki iterasyonlar için servis arayüzleri arkasına eklenecektir.

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

Araştırma verisinde müşteri adı, telefon ve açık plaka saklanmamalıdır. Araçlar anonim kodlarla temsil edilmelidir. Ses kaydı için açık rıza alınmalı; gerekli değilse ham ses silinip yalnızca doğrulanmış metin tutulmalıdır.

