# İstasyon sahipliği ve arayüzler (ICD)

## Kural
Bir modülün çıkış istasyonu o modüle aittir; sınırdaki istasyonun sahibi her zaman akış yukarısındaki modüldür. Sahip modül o istasyondaki Tt, Pt, W ve FAR değerlerini sağlamakla yükümlüdür. Akış aşağısındaki modül bu değerleri girdi olarak kullanır.

Sayılar bu belgede yazılmaz. Hepsi `icd.yaml` dosyasındadır. O dosya `engine/M0_engine/analysis/icd.py` tarafından aktif M0 revizyonundan (şu an rev005) üretilir, elle düzenlenmez. Etiketler [H], kaynak rev005.

## Modüller ve istasyonlar

| Modül | Giriş → çıkış | Kapsam |
|---|---|---|
| M1 Inlet & Fan | 2 → 13; 2 → 21 | Giriş (P2/P1), dış fan + OGV (by-pass tarafı), fan göbeği (iç fan, çekirdek tarafı) |
| M2 Booster | 21 → 25 | Booster kademeleri + geçiş kanalı (P25/P24) |
| M3 HP Compressor | 25 → 3 | HPC; ara kademe çekiş portu dahil (kaçak havası buradan ayrılır) |
| M4 Combustor | 31 → 4 | Yanma odası (verim, P4/P3, yakıt) |
| M5 HP Turbine | 4 → 44 | NGV, rotor ve soğutma havasının karışması (41, 43 iç istasyonlar) |
| M6 LP Turbine | 44 → 5 | Türbinler arası kanal (P45/P44) ve kaçak dönüşü dahil (45 iç istasyon) |
| M7 Nozzle | 5 → 8; 13 → 18 | Çekirdek lülesi (P6/P5); by-pass kanalı (P16/P13) + fan lülesi |
| M8 Shaft & Bearing | - | LP ve HP milleri: güçler, mekanik verim, devir referansları (Girão, Yılmaz) |
| M9 Secondary Air & Oil | 3 → 31 | İkincil hava bütçeleri: W25'in NGV 0.05, HPT rotor 0.06, ara kademe kaçağı 0.02 kadarı; çekiş ve dönüş istasyonları |

## Özel durumlar
- **İstasyon 31 (M9):** W31 = W3 − M9 çekişi. M3'ün çıkışı 3'tür; NGV ve rotor soğutma havasını ayıran M9 olduğu için 31'in sahibi M9'dur.
- **İkincil hava dönüşleri:** NGV havası 41'de (M5), rotor havası 44'te (M5), kaçak 45'te (M6) gaz yoluna karışır. Karışımı, dönüşün yapıldığı modül hesaplar. Debi bütçesi M9'dadır.
- **Mil güçleri (M8):** LPT gücü = (dış fan + iç fan + booster) / η_mek; HPT gücü = (HPC + güç çekişi) / η_mek.

## Bütçeler ve sapma
- `icd.yaml` → `modules.<Mx>.budget`: gerekli PR, izentropik verim (Δη dahil), giriş/çıkış koşulları, güç.
- İzin verilen sapma [T]: PR ±%1, verim ±0.005, debi ±%1, sıcaklık ±10 K. Güç ve alan gibi `info` kalemleri yalnızca raporlanır.
- Modül, ulaştığı değerleri `core.budgets.check_budget(modül, değerler)` ile kontrol eder.
- M0 entegrasyon kontrolü (`engine/M0_engine/analysis/integration.py`) çevrimi bu değerlerle yeniden çalıştırır. İki mod vardır [T]:
  - `thrust_held` (varsayılan, FADEC benzeri): itki 121.43 kN ve W2 sabit, T4 ve yakıt çözülür. ΔSFC ±%0.5 ve ΔEGT ±10 K kontrol edilir; ΔT41 raporlanır.
  - `operating_point`: W2, T4 ve Δη sabit; itki ±%0.5, SFC ±%0.5, EGT ±10 K kontrol edilir.
- Sınır aşılırsa modülden M0'a seçenekli bir CR taslağı açılır (`core/requests.py`): (a) M0 params değişikliği, yani ulaşılan değer kabul edilir ve verim Δη kaymasından çıkarılır; (b) modül yeniden tasarımı. Taslak otomatik uygulanmaz; seçimi kullanıcı yapar.
