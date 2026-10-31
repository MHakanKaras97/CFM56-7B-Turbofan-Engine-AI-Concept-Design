# Turbofan motor nasıl çalışır?

Turbofan, büyük bir fanı küçük bir gaz türbini (çekirdek) ile döndüren jet motorudur. Bugünkü yolcu uçaklarının
neredeyse tamamı turbofan kullanır, çünkü yüksek hızda verimli ve görece sessizdir.

## Dört adımda çalışma prensibi (Brayton çevrimi)
1. **Emme:** Fan havayı içeri çeker.
2. **Sıkıştırma:** Kompresörler havanın basıncını onlarca kat artırır.
3. **Yanma:** Sıkışmış havaya yakıt püskürtülür ve yakılır; gazın sıcaklığı çok yükselir.
4. **Genişleme:** Sıcak gaz türbinleri döndürür, sonra lüleden hızla çıkar.

Türbinler, kompresörleri ve fanı döndürecek gücü üretir. Geriye kalan enerji itkiye dönüşür.

## Baypas: turbofanın sırrı
- Fanın ittiği havanın büyük kısmı çekirdeğe girmez, motorun etrafından (**baypas**) dolaşır.
- Baypas havasının çekirdek havasına oranına **baypas oranı** denir. CFM56-7B'de bu oran yaklaşık 5'tir.
- Çok miktarda havayı biraz hızlandırmak, az miktarda havayı çok hızlandırmaktan daha verimlidir.
  Bu yüzden itkinin büyük kısmı fandan gelir ve yakıt tüketimi düşer.

## İki mil (two-spool) yapısı
- **Alçak basınç (LP) mili:** fan + booster, alçak basınç türbini tarafından döndürülür. Yavaş döner.
- **Yüksek basınç (HP) mili:** yüksek basınç kompresörü, yüksek basınç türbini tarafından döndürülür. Hızlı döner.
- İki mil iç içedir ve birbirinden bağımsız hızlarda döner. Böylece her bileşen kendi en verimli hızında çalışır.

## CFM56-7B hakkında
- CFM International (GE ve Safran ortaklığı) tarafından üretilir; Boeing 737 Next Generation ailesinin tek motorudur.
- Mimari: 1 kademe fan, 3 kademe booster, 9 kademe yüksek basınç kompresörü, tek halkalı yanma odası,
  1 kademe yüksek basınç türbini, 4 kademe alçak basınç türbini.
- Dünyanın en çok üretilen yolcu uçağı motor ailelerinden biridir.

## Bu projedeki modüller
| Modül | Bölüm | Kısa görevi |
|---|---|---|
| M1 | Giriş ve fan | Havayı alır, baypas itkisinin çoğunu üretir |
| M2 | Booster | Çekirdek havasını ilk kez sıkıştırır |
| M3 | Yüksek basınç kompresörü | Basıncı en çok artıran bölüm |
| M4 | Yanma odası | Yakıtı yakar, gazı ısıtır |
| M5 | Yüksek basınç türbini | HP kompresörünü döndürür |
| M6 | Alçak basınç türbini | Fan ve booster'ı döndürür |
| M7 | Lüleler | Gazı hızlandırıp itki üretir |
| M8 | Miller ve yataklar | Dönen parçaları taşır, gücü aktarır |
| M9 | İkincil hava, yağ, dişli kutusu | Soğutma, yağlama ve aksesuar tahriki |

## İstasyon numaraları
Mühendisler gaz yolundaki noktaları numaralarla anar (SAE AS755): **2** fan yüzü, **13** fan çıkışı (baypas),
**25** HP kompresör girişi, **3** HP kompresör çıkışı, **4** türbin girişi (en sıcak nokta), **45** LP türbin girişi,
**5** LP türbin çıkışı, **8** çekirdek lülesi çıkışı, **18** fan lülesi çıkışı.

## Hatırlanacak üç sayı türü
- **Basınç oranı:** havanın kaç kat sıkıştırıldığı. Yüksek olması verimi artırır.
- **Türbin giriş sıcaklığı:** motorun en sıcak noktası. Yükseldikçe güç artar, ama malzeme ve soğutma zorlaşır.
- **Özgül yakıt tüketimi (SFC):** birim itki için yakılan yakıt. Ne kadar düşükse o kadar iyi.
