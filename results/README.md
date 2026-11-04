# İleriye dönük sanal işlem kaydı

Son güncelleme (UTC): 2026-11-04T06:25:05.532924+00:00

| İzlek | Durum | Bakiye (USDT) | Getiri | Aynı coinleri al-tut | Kapalı / açık | En büyük düşüş |
|---|---|---:|---:|---:|---:|---:|
| R1 | 2026-11-03 | 971.72 | %-2.83 | %-4.80 | 2 / 0 | %3.58 |
| R5 | 2026-11-03 | 938.83 | %-6.12 | %-7.41 | 11 / 0 | %7.32 |
| R6 | 2026-11-03 | 947.51 | %-5.25 | %-4.31 | 7 / 0 | %6.93 |
| R7 | 2026-11-03 | 953.29 | %-4.67 | %-8.83 | 10 / 0 | %6.22 |
| R8 | 2026-11-03 | 958.14 | %-4.19 | %-8.83 | 20 / 0 | %5.10 |

Başlangıç: 2026-10-27 UTC. İlk tam gün kapandıktan sonra sonuç oluşur.

Al-tut her izleğin kendi coinlerine eşit ağırlık verir; giriş/çıkış maliyeti her yönde %0,15 varsayılır. Günlük düşüş, net değerleme eğrisinden hesaplanır.

Freqtrade dönem sonunda açık işlemleri son mumun açılış fiyatında zorla kapatır. Bunlar gerçek çıkış sayılmaz; summary.json içinde “açık (değerleme)” olarak ayrılır. Son equity satırı motorun bu değerlemesiyle aynıdır; önceki satırlar gün kapanışı değerlemesidir. Bu sınır etkisi ve son gün yeni girişlerin motorca engellenmesi nedeniyle son gün kaydı bir sonraki çalışmada değişebilir.

**sanal işlem / tarihsel simülasyon, yatırım tavsiyesi değildir**
