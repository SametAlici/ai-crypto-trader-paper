# Günlük ileriye dönük sanal işlem kaydı

27 Ekim 2026 UTC’den başlayarak, dondurulmuş iki momentum stratejisini her gece aynı Freqtrade motoruyla yeniden hesaplar. **[Güncel sonuçlar](results/README.md)**.

| İzlek | Evren | Pozisyon limiti |
|---|---|---:|
| R1 | BTC, ETH, SOL / USDT | 3 |
| R5 | 33 coin / USDT | 5 |

Başlangıç sanal bakiyesi her izlek için 1.000 USDT’dir. Stratejiler günlük mumlar kullanır; sinyal kapanmış mumdan gelir, giriş sonraki mumun açılışındadır. Her yönde %0,15 komisyon/kayma varsayılır ve korumalar etkindir. AI kullanılmaz. Strateji dosyaları dondurulduğu haliyle korunur; bu kayıt için optimize edilmez.

API anahtarı gerekmez; exchange key/secret boş, `dry_run: true`, Telegram ve API sunucusu kapalıdır. Çalıştırıcı yalnızca veri indirme ve backtest komutlarını çağırır. Gerçek emir göndermez. **sanal işlem / tarihsel simülasyon, yatırım tavsiyesi değildir**. Sonuçlar gelecekteki getiriyi kanıtlamaz.

## Çalışma biçimi

