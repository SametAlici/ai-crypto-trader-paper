# İleriye dönük sanal işlem kaydı

Son güncelleme (UTC): 2026-10-29T05:51:00.411461+00:00

| İzlek | Durum | Bakiye (USDT) | Getiri | Aynı coinleri al-tut | Kapalı / açık | En büyük düşüş |
|---|---|---:|---:|---:|---:|---:|
| R1 | 2026-10-28 | 1000.00 | %0.00 | %1.19 | 0 / 0 | %0.00 |
| R5 | 2026-10-28 | 1000.00 | %0.00 | %0.36 | 0 / 0 | %0.00 |
| R6 | 2026-10-28 | 1000.00 | %0.00 | %1.73 | 0 / 0 | %0.00 |
| R7 | 2026-10-28 | 1000.00 | %0.00 | %0.57 | 0 / 0 | %0.00 |
| R8 | 2026-10-28 | 1000.00 | %0.00 | %0.57 | 0 / 0 | %0.00 |

Başlangıç: 2026-10-27 UTC. İlk tam gün kapandıktan sonra sonuç oluşur.

Al-tut her izleğin kendi coinlerine eşit ağırlık verir; giriş/çıkış maliyeti her yönde %0,15 varsayılır. Günlük düşüş, net değerleme eğrisinden hesaplanır.

Freqtrade dönem sonunda açık işlemleri son mumun açılış fiyatında zorla kapatır. Bunlar gerçek çıkış sayılmaz; summary.json içinde “açık (değerleme)” olarak ayrılır. Son equity satırı motorun bu değerlemesiyle aynıdır; önceki satırlar gün kapanışı değerlemesidir. Bu sınır etkisi ve son gün yeni girişlerin motorca engellenmesi nedeniyle son gün kaydı bir sonraki çalışmada değişebilir.

**sanal işlem / tarihsel simülasyon, yatırım tavsiyesi değildir**
