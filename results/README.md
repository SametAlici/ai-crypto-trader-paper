# İleriye dönük sanal işlem kaydı

Son güncelleme (UTC): 2026-11-06T06:49:37.949246+00:00

| İzlek | Durum | Bakiye (USDT) | Getiri | Aynı coinleri al-tut | Kapalı / açık | En büyük düşüş |
|---|---|---:|---:|---:|---:|---:|
| R1 | 2026-11-05 | 971.72 | %-2.83 | %-7.04 | 2 / 0 | %3.58 |
| R5 | 2026-11-05 | 938.83 | %-6.12 | %-10.91 | 11 / 0 | %7.32 |
| R6 | 2026-11-05 | 947.51 | %-5.25 | %-6.49 | 7 / 0 | %6.93 |
| R7 | 2026-11-05 | 953.29 | %-4.67 | %-12.56 | 10 / 0 | %6.22 |
| R8 | 2026-11-05 | 958.14 | %-4.19 | %-12.56 | 20 / 0 | %5.10 |

Başlangıç: 2026-10-27 UTC. İlk tam gün kapandıktan sonra sonuç oluşur.

Al-tut her izleğin kendi coinlerine eşit ağırlık verir; giriş/çıkış maliyeti her yönde %0,15 varsayılır. Günlük düşüş, net değerleme eğrisinden hesaplanır.

Freqtrade dönem sonunda açık işlemleri son mumun açılış fiyatında zorla kapatır. Bunlar gerçek çıkış sayılmaz; summary.json içinde “açık (değerleme)” olarak ayrılır. Son equity satırı motorun bu değerlemesiyle aynıdır; önceki satırlar gün kapanışı değerlemesidir. Bu sınır etkisi ve son gün yeni girişlerin motorca engellenmesi nedeniyle son gün kaydı bir sonraki çalışmada değişebilir.

**sanal işlem / tarihsel simülasyon, yatırım tavsiyesi değildir**
