# Ön kayıt — 26 Ekim 2026

Bu protokol yeni evrenler için herhangi bir backtest çalıştırılmadan yazıldı.
Geçmiş performans evren veya parametre seçmek için kullanılmaz. Snapshot bir kez
alınır; başarısız veri erişimi veya kapanmamış dönem yerine liste uydurulmaz.

- R1 değişmez: BTC/ETH/SOL, 3 slot, R1_TSMomentum.
- R5 değişmez: mevcut 33 coin ve sırası, 5 slot, R5_TSMomentum.
- R6 “Büyük coinler”: CoinGecko ücretsiz /api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=100&page=1
  snapshot anında piyasa değeri sırasıyla taranır. Stablecoin, wrapped/staked/bridged
  token, aktif Binance spot USDT çifti olmayan veya 2026-10-27 öncesi 400 günlük
  mumu olmayanlar çıkarılır; ilk 10 kalana kadar aşağı inilir. 5 slot.
- R7 “Geniş evren”: Binance exchangeInfo TRADING spot USDT çiftleri; stablecoin,
  fiat, leveraged UP/DOWN/BULL/BEAR, wrapped/staked/bridged token ve 400 günlük
  geçmişi olmayanlar çıkarılır. 2026-09-27 dahil / 2026-10-27 hariç 30 kapalı UTC
  günlük mumun quoteAssetVolume toplamına göre ilk 70 seçilir. Eşitlikte sembol
  alfabetik sırası kullanılır. JUP (Jupiter), UP kaldıraç tokenı değildir ve
  yalnız son iki harfi nedeniyle çıkarılmaz. 5 slot.
- R8 “Geniş + çok pozisyon”: R7 ile aynı evren ve sıra; 10 slot.
- R6/R7/R8 aynı R5_TSMomentum kodunu kullanır; yalnız whitelist,
  max_open_trades ve r5.position_cap_slots değişir.
- Her izlek: 2026-10-27 UTC başlangıç, 1000 USDT, tek yön 0.0015 ücret,
  --enable-protections, data-api.binance.vision. R7/R8 ayrıca 0.0025 ücretle
  bağımsız stress koşusu; ücret karşılaştırması ana kaydı değiştirmez.
- Al-tut her izleğin kendi evrenine eşit başlangıç ağırlığı verir.
- JSON snapshot'ları zaman damgası, kaynak, türetilmiş aday/ret listeleri ve
  seçilen sıralı listeyi tutar; tam API yanıtları veya sırlar tutulmaz.
- CoinGecko hatalarında üstel geri çekilme; kalıcı hatada dur. Kapanmamış hacim
  penceresinde dur. Snapshot hazır olmadan nightly veya yeni backtest çalışmaz.
- Config whitelist sırası kayıtlı sırasıdır. Kurulu Freqtrade 2026.9
  optimize/backtesting.py _time_pair_generator_det önce açık işlemleri işler,
  ardından pairs listesini dict.fromkeys ile sırasını koruyarak dolaşır.
  StaticPairList ve veri yükleyici whitelist sırasını korur. Boş slotu aşan
  eşzamanlı girişlerde bu sıra belirleyicidir; sıralama yeniden optimize edilmez.
- Delist edilen çift son kullanılabilir kapanışla değerlenir; ileri doldurma
  yalnız delist doğrulamasından sonra uygulanmalıdır. Motorla ilgili ayrım:
  kurulu Freqtrade 2026.9 handle_left_open son satırın OPEN_IDX fiyatını kullanır,
  son kapanışı değil. Bu nedenle “Freqtrade son kapanış kullanır” iddiası doğru
  değildir. Otomatik delist desteği yoksa sağlık kontrolü durur; sessizce çift
  çıkarılmaz. Bu sınır ve motor dönem sonu değerlemesi raporda belirtilir.

R1→R6→R5→R7 evren genişliği karşılaştırmasıdır; R6/R5/R7 5 slotta sabittir,
ama R1 3 slottur (R1→R6 salt evren etkisini izole etmez). R7→R8 aynı evrende
slot sayısını test eder. Sonuç tabloları net getiri ve günlük max DD sıralarını
ayrı gösterir. Hiçbiri gerçek işlem veya kâr garantisi değildir.
