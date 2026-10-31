# İleriye dönük sanal işlem kaydı

Son güncelleme (UTC): 2026-10-31T05:44:16.058313+00:00

| İzlek | Durum | Bakiye (USDT) | Getiri | Aynı coinleri al-tut | Kapalı / açık | En büyük düşüş |
|---|---|---:|---:|---:|---:|---:|
| R1 | 2026-10-30 | 971.90 | %-2.81 | %-4.08 | 0 / 2 | %3.57 |
| R5 | 2026-10-30 | 952.00 | %-4.80 | %-4.55 | 1 / 4 | %6.02 |
| R6 | 2026-10-30 | 960.47 | %-3.95 | %-2.85 | 1 / 4 | %5.66 |
| R7 | 2026-10-30 | 963.78 | %-3.62 | %-5.44 | 0 / 5 | %5.19 |
| R8 | 2026-10-30 | 962.37 | %-3.76 | %-5.44 | 0 / 10 | %4.68 |

Başlangıç: 2026-10-27 UTC. İlk tam gün kapandıktan sonra sonuç oluşur.

Al-tut her izleğin kendi coinlerine eşit ağırlık verir; giriş/çıkış maliyeti her yönde %0,15 varsayılır. Günlük düşüş, net değerleme eğrisinden hesaplanır.

Freqtrade dönem sonunda açık işlemleri son mumun açılış fiyatında zorla kapatır. Bunlar gerçek çıkış sayılmaz; summary.json içinde “açık (değerleme)” olarak ayrılır. Son equity satırı motorun bu değerlemesiyle aynıdır; önceki satırlar gün kapanışı değerlemesidir. Bu sınır etkisi ve son gün yeni girişlerin motorca engellenmesi nedeniyle son gün kaydı bir sonraki çalışmada değişebilir.

**sanal işlem / tarihsel simülasyon, yatırım tavsiyesi değildir**
