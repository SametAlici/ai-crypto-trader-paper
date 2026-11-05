# İleriye dönük sanal işlem kaydı

Son güncelleme (UTC): 2026-11-05T06:49:11.496454+00:00

| İzlek | Durum | Bakiye (USDT) | Getiri | Aynı coinleri al-tut | Kapalı / açık | En büyük düşüş |
|---|---|---:|---:|---:|---:|---:|
| R1 | 2026-11-04 | 971.72 | %-2.83 | %-0.48 | 2 / 0 | %3.58 |
| R5 | 2026-11-04 | 938.83 | %-6.12 | %-4.45 | 11 / 0 | %7.32 |
| R6 | 2026-11-04 | 947.51 | %-5.25 | %-0.97 | 7 / 0 | %6.93 |
| R7 | 2026-11-04 | 953.29 | %-4.67 | %-6.11 | 10 / 0 | %6.22 |
| R8 | 2026-11-04 | 958.14 | %-4.19 | %-6.11 | 20 / 0 | %5.10 |

Başlangıç: 2026-10-27 UTC. İlk tam gün kapandıktan sonra sonuç oluşur.

Al-tut her izleğin kendi coinlerine eşit ağırlık verir; giriş/çıkış maliyeti her yönde %0,15 varsayılır. Günlük düşüş, net değerleme eğrisinden hesaplanır.

Freqtrade dönem sonunda açık işlemleri son mumun açılış fiyatında zorla kapatır. Bunlar gerçek çıkış sayılmaz; summary.json içinde “açık (değerleme)” olarak ayrılır. Son equity satırı motorun bu değerlemesiyle aynıdır; önceki satırlar gün kapanışı değerlemesidir. Bu sınır etkisi ve son gün yeni girişlerin motorca engellenmesi nedeniyle son gün kaydı bir sonraki çalışmada değişebilir.

**sanal işlem / tarihsel simülasyon, yatırım tavsiyesi değildir**
