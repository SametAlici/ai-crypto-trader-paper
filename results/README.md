# İleriye dönük sanal işlem kaydı

Son güncelleme (UTC): 2026-11-01T06:07:36.807051+00:00

| İzlek | Durum | Bakiye (USDT) | Getiri | Aynı coinleri al-tut | Kapalı / açık | En büyük düşüş |
|---|---|---:|---:|---:|---:|---:|
| R1 | 2026-10-31 | 971.72 | %-2.83 | %-4.13 | 2 / 0 | %3.58 |
| R5 | 2026-10-31 | 959.59 | %-4.04 | %-5.30 | 6 / 0 | %6.02 |
| R6 | 2026-10-31 | 950.57 | %-4.94 | %-3.74 | 6 / 0 | %6.63 |
| R7 | 2026-10-31 | 971.58 | %-2.84 | %-6.26 | 5 / 0 | %5.19 |
| R8 | 2026-10-31 | 978.03 | %-2.20 | %-6.26 | 10 / 0 | %4.68 |

Başlangıç: 2026-10-27 UTC. İlk tam gün kapandıktan sonra sonuç oluşur.

Al-tut her izleğin kendi coinlerine eşit ağırlık verir; giriş/çıkış maliyeti her yönde %0,15 varsayılır. Günlük düşüş, net değerleme eğrisinden hesaplanır.

Freqtrade dönem sonunda açık işlemleri son mumun açılış fiyatında zorla kapatır. Bunlar gerçek çıkış sayılmaz; summary.json içinde “açık (değerleme)” olarak ayrılır. Son equity satırı motorun bu değerlemesiyle aynıdır; önceki satırlar gün kapanışı değerlemesidir. Bu sınır etkisi ve son gün yeni girişlerin motorca engellenmesi nedeniyle son gün kaydı bir sonraki çalışmada değişebilir.

**sanal işlem / tarihsel simülasyon, yatırım tavsiyesi değildir**
