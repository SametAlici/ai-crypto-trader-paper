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

## Trade Lab sitesi ve bildirimler

[Trade Lab — İleriye Dönük Sanal Test](https://trade.blacktowhitestudio.com),
`scripts/build_site.py` ile yalnızca `results/r1` ve `results/r5` altındaki
`summary.json` ve `equity.csv` dosyalarından oluşturulur. Modern, mobil uyumlu koyu
sayfa; UTC ve Türkiye saatini, getiriyi, günlük en büyük düşüşü, kapalı/açık işlem
sayılarını ve işlem tablolarını gösterir. Grafik, başlangıcı 100 olan yerel SVG’dir;
harici JavaScript, CDN veya izleyici yoktur. Dönem öncesi “Başlamadı” gösterilir.

Tek B&H kartı ve grafik çizgisi **R5’in 33 coinlik evrenine eşit başlangıç ağırlığı**
veren, yeniden dengelenmeyen pasif sepettir. R1’in kendi evrenindeki al-tut eğrisi
sonuç dosyalarında ayrıca bulunur. B&H düşüşü kendi günlük eğrisinden hesaplanır;
pasif sepete motorun işlem/açık pozisyon sayaçları uygulanmaz (—).

```sh
.venv/bin/python scripts/build_site.py
.venv/bin/python scripts/secret_scan.py
```

Çıktı `site/index.html`, küçük `site/style.css` ve
`trade.blacktowhitestudio.com` içeren `site/CNAME` dosyalarıdır. Üretilen HTML/CSS,
her derlemede yeniden yazılır; düzenleme kaynakları `scripts/build_site.py` ve
`scripts/site.css` dosyalarıdır. Yayımlamadan önce **üretilen site dahil** secret
taraması zorunludur. Site üreticisi yalnızca gerekli rapor alanlarını işler;
bilinmeyen JSON alanlarını sayfaya kopyalamaz ve parite metinlerini HTML için kaçırır.

Nightly workflow, doğrulanmış sonuçları commit ettikten sonra `main` dalını yeniden
alarak siteyi üretir ve resmi `configure-pages@v5`, `upload-pages-artifact@v4`,
`deploy-pages@v4` action’larıyla `github-pages` ortamına yayımlar.
`pages: write` ve `id-token: write` yalnızca Pages işine verilir.
`main` dalına `results/`, site üreticisi/CSS veya workflow değişikliği push edildiğinde
yalnızca site yayımlanır; motor yeniden çalıştırılmaz. Botun `GITHUB_TOKEN` ile yaptığı
sonuç push’u yeni workflow tetiklemez; aynı nightly çalışmasının Pages işi yayımlar.
Başarı ve hata durumları Türkçe Actions çalışma özetine yazılır.

İlk kurulumda depo Settings → Pages → Build and deployment → Source alanında
**GitHub Actions** seçilmeli; Custom domain alanına `trade.blacktowhitestudio.com`
yazılmalı, DNS’te `trade` CNAME kaydı `sametalici.github.io` hedefine yöneltilmelidir.
GitHub alan adını doğruladıktan ve sertifika hazır olduktan sonra HTTPS zorlaması
açılmalıdır. `CNAME` dosyası DNS’i veya GitHub ayarlarını tek başına değiştirmez.
Bkz. [özel Pages workflow’ları](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).

İsteğe bağlı Telegram bildirimi için Settings → Secrets and variables → Actions
altında `TELEGRAM_BOT_TOKEN` ve `TELEGRAM_CHAT_ID` depo sırlarını tanımlayın.
İkisi de varsa her zamanlanmış/elle nightly çalışma sonunda kısa Türkçe sonuç
(R1, R5, B&H, açık pozisyon sayıları ve site bağlantısı) gönderilir. Motor veya Pages
başarısızsa çalışma URL’siyle hata mesajı gönderilir. Eksik sırlarda script sessizce
atlar; push yayımlamalarında bildirim göndermez. Sırlar yalnızca bildirim adımının
ortamına aktarılır; komut satırına, kaynak dosyaya, HTML’e veya günlüğe yazılmaz.
HTTP hata ayrıntıları da sır içerebileceği için gizlenir. Testlerde ağ çağrısı yapılmaz.
Bildirim hatası çalışma özetine eklenir; yayımlanmış sonuçları geri almaz.
Freqtrade’in Telegram arayüzü kapalı kalır; bu ayrı bir raporlama scriptidir.

### Zamanlamayı canlı tutma

Ayın ilk UTC gününde (ve her elle çalıştırmada), nightly işinin keepalive adımı
`GITHUB_TOKEN` ve yalnızca o işe verilen `actions: write` ile
`PUT /repos/{owner}/{repo}/actions/workflows/nightly.yml/enable` çağırır.
İşlem idempotenttir; boş/sahte etkinlik commit’i oluşturmaz.
Nightly sonuç commit’leri **ancak gerçek değişiklik içeren bir commit oluşursa**
depo etkinliği sayılır; değişiklik yoksa commit yapılmaz.

GitHub, public depoda 60 gün etkinlik olmadığında zamanlamayı kapatabilir.
Keepalive adımı yalnızca workflow hâlâ çalışırken yürüyebilir; devre dışı kalmış
bir workflow kendi kendini kurtaramaz. Bu durumda Actions arayüzünden workflow’u
etkinleştirin veya yetkili bir oturumda `gh workflow enable nightly.yml` çalıştırın,
sonra elle bir çalışma başlatın. API ile yeniden etkinleştirme bir depo commit’i
oluşturmaz; bu adım 60 günlük sınırın kesin olarak aşılacağını garanti etmez.
Bkz. [GitHub etkinleştirme ve 60 gün kuralı](https://docs.github.com/en/actions/managing-workflow-runs-and-deployments/managing-workflow-runs/disabling-and-enabling-a-workflow).
