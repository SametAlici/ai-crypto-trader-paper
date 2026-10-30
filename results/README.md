# İleriye dönük sanal işlem kaydı

Son güncelleme (UTC): 2026-10-30T05:51:32.532822+00:00

| İzlek | Durum | Bakiye (USDT) | Getiri | Aynı coinleri al-tut | Kapalı / açık | En büyük düşüş |
|---|---|---:|---:|---:|---:|---:|
| R1 | 2026-10-29 | 1007.81 | %0.78 | %-3.96 | 0 / 2 | %0.00 |
| R5 | 2026-10-29 | 1012.96 | %1.30 | %-7.24 | 0 / 5 | %0.00 |
| R6 | 2026-10-29 | 1018.09 | %1.81 | %-3.72 | 0 / 5 | %0.00 |
| R7 | 2026-10-29 | 1016.51 | %1.65 | %-8.59 | 0 / 5 | %0.00 |
| R8 | 2026-10-29 | 1009.65 | %0.97 | %-8.59 | 0 / 10 | %0.00 |

Başlangıç: 2026-10-27 UTC. İlk tam gün kapandıktan sonra sonuç oluşur.

Al-tut her izleğin kendi coinlerine eşit ağırlık verir; giriş/çıkış maliyeti her yönde %0,15 varsayılır. Günlük düşüş, net değerleme eğrisinden hesaplanır.

Freqtrade dönem sonunda açık işlemleri son mumun açılış fiyatında zorla kapatır. Bunlar gerçek çıkış sayılmaz; summary.json içinde “açık (değerleme)” olarak ayrılır. Son equity satırı motorun bu değerlemesiyle aynıdır; önceki satırlar gün kapanışı değerlemesidir. Bu sınır etkisi ve son gün yeni girişlerin motorca engellenmesi nedeniyle son gün kaydı bir sonraki çalışmada değişebilir.

**sanal işlem / tarihsel simülasyon, yatırım tavsiyesi değildir**
