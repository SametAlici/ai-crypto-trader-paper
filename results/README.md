# İleriye dönük sanal işlem kaydı

Son güncelleme (UTC): 2026-11-10T07:20:47.112206+00:00

| İzlek | Durum | Bakiye (USDT) | Getiri | Aynı coinleri al-tut | Kapalı / açık | En büyük düşüş |
|---|---|---:|---:|---:|---:|---:|
| R1 | 2026-11-09 | 929.63 | %-7.04 | %-9.66 | 4 / 0 | %7.76 |
| R5 | 2026-11-09 | 894.43 | %-10.56 | %-12.20 | 16 / 0 | %11.71 |
| R6 | 2026-11-09 | 921.77 | %-7.82 | %-9.36 | 10 / 0 | %9.46 |
| R7 | 2026-11-09 | 916.09 | %-8.39 | %-13.44 | 15 / 0 | %9.88 |
| R8 | 2026-11-09 | 924.16 | %-7.58 | %-13.44 | 30 / 0 | %8.47 |

Başlangıç: 2026-10-27 UTC. İlk tam gün kapandıktan sonra sonuç oluşur.

Al-tut her izleğin kendi coinlerine eşit ağırlık verir; giriş/çıkış maliyeti her yönde %0,15 varsayılır. Günlük düşüş, net değerleme eğrisinden hesaplanır.

Freqtrade dönem sonunda açık işlemleri son mumun açılış fiyatında zorla kapatır. Bunlar gerçek çıkış sayılmaz; summary.json içinde “açık (değerleme)” olarak ayrılır. Son equity satırı motorun bu değerlemesiyle aynıdır; önceki satırlar gün kapanışı değerlemesidir. Bu sınır etkisi ve son gün yeni girişlerin motorca engellenmesi nedeniyle son gün kaydı bir sonraki çalışmada değişebilir.

**sanal işlem / tarihsel simülasyon, yatırım tavsiyesi değildir**
