# Geometri adım 2 çelişkileri: #75, #76, #77 (yalnız analiz)

Kapsam: M2 rev001 (aktif kayıt), geometri adım 2 kuralları R-G2.9-17, M1 rev014 (salt okunur). Bu notta geometri kodu,
`geometry_params.yaml`, BOM, kayıt veya CR değişmedi. Sayıların hepsi
`engine/M2_booster/analysis/conflicts_75_77.py` betiğinden gelir (fonksiyon adı her satırda); betik M1 geometri kodunu
yalnız içe aktarır, dosya yazmaz. Geçici katılar (sıra bantları, #76 ön konisi) yalnız betiğin içinde vardır.
Etiketler: [H] koddan hesap ([T] kural oranlarından), [T] tahmin/öneri, [G] genel mühendislik bilgisi, [KS] ikincil kaynak.

## 1. #77 M1 parçaları ile çakışmalar

Ölçüm (`overlap_table`): eksenel simetrik M2 parçaları (tambur, kasa, iç örtüler) için ortak hacim tamdır ve M1 adedi
(dikme 12) ile çarpılarak takım hacmi verilir [H]. Kanatlı M2 parçaları için iki ölçü: 0 numaralı örnek (hardware.m1_overlap
ile aynı) ve saatlemeden bağımsız "sıra bandı" (göbek çizgisi ile kasa arasında sıranın x aralığı; dönen sıra bu bandın
tamamını süpürür, 31-49 kanatlı bir stator sırası halkayı kesen bir dikmeden saatlenerek kaçamaz) [T].
Yarıçap aralığı ortak katının köşe ve kenar örneklerinden alınır [H].

### (a) M1.4.3 splitter halkası - M2 kanatları ve kasası

- Splitter halkası x 0.235369-0.634908 m, dış yüz r_split 0.433488 m, iç yüz 0.424818 m (kalınlık 0.008670 m,
  0.02 x r_split [T] M1 kuralı), ön dudak 0.034679 m boyunca incelir [H] (`frame_numbers`).
- M2 kasası x 0.235369-0.641557 m, iç yüz 0.433488 m (= ist. 21 uç yarıçapı), dış yüz 0.442158 m (kalınlık 0.008670 m,
  0.02 x r [T]) [H].
- Splitter ile kasa arasında ortak hacim yok, mesafe 0 [H] (`splitter_casing`): splitter dış yüzü = kasa iç yüzü,
  x 0.270048-0.634908 m boyunca ortak yüzey [H].
- Aynı fiziksel duvar mı: evet, ikisi de çekirdek ile baypas arasındaki ayırıcı duvarı aynı eksenel bölgede modelliyor.
  M1 kalınlığı çekirdek tarafına (içe) almış, M2 baypas tarafına (dışa). Kök neden: M1 akış yolunda baypas iç duvar
  yarıçapı r_split2 = ist. 21 uç yarıçapı 0.433488 m (sıfır kalınlıklı ayırıcı varsayımı) [H]; iki duvar için radyal yer
  sıfır.
- Çakışmalar (bant, takım hacmi; r aralığı hep 0.424818-0.433488 m) [H]: R1 1.012e-3 m3 (x 0.24794-0.29824),
  S1 1.978e-3 (x 0.31082-0.39541), R2 8.969e-4 (x 0.41656-0.45493), S2 1.515e-3 (x 0.46452-0.53218), R3 4.227e-4
  (x 0.54910-0.57948), S3 1.111e-3 (x 0.58708-0.63491). 0 numaralı örnek oranları: kanat uçları 0.041/0.059/0.075,
  stator kanatları 0.081/0.101/0.119 [H].
- Kütle: M1.4.3 23.3591 kg [H] (BOM değeri ve `fan_frame.masses` rev014 ile aynı; alüminyum 2800 kg/m3, hacim
  0.0083425 m3). M2 kasası 31.8164 kg [H] (`hardware.masses`; ti6al4v 4430 kg/m3 yer tutucu, #71; hacim 0.0071820 m3;
  alüminyum yoğunluğuyla 20.1097 kg) [H]. M2 BOM'u bugün boş olduğu için toplamda henüz çift sayım yok; M2.0.2 BOM'a
  girdiği anda x 0.270-0.635 m boyunca aynı duvar iki kez sayılır [T].
- M2 tarafında kaldırılabilir mi: hayır. Splitter iç yüzü M2 uç akış yolunun 8.67 mm içinde; bunu ancak uç yarıçapının
  düşmesi (rev001 meanline değişikliği, bu analizin dışında) veya M1'in kalınlığı dışa alması (CR) kaldırır. Kasanın
  kalınlığı, yönü, uzunluğu bu çakışmayı etkilemez (çakışan M1 parçası kanatlarla).
- CR taslağı yönü (M0 için, açılmadı): ya (i) M1 splitter halkası dudaktan sonra iç yüzü r = 0.433488 m'de olacak
  şekilde dışa kalınlaşır ve M2 kasası bu bölgede ayrı duvar olmaz (sahiplik kararı: kasa M1'de mi M2'de mi), ya da
  (ii) M1 baypas iç duvarını en az bir duvar kalınlığı kadar (bugünkü kurallarla 0.008670 m [H]) dışa alır ve iki ayrı
  duvar (splitter + booster kasası) arasında boşluk kalır. İkisi de M1 ist. 13 baypas alanını değiştirir (M1 kabul
  edilmiş, yeniden analiz gerekir) [T].

### (b) M1 baypas dikmeleri (M1.4.4) ve OGV (M1.3.1) - M2 kasası ve ayakları

- Kasa x OGV: tam 8.508e-6 m3 tek kanat, takım (51 kanat) 4.339e-4 m3, x 0.32121-0.47806, r 0.43349-0.44216 [H].
- Kasa x baypas dikmesi: 1.232e-5 m3, takım (12) 1.478e-4 m3, x 0.49374-0.61922, r 0.43349-0.44216 [H].
- Ayaklar: S1 ayağı x OGV 3.463e-6 (örnek 0, oran 0.093; halka 1.979e-4 takım), S2 ayağı x baypas dikmesi 2.379e-6
  (0.126), S3 ayağı x baypas dikmesi 1.595e-6 (0.178); S2 ayak halkası OGV firar bölgesine de değiyor (x 0.45782-0.47806,
  takım 9.307e-6) [H]. Oluk derinliği 4.464/3.573/2.880 mm [H].
- M2 [T] seçenekleri:
  - Kasa kalınlığını içe almak: olmaz, iç yüz akış yolu (R-G2.5/R-G2.12, rev001 yarıçapı).
  - Kalınlık 0: çakışma kalkar ama duvar kalmaz (fiziksel değil).
  - Kasa boyu: OGV hücum kenarı x 0.32121 m'de bitirmek S1 oluğunu (x 0.30236-0.40387) keser, R2-S3 kasasız kalır; olmaz.
  - Eksenel boşluk: OGV x 0.32121-0.47806 aralığı booster'ın ortasında; boşluk oranı ne olursa olsun S1-S2 OGV altında
    kalır (bkz. c).
  - Ayak derinliği: oluk/ayak derinliği 0 yalnız ayak çakışmasını kaldırır, kasa çakışması kalır.
  Sonuç: M2 tarafında kaldırılamaz; (a) ile aynı radyal yer sorunu, aynı CR yönü (baypas iç duvarı dışa veya ortak duvar).
  Gerçek motorda OGV'nin booster'ın radyal dışında durması olağandır [G]; çakışma eksenel değil radyal yer eksikliğidir.

### (c) M1 fan çerçevesi çekirdek dikmeleri (M1.4.5), göbek halkası (M1.4.1) ve yatak flanşı

- Çerçeve x 0.478059-0.634908 m, çekirdek dikmesi x 0.493744-0.619223 m, kalınlık 0.015058 m, r 0.30213-0.424818 m [H].
- Çakışmalar [H]: tambur 2.144e-5 m3 (takım 2.573e-4; x 0.49374-0.61922, r 0.32531-0.36251); S2 iç örtüsü takım
  1.010e-4 (r 0.33546-0.35005); S3 iç örtüsü takım 5.228e-5 (r 0.35444-0.36471); S2 kanat bandı takım 5.284e-4;
  R3 rotor bandı takım 3.763e-4; S3 kanat bandı takım 3.556e-4; R3 kök halkası takım 1.111e-4. Örnek 0 oranları: R3 kanadı
  0.653, S3 kanadı 0.550, R3 kök bloğu 0.468, S2 kanadı 0.137, tambur 0.092 (open_items ile aynı) [H].
- Göbek halkası (r 0.293460-0.30213, x 0.478-0.635) ve yatak flanşı (iç yarıçap 0.151065, x 0.621904-0.634908) dönen
  tamburun içinde, ortak hacim yok [H]; fakat bunları splitter'a bağlayan çekirdek dikmeleri dönen tamburdan geçmek
  zorunda: topolojik olarak kurulamaz [G].
- M2 tarafında eksenel kaydırma: sıra genişlikleri toplamı 0.325786 m (rev001 kirişleri ve R-G2.3 kademelenmesi),
  ist. 21'den dikme hücum kenarına yer 0.258375 m, eksik 0.067411 m [H]. Dikme önünde bitmek için gereken boşluk oranı
  -0.2096, çerçeve başına -0.2584 (negatif, imkânsız) [H] (`frame_numbers`). Boşluk, kasa boyu, kasa kalınlığı, ayak
  derinliği bu grubu kaldıramaz; yalnız meanline değişikliği (kiriş/kademe sayısı, yeni revizyon) veya M1 CR'ı.
- CR yönü (M1): çekirdek dikmeleri en az x24 - dikme hücum kenarı = 0.147812 m, çerçeve başlangıcı 0.163497 m aft'a
  [H] (geçiş kanalı 24 -> 25 modellenmedi, ek uzunluk ister) ve çerçeve içinden geçen çekirdek kanalı yarıçapları
  (bugün yer tutucu 0.30213-0.424818) M2 ist. 24/25 anülüsüne (0.36624-0.433488) uydurulur [T]. M1 #49 tetikleyicisi
  gerçekleşti. CFM56 yerleşiminde booster fan çerçevesi dikmelerinin önünde durur ve çekirdek akışı geçiş kanalında
  çerçeveden geçer [G].

## 2. #76 Tambur - fan diski arayüzü, ön koni

- M1 diski (rev014, `forward_space`) [H]: ön yüz x -0.124098, arka yüz x 0.140291, jant 0.226773, yuva tabanı 0.200138,
  canlı jant iç yarıçapı 0.172952, göbek (bore) 0.068032-0.147349 (genişlik 0.158634, gövde 0.066097). Fan kanadı göbek
  firar kenarı (0.109785, 0.30213). Komşular arka yüze mesafe: aralayıcı 6.35 mm, şim 11.79 mm, kanat 12.29 mm,
  platform 26.83 mm (geçici koniye göre, `cone_check`) [H]. Spinner diskin önünde (koniye 0.2646 m) [H].
- M8 sınırı r 0.151065 m: kaynağı M1 `fan_frame_params.yaml` `bearing_flange_inner_over_hub_radius` 0.5 [T] x ist. 21
  göbek yarıçapı 0.30213; M1 `fan_frame.interfaces` "M8_bearing_support", x 0.621904-0.634908 (çerçeve arkası) [H]. M8
  dosyalarında bu değer yok; LP mili ve yataklar tasarlanmadı.
- Boş yer: x 0.140291-0.235369 (0.095078 m) ve r 0-0.30213 bölgesi hiçbir M1 parçasıyla kesişmiyor [H]. Aynı aralıkta
  iç akış yolu duvarı da yok: M1 platformu x 0.140291'de, M2 rim 1 ist. 21'de başlıyor; 95 mm'lik göbek duvarı boşluğu
  [H]. Ön koni bu boşluğa bir göbek kabuğu ile birlikte konursa iki açığı birden kapatır [T].
- Geçici koni (yalnız betikte): disk arka yüzünde flanş halkası (r 0.172952-0.200138, kalınlık 0.009704 = R-G2.13 flanş)
  ve cıvata dairesi 0.186545'ten ist. 21'deki tambur flanşına (iç yarıçap 0.172952) inen 4.852 mm (kademe 1 duvarı)
  konik kabuk [T]. Sonuç [H]: hiçbir M1 parçasıyla ortak hacim yok, diske mesafe 0 (cıvatalı temas, istenen), M8
  sınırına radyal pay 0.021887 m; hacim 7.802e-4 m3, kütle 3.456 kg (ti6al4v). Kütle bir kez, M2.0.1 tamburunda sayılır;
  M1 BOM'unda arka kol yok, çift sayım olmaz [T].
- Değişmesi gereken kurallar: R-G2.9 ("ist. 21 önü M1'dir", rim 1 ist. 21'de başlar), R-G2.13 (flanş ist. 21
  düzleminde, "hiçbir M2 parçası ist. 21'i geçmez"), R-G2.17 ("x < ist. 21 parça yok" kontrolü). Donanım sınırı aero
  istasyonu yerine M1 disk arka yüzü (m1_disk_aft_face_x_m) olur [T]. J2-1 ("tambur fan diskinin arka yüzüne
  cıvatalı" [KS]) bu seçenekle uyumlu.
- Kalan M1 yükü: cıvata delikleri M1 diskinin canlı jantında; delik/özellik eklemek M1 parçasının değişmesi demek, en az
  bir arayüz CR'ı gerekir (konide ortak hacim olmaması bunu ortadan kaldırmaz) [T].
- Hüküm: koni geometrik olarak sığar ve M1 hacimleriyle çakışmaz [H]; uygulanmadı. Karar M0/kullanıcıda: M2 kural
  değişikliği (R-G2.9/13/17) + M1 disk delik arayüzü (CR) ya da M1 arka kol (CR).

## 3. #75 Rotor yuvaları arka yüzde neden kapanıyor

`slot_closure` [H]. Tanımlar: yuva tabanı r_sb = göbek_min(rotor) - 0.25 x rotor kirişi (`hw_slot_depth_over_rotor_chord`);
sızdırmazlık dişi tabanı (tambur duvarı dış yarıçapı) r_wall_out = göbek_min(stator) - (0.08 + 0.06 + 0.06 x 1.0) x stator
kirişi - conta açıklığı (`hw_shroud_thickness`, `hw_land_thickness`, `hw_tooth_height_over_land_thickness`,
`hw_seal_clearance_over_tip_clearance` 1.0 x uç açıklığı). Göbek_min(rotor) rotor hücum kenarındaki göbek, göbek_min(stator)
= rotor firar kenarı göbeği.

Kapanma yüksekliği = göbek yükselişi (rotor boyunca) + 0.25 c_R - 0.20 c_S - conta açıklığı:

| Kademe | göbek yükselişi mm | yuva derinliği 0.25 c_R mm | conta yığını 0.20 c_S mm | conta açıklığı mm | kapanma mm |
|---|---|---|---|---|---|
| 1 | 21.324 | 15.088 | 17.854 | 0.855 | 17.702 |
| 2 | 16.173 | 12.015 | 14.290 | 0.681 | 13.217 |
| 3 | 12.461 | 9.653 | 11.520 | 0.547 | 10.046 |

Değerler [H]. Belirleyici terim rotor boyunca göbek yükselişidir: diş tabanı rotor firar göbeğine, yuva tabanı rotor hücum
göbeğine bağlı. Yuva derinliği sıfır olsa bile diş tabanı rotor hücum göbeğinin 2.615/1.202/0.394 mm üstünde kalır [H];
yani "yuvayı sığlaştır" seçeneği imkânsız. Aft yüzün açılması için conta yığınının stator kirişine oranı 0.398/0.385/0.374
olmalıydı (bugün 0.20) [H]. Ön yüz açık, çünkü önceki statorun duvarı yuva tabanının 12.53/9.91 mm altında [H].

Kural seçenekleri (hiçbiri rev001 meanline'ına dokunmaz: yarıçap, kiriş, sayı, düzlem aynı) [T]:

1. Eğik tabanlı eksenel yuva: taban yerel göbek çizgisine paralel, aynı derinlik. Arka yüz taban 0.308367/0.333444/0.352855,
   duvar dışının 3.622/2.956/2.415 mm üstünde; ön yüz pay 12.53/9.91 mm aynı [H]. [G] gerekçe: konik jantta eksenel
   kırlangıç kuyruğu jant konisini izler, kök boyun/lob kesiti boyunca sabit kalır ve kök bloğu yük taşıma yüzeyi her
   yerde aynı derinliktedir.
2. Çevresel (teğet girişli) kırlangıç oluğu: jant başına tek 360° oluk, yüzler kapalı; kanatlar yükleme penceresinden
   takılır, kilit parçalarıyla sabitlenir. [G] gerekçe: tambur tipi rotorlarda yaygındır, oluk tornada açılır, jant
   çevresel olarak sürekli kalır (çember gerilmesi taşıyan halka kesilmez), komşu duvar/conta kolu jantla her yarıçapta
   birleşebilir. J2-2 CFM56-7B için doğrulanamadı.
3. Duvar bağlantısını yuva tabanının altına indirmek (rim arka yüzünde basamak veya konik ara kol; dişler duvar yerine
   kol üstünde): gereken iniş 17.70/13.22/10.05 mm; duvar yuva tabanında kalırsa diş yüksekliği 23.06/17.50/13.50 mm olurdu
   (bugün 5.36/4.29/3.46 mm) [H]. [G] gerekçe: gerçek tamburlarda kademeler arası conta kolu jantlara yuva tabanının
   altından bağlanır; uzun ince dişler esnek ve titreşime açık olduğundan iniş kol/örtü tarafında yapılır.
4. Yalnız önden açık kör yuva + ön tutucu (kilit plakası/yarık halka): [G] gerekçe karşıtı: eksenel yuvalar broşla açılır,
   kör yuva broşlanamaz; kompresör rotor kanadındaki gaz kuvveti öne doğrudur, ana yükü ön tutucu taşır, kapalı arka uç
   yalnız ters yükte çalışır. Bugünkü geometrinin karşılığıdır, ama üretim gerekçesi zayıf.
5. Yuvayı sığlaştırmak (taban = diş tabanı): imkânsız, derinlik negatif (-2.615/-1.202/-0.394 mm) [H].
6. Kanatlı tümleşik halka/disk (yuvasız): [G] gerekçe: modern kompresörlerde kullanılır, kök ve yuva kütlesi kalkar;
   onarım ve FOD (FM2-1) açısından dezavantajlı. Sayılar değişmez.

Öneri (karar M0/kullanıcıda): 1 veya 2; ikisi de yapısal aşamada (A-4) kök/jant boyutlandırmasıyla birlikte seçilmeli,
"R-G2.10 geçsin" gerekçesiyle değil.

## 4. Adım 3a uygulaması (#75 seçenek 1, #76 ön koni)

Kurallar: R-G2.9/13/17 değişti (donanım sınırı M1 disk arka yüzü, ist. 21 yalnız akış düzlemi), yeni R-G2.18 (ön koni)
ve R-G2.19 (eğik yuva tabanı). M1 disk değerleri artık `hardware.m1_interface` ile M1 kodundan okunuyor; yazılmış kopya
yok. Sonuçlar `hardware.slot_checks` ve `hardware.cone_checks` çıktısıdır [H]: arka yüz payı 3.622/2.956/2.415 mm
(bölüm 3'teki tahminle aynı), koni 3.456 kg, M8 sınırına 0.021887 m, M1 rotor parçalarıyla ortak hacim 0. Kök blokları
eğik tabanla hafifledi (4.081/2.632/1.771 kg), tambur 63.106 kg (koni dahil). Paylar küçük; yapısal aşamada (A-4) kök
ve jant boyutlandırmasıyla birlikte yeniden bakılacak. Kasa (M2.0.2) ve #77 CR-002/CR-003 kararını bekliyor.
