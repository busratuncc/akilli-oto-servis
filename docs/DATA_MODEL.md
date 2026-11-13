# Araştırma veri modeli

## Temel ilke

Üretim kayıtları ile araştırma verisi ayrılmalıdır. Müşteri adı, telefon, açık plaka ve adres araştırma veri setine aktarılmamalıdır.

## Araç

- Anonim araç kodu
- Marka ve model
- Model yılı
- Motor ve yakıt tipi
- Kilometre

## Servis vakası

- Müşteri şikâyeti
- Gözlenen belirtiler
- OBD-II kodları
- Yapılan testler ve gözlemler
- Kesinleşen arıza
- Yapılan işlemler ve parçalar
- Onarım sonucu
- Aynı şikâyetle geri dönüş bilgisi
- Usta onayı

## Yapay zekâ izi

- Ham transkript
- Model/sağlayıcı adı ve sürümü
- Yapılandırılmış öneri
- Ustanın yaptığı düzeltmeler
- Kabul/red bilgisi
- Oluşturma ve onay zamanı

## Araştırma bölünmesi

- Eğitim/geliştirme ve test vakaları birbirinden ayrılmalıdır.
- Aynı servis vakasının farklı anlatımları farklı bölümlere düşmemelidir.
- Test kümesi deney tasarımı tamamlanmadan görülmemelidir.
- Gerçek, geçmişten hatırlanan ve senaryo olarak yazılan vakalar ayrı etiketlenmelidir.

