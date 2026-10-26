# Günlük ileriye dönük sanal işlem kaydı

27 Ekim 2026 UTC’den başlayarak, dondurulmuş momentum kurallarını beş izlekte her gece aynı Freqtrade motoruyla yeniden hesaplar. **[Güncel sonuçlar](results/README.md)**.

| İzlek | Evren | Pozisyon limiti |
|---|---|---:|
| R1 | BTC, ETH, SOL / USDT | 3 |
| R5 | 33 coin / USDT | 5 |
| R6 | Piyasa değeri ilk 10 uygun coin | 5 |
| R7 | 30 günlük USDT hacmi ilk 70 uygun coin (snapshot bekliyor) | 5 |
| R8 | R7 ile aynı evren ve sıra (snapshot bekliyor) | 10 |

Başlangıç sanal bakiyesi her izlek için 1.000 USDT’dir. Stratejiler günlük mumlar kullanır; sinyal kapanmış mumdan gelir, giriş sonraki mumun açılışındadır. Her yönde %0,15 komisyon/kayma varsayılır ve korumalar etkindir. AI kullanılmaz. Strateji dosyaları dondurulduğu haliyle korunur; bu kayıt için optimize edilmez.

API anahtarı gerekmez; exchange key/secret boş, `dry_run: true`, Telegram ve API sunucusu kapalıdır. Çalıştırıcı yalnızca veri indirme ve backtest komutlarını çağırır. Gerçek emir göndermez. **sanal işlem / tarihsel simülasyon, yatırım tavsiyesi değildir**. Sonuçlar gelecekteki getiriyi kanıtlamaz.

## Çalışma biçimi

