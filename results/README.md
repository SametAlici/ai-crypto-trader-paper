# İleriye dönük sanal işlem kaydı

Son güncelleme (UTC): 2026-11-19T07:28:46.975657+00:00

| İzlek | Durum | Bakiye (USDT) | Getiri | Aynı coinleri al-tut | Kapalı / açık | En büyük düşüş |
|---|---|---:|---:|---:|---:|---:|
| R1 | 2026-11-18 | 929.63 | %-7.04 | %-24.20 | 4 / 0 | %7.76 |
| R5 | 2026-11-18 | 894.43 | %-10.56 | %-24.49 | 16 / 0 | %11.71 |
| R6 | 2026-11-18 | 921.77 | %-7.82 | %-22.53 | 10 / 0 | %9.46 |
| R7 | 2026-11-18 | 916.09 | %-8.39 | %-27.65 | 15 / 0 | %9.88 |
| R8 | 2026-11-18 | 924.16 | %-7.58 | %-27.65 | 30 / 0 | %8.47 |

Başlangıç: 2026-10-27 UTC. İlk tam gün kapandıktan sonra sonuç oluşur.

Al-tut her izleğin kendi coinlerine eşit ağırlık verir; giriş/çıkış maliyeti her yönde %0,15 varsayılır. Günlük düşüş, net değerleme eğrisinden hesaplanır.

Freqtrade dönem sonunda açık işlemleri son mumun açılış fiyatında zorla kapatır. Bunlar gerçek çıkış sayılmaz; summary.json içinde “açık (değerleme)” olarak ayrılır. Son equity satırı motorun bu değerlemesiyle aynıdır; önceki satırlar gün kapanışı değerlemesidir. Bu sınır etkisi ve son gün yeni girişlerin motorca engellenmesi nedeniyle son gün kaydı bir sonraki çalışmada değişebilir.

**sanal işlem / tarihsel simülasyon, yatırım tavsiyesi değildir**