GitHub Actions her gün 00:20 UTC’de veya elle `workflow_dispatch` ile çalışır. Public GitHub deposunda standart Ubuntu runner kullanılır; ücretli API, sunucu veya servis gerekmez. GitHub zamanlamayı geciktirebilir; public depolarda 60 günlük depo hareketsizliği sonrası zamanlanmış workflow durabilir ([GitHub açıklaması](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#schedule)). `main` varsayılan dal olmalı ve Actions yazma yetkisi açık olmalıdır; dal koruması botun sonuç commit’ini engelleyebilir.

1. Kaynak secret taramasından geçer; sabit sürümler kurulur, testler çalışır.
2. 33 paritenin 2025-01-01’den itibaren 1d verisi indirilir (başlangıçtan önce 400’den fazla ısınma mumu).
3. Açık UTC gününün mumu dosyalardan çıkarılır. Eksik veya eski veri varsa işlem başarısız olur; kısmi sonuç yayımlanmaz.
4. İki izlek `--timerange 20261027- --fee 0.0015 --enable-protections --export trades --cache none` ile hesaplanır. İlk tam gün henüz kapanmadıysa motor çalıştırılmaz; başlangıç bakiyesi ve “Başlamadı” kaydı üretilir.
5. `results/<izlek>/summary.json`, `equity.csv` ve Türkçe sonuç tablosu yazılır. Yeniden secret taramasından sonra sadece `results/` değişiklikleri bot tarafından `main` dalına commit edilir.

Geçmişten bugüne tekrar hesaplamak, sabit strateji ve sabit veri varsayımıyla tekrarlanabilir bir ileri dönem simülasyonudur. Borsanın geçmiş mum veya piyasa kurallarını değiştirmesi geçmiş sonucu değiştirebilir. Ağ/işlem gecikmeleri ve gerçek emir gerçekleşmeleri modellenmez. Veri her gece yeniden indirilir; OHLCV, ham backtest arşivleri ve yerel günlükler yayımlanmaz.

### Dönem sonu ve değerleme

Freqtrade 2026.9 açık işlemleri son mumun **açılış fiyatında** `force_exit` ile kapatır ve son mumda yeni giriş yapmaz. Bu işlemler raporda “açık (değerleme)” olarak ayrılır; kapalı işlem sayısına dahil edilmez. Bakiye, bu çıkış komisyonunu da içeren motor net değeridir. Son günün sonucu sonraki çalışmada değişebilir; bunu kesintisiz çalışan bir dry-run botunun birebir emir kaydı olarak yorumlamayın.

`equity.csv` başlangıç bakiyesini ve günlük net değerlemeyi içerir. Normal günlerde açık pozisyonlar gün kapanışında, çıkış maliyeti düşülerek değerlenir. Son satır motor bakiyesiyle uzlaştırılır: terminal pozisyonlarda son mum açılışı kullanılır. `max_drawdown_pct` bu günlük eğrinin zirveden düşüşüdür; `engine_max_drawdown_pct` motorun işlem kapanışlarına dayalı ayrı ölçüsüdür. Gün içi düşüş ölçülmez. Açık pozisyonların giriş tarihi/fiyatı ve değerleme tarihi/fiyatı JSON’da bulunur.

Al-tut her izleğin **kendi** paritelerine eşit başlangıç ağırlığı verir, yeniden dengeleme yapmaz. Başlangıç gününün açılışından son kapanmış günün kapanışına kadar, her yönde aynı %0,15 maliyetle hesaplanır. Dönem başlamadan karşılaştırma alanı boştur. Boş işlem listeleri geçerli bir sonuçtur.

### ABD runner’larında veri erişimi

ccxt **4.5.90** kaynak kodu ve gerçek isteklerle doğrulanan spot anahtarı `urls.api.public`’tir. Hem `ccxt_config` hem `ccxt_async_config` bunu `https://data-api.binance.vision/api/v3` olarak değiştirir; `options.fetchMarkets.types = ["spot"]` futures piyasalarının yüklenmesini engeller. `fetchCurrencies` kapalıdır. `exchangeInfo` ve `klines` bu hostta çalışır. `scripts/freqtrade_public.py` senkron ve asenkron ccxt isteklerini kontrol eder; Vision dışına giden herhangi bir isteği **göndermeden önce** hata verir ve izinli istekleri günlüğe yazar. Böylece erişilebilen yerel `api.binance.com` bu testi maskeleyemez. Freqtrade’in kendi `download-data` komutu çalıştığından özel feather indiricisine gerek yoktur; dosyalar ayrıca Freqtrade’in kendi yükleyicisiyle okunup doğrulanır.

Freqtrade’in bu sürümü kapalı `api_server` bölümü için bile kimlik doğrulama alanları ister. Kaynak config’lerde bölüm açıkça kapalıdır; çalıştırıcı geçici runtime config’inden bu kullanılmayan bölümü çıkarır. Kullanıcı adı, parola veya JWT sırrı eklenmez. `FREQTRADE__*` ortam değişkenleri alt süreçlere aktarılmaz.

## Yerel çalıştırma

Python 3.12 ve uv ile (önbellekler proje içindedir):

```sh
UV_CACHE_DIR=.uv-cache uv venv --python 3.12 .venv
UV_CACHE_DIR=.uv-cache uv pip install --python .venv/bin/python --only-binary=TA-Lib -r requirements.txt
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
.venv/bin/python scripts/run_forward.py
.venv/bin/python scripts/validate_engine.py
.venv/bin/python scripts/secret_scan.py
```

`validate_engine.py`, indirilen veri üzerinde iki izleği 2026-09-01’den itibaren ve tek mum/işlemsiz sınır durumunu geçici dizinde sınar; ileri dönem sonuçlarını değiştirmez.

TA-Lib 0.8.2 için CPython 3.12 manylinux x86-64 wheel’i mevcuttur ([PyPI](https://pypi.org/project/TA-Lib/0.8.2/#files)); CI `--only-binary=TA-Lib` kullanarak kaynak derlemeyi engeller. Freqtrade 2026.9, ccxt 4.5.90 ve hesaplamada kullanılan NumPy/pandas/technical sürümleri kaynak projenin kilidiyle aynıdır. Gereksiz FreqAI bağımlılıkları alınmamıştır.

Secret tarayıcısı `.env` ve `.env.*` dosyalarını (örnekler dahil), yaygın anahtar/token biçimlerini ve boş olmayan kimlik bilgisi atamalarını reddeder. Eşleşen değerleri yazdırmaz. Tüm sır biçimlerini tanıdığı iddiası yoktur; yayımlanacak dosyaları ayrıca gözden geçirin. `.gitignore` veri, günlük, veritabanı, ortam ve önbellek dosyalarını dışlar.