GitHub Actions her gün 00:20 UTC’de veya elle `workflow_dispatch` ile çalışır. Public GitHub deposunda standart Ubuntu runner kullanılır; ücretli API, sunucu veya servis gerekmez. GitHub zamanlamayı geciktirebilir; public depolarda 60 günlük depo hareketsizliği sonrası zamanlanmış workflow durabilir ([GitHub açıklaması](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#schedule)). `main` varsayılan dal olmalı ve Actions yazma yetkisi açık olmalıdır; dal koruması botun sonuç commit’ini engelleyebilir.

1. `frozen.json` kontrolü en başta çalışır; strateji veya config değişmişse test durur. Kaynak secret taramasından geçer; sabit sürümler kurulur, testler çalışır.
2. Beş izleğin birleşik paritelerinin 2025-01-01’den itibaren 1d verisi indirilir (başlangıçtan önce 400’den fazla ısınma mumu).
3. Açık UTC gününün mumu dosyalardan çıkarılır. Eksik veya eski veri varsa işlem başarısız olur; kısmi sonuç yayımlanmaz.
4. Beş izlek `--timerange 20261027- --fee 0.0015 --enable-protections --export trades --cache none` ile hesaplanır. R7/R8 ayrıca 0.0025 ücretle sınanır. İlk tam gün henüz kapanmadıysa motor çalıştırılmaz; başlangıç bakiyesi ve “Başlamadı” kaydı üretilir.
5. `results/<izlek>/summary.json`, `equity.csv` ve Türkçe sonuç tablosu yazılır. Yeniden secret taramasından sonra `results/health.json` dahil sadece `results/` değişiklikleri bot tarafından `main` dalına commit edilir.

Geçmişten bugüne tekrar hesaplamak, sabit strateji ve sabit veri varsayımıyla tekrarlanabilir bir ileri dönem simülasyonudur. Borsanın geçmiş mum veya piyasa kurallarını değiştirmesi geçmiş sonucu değiştirebilir. Ağ/işlem gecikmeleri ve gerçek emir gerçekleşmeleri modellenmez. OHLCV önbelleği geri yüklenir ve veri kuyruğu her gece güncellenir; OHLCV, ham backtest arşivleri ve yerel günlükler yayımlanmaz.

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
`scripts/build_site.py` ile registry’deki beş `results/<izlek>`, ayrı `results/reference/<izlek>` raporları ve
`results/health.json` dosyalarından oluşturulur. Modern, mobil uyumlu koyu
sayfa; UTC ve Türkiye saatini, getiriyi, günlük en büyük düşüşü, kapalı/açık işlem
sayılarını ve işlem tablolarını gösterir. Grafik, başlangıcı 100 olan yerel SVG’dir;
harici JavaScript, CDN veya izleyici yoktur. Dönem öncesi “Başlamadı” gösterilir.

Üstte ileriye dönük kayıt, referans geçmiş ve araştırma özeti arasında geçiş yapılır.
Beş izlek ve her birinin kendi al-tut evreni seçilebilir; referans geçmişte yalnız R1/R5 vardır. 1G, 1H (hafta), 1A, 3A, 6A, 12A ve Tümü
filtreleri günlük veriden tarayıcıda hesaplanır. Yetersiz geçmişte uyarı verilir ve
tüm veri kullanılır. Grafikler yerel SVG; veri sayfada kaçırılmış JSON’dur. Harici
kütüphane, CDN, izleyici veya ağ isteği kullanılmaz. JavaScript kapalıysa kaynak
CSV/JSON dosyaları kullanılabilir. Mobil tablolar kendi içinde yatay kayar.

```sh
.venv/bin/python scripts/build_site.py
.venv/bin/python scripts/secret_scan.py
```

Çıktı `site/index.html`, `site/style.css`, yerel `site/app.js`, `site/metrics.js` ve
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
(beş izlek, kendi B&H sonuçları, açık pozisyon sayıları ve site bağlantısı) gönderilir. Motor veya Pages
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

## Dondurma ve sistem sağlığı

`scripts/freeze_check.py`, iki stratejinin tam dosya baytlarını, beş config’in
anahtarları sıralanmış tam JSON içeriğini ve evren/protokol/registry dosyalarını SHA256 ile denetler. Böylece trading
parametreleri, pariteler ve güvenlik ayarları da korunur; yalnızca JSON boşlukları
etkisizdir. `frozen.json` başlangıç kaydıdır; nightly bunu yenilemez. Kontrol hatası
Telegram’da **“Strateji dosyaları değişmiş — test donduruldu”** olarak bildirilir.

Koşu öncesi yerel veri durumu ve indirme sonrası durum denetlenir; tüm motor
koşularından sonra tekrar denetlenir. Son kapalı 1d mum her paritede dün UTC olmalı;
START_DATE’ten beri arada gün atlanmamalıdır. Daha sıkı indirme kontrolü 2025’ten
beri ısınma verisini de doğrular. `listing_dates.json`, Binance public klines
`startTime=0&limit=1` yanıtından alınan ilk günlük mum tarihlerini kaydeder;
yalnızca bu doğrulanmış listeleme öncesi günler mazur görülür. İlk mumdan önceki
rastgele veri boşluğu listeleme sayılmaz. Geçersiz fiyat/hacim ve tekrar eden günler
reddedilir. Başarısız koşuda beş izleğin sonuçları yayımlanmaz; sağlık günlüğü
başarısızlığı kaydeder. İlk indirme öncesi eski yerel veri, indirme sonrası düzelirse
koşu başarılı sayılır. `results/health.json` başarı, UTC koşu zamanı, süre, veri
tazeliği, iyi/eksik pariteler ve öncesi/sonrası kontrollerini tutar. Aynı gündeki
tekrarlar beklenen/gerçekleşen günlük çalışma hesabında bir kez sayılır.
Beklenen ilk çalışma 28 Ekim 2026 00:20 UTC’dir. Sitede son 30 koşu gösterilir;
günlük dosyasındaki daha eski kayıtlar korunur. Başarısız sağlık kaydı da secret
taramasından sonra nightly tarafından commit edilir; site son başarılı raporda kalır.
Telegram net getiri, her izleğin kendi al-tut getirisi, komisyon, açık pozisyon
sayıları ve gerekiyorsa sağlık uyarısını içerir. Sırlar yalnızca env’den alınır.

## Metriklerin anlamı

`summary.json` brüt kâr, ücretler ve net kârı USDT olarak içerir. Ücret,
`amount × open_rate × fee_open + amount × close_rate × fee_close` toplamıdır;
`fee_open/fee_close` oran değerleridir. Brüt = net + ücret. Dönem sonu açık
pozisyonlar için motorun varsayımsal çıkış ücreti dahildir; gerçek ödenmiş ücret
veya gerçek emir yoktur. Net kâr ve coin katkıları açık değerlemeyi içerir.

Kazanma oranı, ortalama kazanç/kayıp ve en iyi/ilk üç işlem ölçüleri yalnızca
kapalı işlemlerden gelir. Paylar net kâr pozitif değilse tanımsız (`null`);
yok sayılan “en iyi işlem” en yüksek net sonuçlu kapalı işlemdir (hepsi kayıpsa
en küçük kayıp). “En iyi işlem olmadan” bu katkının çıkarılmasıdır; portföy yeniden
çalıştırılmaz. Dönem filtresinde kapanan işlemin yalnızca o dönemdeki net değer
katkısı kullanılır; önceki dönemde birikmiş kâr tekrar sayılmaz. Kazanma oranı ise
kapanan işlemin tüm yaşamındaki net sonuca bakar. Günlük getiriler ardışık net
değerlerin oranıdır; aylık getiriler bunların bileşiğidir. Calmar yıllık bileşik
getiri / günlük max düşüş olup 30 günden az veride veya sıfır düşüşte gösterilmez.
Günlük per-coin/per-trade kümülatif katkılar dönem hesaplarının girdisidir.
`trades.csv` ve `daily_returns.csv`, özet JSON’a ek dışa aktarımlardır.

### Stop modeli

Backtest −%30 stoploss’u günlük mumun en düşük fiyatıyla, borsada bekleyen bir stop
emri varmış gibi sınar. Bu iyimserdir: fiyat boşlukları ve kayma nedeniyle gerçek
emir stopun altında gerçekleşebilir. Gerçek emir yoktur. Canlı sürümde borsa
tarafında gerçek bir stop emri gerekir. Bu not strateji veya stop ayarını değiştirmez.

## Geçmiş simülasyon (referans)

**Geçmiş simülasyon (referans) — ileriye dönük test değildir; bu dönem strateji geliştirmede kullanıldı**

`results/reference/r1` ve `results/reference/r5` içindeki sabit snapshot,
2024-01-01 00:00 UTC ≤ tarih < 2026-10-26 00:00 UTC dönemini kapsar.
Son kapalı mum 25 Ekim’dir; 26 Ekim’in kapanmamış mumu dahil değildir.
Aynı dondurulmuş strateji/config, 0.0015 ücret, `--enable-protections` ve
400 günlük ısınma gereksinimini karşılayan 2022-11-01’den başlayan veri kullanılır.
Referans bir kez `scripts/run_reference.py` ile çalıştırılmıştır; nightly bunu
çağırmaz ve script mevcut referans klasörünü yeniden yazmayı reddeder. Kendi
SHA256 kayıtları özetlerde bulunur. İleriye dönük kayda birleştirilmez.

Kontroller ve site üretimi:

```sh
.venv/bin/python scripts/freeze_check.py
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
.venv/bin/python scripts/build_site.py
.venv/bin/python scripts/secret_scan.py
```

Tarayıcı hesaplarının sentetik testleri Node.js gerektirir (GitHub Ubuntu runner’da
mevcuttur). Site üretimi Python standart kütüphanesiyle çalışır.

## Beş track protokolü ve araştırma özeti

Ön kayıt ve seçim kuralları: [`universes/PROTOCOL.md`](universes/PROTOCOL.md).
Tek registry `scripts/tracks.py` içindedir. R1/R5 strateji ve config hash'leri
korunmuştur. R6 piyasa değeri ilk 10 / 5 slot, R7 hacim ilk 70 / 5 slot,
R8 R7 ile aynı sıra / 10 slottur. R6/R7/R8 yalnız config farklarıyla
R5_TSMomentum kullanır. Nightly birleşik pariteleri bir kez indirir; sağlık
kontrolü hepsini kapsar. Her track kendi eşit ağırlıklı al-tutuyla karşılaştırılır.
R7/R8 için %0,25 ücretle ayrı motor koşusu ve eğri vardır.

Snapshot komutu `.venv/bin/python scripts/build_universes.py` yalnız public API
kullanır; hazır R6'yı değiştirmez, hazır R7'yi yeniden yazmayı reddeder.
2026-10-26 günü yapılan gerçek denemede R6 elde edildi; R7 için istenen son günlük
mum henüz kapanmadığından R7/R8 pending kalır. **2026-10-27 00:00 UTC sonrasında**
aynı komutla R7 snapshot tamamlanmalıdır; bunu geçmiş performansa bakmadan yapın.
Pending whitelist ile çalıştırıcı veri indirmeden/backtest'ten önce durur.
Snapshot script'i yeni config/evren hash'lerini frozen.json'a ekler. Yeni track'ler
hazır olana kadar site açıkça snapshot beklendiğini gösterir. Mevcut referans
geçmişi yalnız R1/R5'tir; yeni track'lere tarihsel referans üretilmez.

Workflow 20 dakikalık üst sınıra sahiptir; UTC tarih + evren/config hash'ine bağlı
`actions/cache` önce önceki günün OHLCV'sini geri yükler, Freqtrade eksik kuyruğu
indirir. 20 dakikanın altında gerçek beş-track motor süresi, R7 kapanış verisi
olmadan henüz ölçülemez; timeout bir performans kanıtı değildir.

`research/` yalnız private projenin `exports/research_snapshot.json` ve
`exports/research_equity/*.csv` dosyalarının byte-identical kopyasıdır.
`scripts/import_research.py` tüm dosyaları **kopyalamadan önce** mevcut secret
scanner ile tarar; bulguda hiçbir dosya kopyalamaz. Site build'i tekrar tarar ve
alan izin listesi kullanır. Private kaynak değiştirilmez. “Araştırma özeti” ayrı
üst sekmedir; kanıt türleri birbirine karıştırılmaz. Tarihsel simülasyon; bu
veriler strateji geliştirmede kullanıldı; ileriye dönük test değildir.

Delisting konusunda motor kaynak doğrulaması: Freqtrade 2026.9 `handle_left_open`
son kullanılabilir mumun **açılışını** kullanır. “Freqtrade son kapanışı kullanır”
ifadesi doğru değildir. İstenen son kapanış muhasebesi ayrıca uygulanmadan bunu
motor davranışı diye sunmuyoruz; mevcut sağlık kontrolü eksilen veride durur ve
kısmi rapor yayımlamaz. Normal dönem sonu motor değerlemesi değişmemiştir.
