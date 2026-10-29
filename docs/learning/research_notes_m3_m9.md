> Secondary summary, not a primary source. Every line [KS weak]. Only LLP lives verified against the Owner's Guide table (ISSUE58) may enter rule books.

"İkincil özet, birincil kaynak değil. Her satır \[KS zayıf]. Yalnızca Owner’s Guide tablosuyla doğrulanan LLP ömürleri kural kitabına girer. Kalanlar kaynak bulunana kadar girdi değildir."



M3 — HP kompresör (High-Pressure Compressor)
M3.1. Çok kademeli referans kompresör
Doğrulanabilen bilgiler
CFM56-7B ailesinin temel motor mimarisi şu şekildedir:

* Fan: 1 kademe
* LPC/booster: 3 kademe
* HPC: 9 kademe
* HPT: 1 kademe
* LPT: 4 kademe
Bu kademe sayıları EASA'nın motor tipi veri sayfasında ve Aircraft Commerce'un CFM56-7B rehberinde belirtilmektedir. Studylib

Dolayısıyla M3 için dokuz kademeli eksenel HP kompresör temel alınabilir.
E3 CR-168211 ne kadar uygun?
NASA'nın E3 programı, gelecekteki ticari uçak motorları için yakıt verimliliğini artırmayı hedefleyen bir araştırma programıdır. CR-168211 raporu, entegre çekirdek ve düşük basınçlı mil sisteminin tasarımını ve test sonuçlarını içerir. NASA Technical Reports Server

Bu nedenle E3 raporu aşağıdaki alanlarda yararlıdır:

* Kompresör ve türbin performans eğrileri.
* Çekirdek motorun termodinamik davranışı.
* Kompresör verimi ile çalışma koşulları arasındaki ilişki.
* Referans motor modelinin hesaplamalarla doğrulanması.
Ancak E3 kompresörünü CFM56-7B27 kompresörü olarak kullanamayız. E3, ayrı bir araştırma motorudur. Geometrisi, kademe yükleri ve performans haritaları ancak uygunluk analizi yapıldıktan sonra referans olarak kullanılabilir.
NASA TP-1523 ne için kullanılmalı?
NASA TP-1523, göbek/uç yarıçapı oranı 0,8 olan 14 ses altı kompresör orta kademesini inceler. Çalışmada kademe verimi, kanat açıklık oranı, difüzyon faktörü ve kanat katılığı gibi parametreler değerlendirilir. NASA Technical Reports Server

Bu kaynak için önerdiğim kullanım:

* Uygun: M3 orta kademelerinin genel aerodinamik davranışını modellemek.
* Koşullu: Kademe yük katsayısı ve verim için başlangıç aralıkları oluşturmak.
* Uygun değil: CFM56-7B27'nin belirli bir kademesinin gerçek ölçülerini bu rapordan doğrudan çıkarmak.
Senin önceki notundaki değerlendirme bu açıdan mantıklı: TP-1523, booster yerine M3'ün orta kademeleri için daha uygun bir genel referans olabilir. Fakat gerçek uygunluk, M2'de belirlenen giriş koşulları ve kademe boyutlarıyla karşılaştırılmalı.
M3.2. Dokuz kademenin kanat sayıları, IGV ve değişken statörler
Parametre	Mevcut bulgu	Durum
HPC kademe sayısı	9	Doğrulandı
Giriş kılavuz kanatları (IGV)	HPC girişinde bulunur	Ayrıntılı geometri doğrulanmadı
Değişken statörler (VSV)	Eğitim dokümanlarında 1., 2. ve 3. kademe VSV'leri gösteriliyor	Kademe konfigürasyonu aile düzeyinde destekleniyor
Her kademedeki rotor kanat sayısı	Doğrudan doğrulanmış tablo bulunamadı	Açık
Her kademedeki statör kanat sayısı	Doğrudan doğrulanmış tablo bulunamadı	Açık
VSV açı çizelgesi	Doğrudan doğrulanmış sayısal çizelge bulunamadı	Açık



CFM56-7B eğitim dokümanlarında IGV ile birinci, ikinci ve üçüncü kademe değişken statörleri tanımlanır. Bununla birlikte bunların yalnızca isimlerini veya şematik gösterimlerini görmek, her kademe için kanat sayısını ve çalışma açısını doğrulamak için yeterli değildir. FlipHTML5

Mühendislik kararı: Kanat sayıları bulunana kadar bunları CFM56-7B27'ye özgü sabitler olarak tanımlamayalım. Geçici değerler gerekirse ayrı bir estimated\_geometry katmanında tutulmalı ve kaynaklı verilerle karıştırılmamalı.
M3.3. HPC giriş/çıkış yarıçapları ve son kademe kanat yüksekliği
Bu araştırmada aşağıdaki ölçüleri doğrudan CFM56-7B27'ye atfedebileceğimiz güvenilir, açık bir boyut tablosu doğrulayamadım:

* HPC giriş hub yarıçapı.
* HPC giriş tip yarıçapı.
* HPC çıkış hub ve tip yarıçapları.
* Son kademe kanat yüksekliği.
* Kademe bazında eksenel uzunluklar.
* Kademe bazında rotor ve statör kordları.
Bu verileri genel motor boyutlarından türetmek doğru olmaz. Örneğin motorun toplam uzunluğu, HPC'nin iç uzunluğunu veya son kademe kanat yüksekliğini tek başına belirlemez.

Önerilen modelleme yöntemi: Giriş ve çıkış kesitleri, M2'nin belirlediği booster çıkış koşulları ve genel motor çevrimiyle tutarlı olacak şekilde hesaplanmalı. Hesaplanan ölçüler, üretici geometrisi bulunana kadar tahmin olarak etiketlenmeli.
M3.4. Bleed noktaları ve kademeleri
HPC havası, motorun ikincil hava sistemi içinde soğutma ve basınçlandırma gibi amaçlarla kullanılır. Ancak her bir bleed hattının kesin bağlantı kademesini ve debisini belirlemek için CFM56-7B'ye özgü ikincil hava şeması gerekir.

CTC-215 veya CFM56-7B eğitim dokümanları, bu araştırmada incelenmesi gereken kaynaklar arasında. Fakat henüz her hattın başlangıç kademesini ve debisini doğrulanmış sayısal veri olarak çıkaramadım.
M3.5. Ti → Ni geçişi, tambur ve disk yapısı, LLP ömürleri
Aircraft Commerce rehberindeki, Tech Insertion öncesi -7B motorlarına ait tabloda HPC bölümünde şu parçalar listeleniyor:
HPC parçası	CFM56-7B27 için bildirilen ömür
Forward shaft	20.000 EFC
Stage 1–2 spool	20.000 EFC
Stage 3 disk	20.000 EFC
Stage 4–9 spool	20.000 EFC
CDP seal	20.000 EFC



Bu değerler, rehberin Tech Insertion öncesi motorlar için verdiği tablodan alınmıştır. aircraft-commerce.com

EFC, Engine Flight Cycle anlamına gelir. Bu değerleri saat cinsinden ömürle karıştırmamak gerekir.

Malzeme geçişi, tambur ve disk yapısı bakımından açık kaynaklarda -7B27'nin bütün parçalarını malzeme sınıfına ve kademe konumuna göre eşleyen doğrulanmış bir tablo bulamadım. Bu nedenle titanyum alaşımından nikel bazlı süperalaşıma geçişin kesin kademesini şu aşamada işaretlemiyorum.

Burada ayrıca önemli bir ayrım var: LLP ömrü, parçanın bütün koşullarda ulaşacağı fiziksel ömür değildir; onaylı limitlerle ilişkili bakım/ömür sınırıdır. Yukarıdaki değerler gerçek bir motorun kalan ömrünü belirlemek için tek başına kullanılamaz.
M3.6. Küçük çekirdek verim kaybı
DiOrio'nun MIT tezinde iki önemli mekanizma inceleniyor:

1. Reynolds sayısı: Küçük çekirdekli kompresörlerde Reynolds sayısının düşmesi, yüksek Reynolds sayısına göre tasarlanmış kanatlarda kademe verimini azaltabilir.
2. Uç boşluğu: Kanat uç boşluğunun kanat açıklığına oranının artması, kaçak akışını ve verim kaybını artırabilir.
Tezde, belirli küçük çekirdek koşullarında Reynolds sayısına bağlı olarak yüzde 1,9'a kadar kademe verimi kaybı ve uç boşluğuna ilişkin ek verim cezaları hesaplanmaktadır. Bunlar belirli araştırma koşullarına ait sonuçlardır; CFM56-7B27 için ölçülmüş verim kaybı değerleri değildir. MIT Open Scholarship

M3 modülünde bu çalışmayı kullanarak:

* Kademe verimi için uç boşluğu düzeltmesi,
* Reynolds sayısına bağlı düzeltme,
* Tasarım ve analiz sonuçları arasındaki verim farkının açıklanması
gibi işlevler oluşturabiliriz.
M3 için sonuç
Doğrulandı: Dokuz kademe, genel motor mimarisi ve belirli bakım ömürleri.

Genel referans mevcut: NASA TP-1523, E3 CR-168211 ve DiOrio MIT tezi.

Açık kalanlar: Kademe bazında kanat sayıları, gerçek iç yarıçaplar, son kademe kanat yüksekliği, ayrıntılı bleed çizelgesi ve Ti/Ni geçişinin kesin konumu.
3. M4 — Yanma odası (Combustor)
M4.1. SAC konfigürasyonu ve enjektör sayısı
İlk olarak doğru konfigürasyonu seçmeliyiz: CFM56-7B27 SAC, yani Single Annular Combustor.

EASA'nın CFM56-7B veri sayfası SAC ve DAC konfigürasyonlarını ayrı ayrı tanımlar. Dolayısıyla CFM56-7B27 için hazırladığımız referansın DAC değil SAC olduğunu açıkça belirtmeliyiz. Tech Insertion uygulanmış motorlarda ise değiştirilmiş HPC, yanma odası ve HPT bulunduğundan /3 gibi varyant eklerini de dikkate almak gerekir. (EASA veri sayfası kopyası; Aircraft Commerce rehberi)

Açık kaynaklarda bulunan CFM56-7B eğitim dokümanlarına göre SAC yanma odasında:

* 20 yakıt enjektörü bulunur.
* Yanma odası, HPC'nin dokuzuncu kademesinden sonra ve HPT nozulundan önce yer alır.
* İç ve dış liner kullanılır.
* Yakıt-hava karışımını iyileştirmek için swirl elemanları bulunur.
* Liner üzerindeki film soğutma delikleri, sıcak gazla temas eden yüzeylerin korunmasına yardımcı olur.
* Eğitim dokümanları linerların iç yüzeylerinde termal bariyer kaplaması (TBC) bulunduğunu belirtir.
Kaynak: CFM56-7B yanma odası eğitim dokümanı.
Geometri için durum
Parametre	Bulgu	Durum
Yanma odası tipi	SAC, halka tipi	Doğrulandı
Yakıt enjektörü sayısı	20	Doğrulandı
İç ve dış liner	Mevcut	Doğrulandı
Film soğutma	Mevcut	Doğrulandı
TBC	Eğitim dokümanlarında belirtiliyor	Doğrulandı
Dış çap	Doğrudan ölçü bulunamadı	Açık
İç çap	Doğrudan ölçü bulunamadı	Açık
Toplam uzunluk	Doğrudan ölçü bulunamadı	Açık
Yanma odası hacmi	Doğrudan ölçü bulunamadı	Açık
Liner et kalınlığı	Doğrudan ölçü bulunamadı	Açık
Enjektörlerin açısal yerleşimi	20 enjektörlü düzen biliniyor; kesin koordinatlar doğrulanmadı	Kısmen doğrulandı



Önemli: Bir çizimde görülen yanma odası dış çapı, iç çapı ve uzunluğu ölçekli ve referans ölçülü değilse gerçek ölçü kabul edilmemeli. Böyle bir geometriden ölçüm yapılırsa \[T] etiketi kullanılmalı.
M4.2. Basınç kaybı ve yanma verimi
Yanma odasının termodinamik modelinde iki ayrı parametre gerekir:

1. Toplam basınç kaybı: Yanma odasından geçerken toplam basıncın ne kadar azaldığını gösterir.
2. Yanma verimi: Yakıtın kimyasal enerjisinin ne kadarının akışa aktarıldığını ifade eder.
Bu iki parametre birbirinin yerine kullanılamaz.

NASA CR-168211, E3 araştırma motorunun tasarım ve test sonuçlarını içerdiği için yanma odası ve çekirdek motor performansını incelemek açısından aday kaynaktır. Ancak bu rapordaki değerler CFM56-7B27'nin ölçülmüş basınç kaybı veya yanma verimi olarak aktarılmamalıdır. NASA CR-168211

Bu araştırmada CFM56-7B27 SAC için doğrudan doğrulanmış, kaynaklı bir basınç kaybı ve yanma verimi tablosu bulamadım.

Modelde kullanılacak yöntem:

* Yanma odası giriş koşulları HPC çıkışından alınmalı.
* Basınç kaybı ayrı bir parametre olarak tanımlanmalı.
* Yanma verimi, yakıt-hava oranı ve enerji dengesiyle birlikte ele alınmalı.
* E3 veya genel yanma odası korelasyonları kullanılacaksa bunlar correlation\_reference olarak işaretlenmeli.
* CFM56-7B27'ye aitmiş gibi gösterilmemeli.
M4.3. ICAO emisyon verileri
Bu başlıkta doğrudan CFM56-7B27'ye ait bir açık kaynak belgesi bulabildim: ICAO-3CM034.

Belge, motorun emisyon sertifikasyon verilerini ve LTO (Landing and Take-Off) çevrimi sonuçlarını içeriyor. Kaynak: CFM56-7B27 ICAO emisyon belgesi.

Belgedeki temel bilgiler:
Parametre	Belgedeki değer
Motor tanımı	CFM56-7B27
Benzersiz veri numarası	3CM034
Bypass oranı	5
Basınç oranı	28,63
Sertifikasyon itki değeri	121,44 kN
HC, özgül emisyon değeri	4,3 g/kN
CO, özgül emisyon değeri	34,7 g/kN
NOx, özgül emisyon değeri	64,1 g/kN
Duman sayısı	20,2



Burada önemli bir ayrıntı var: Belge, ilk tabloda sertifikasyon/regülasyon verilerini; devamında ise farklı güç ayarlarında ölçülmüş emisyon verilerini veriyor. Bu nedenle iki veri kümesi karıştırılmamalı.
LTO ölçüm verileri
Çalışma koşulu	Güç ayarı	Süre	Yakıt debisi (kg/s)	HC (g/kg)	CO (g/kg)	NOx (g/kg)
Take-off	%100	0,7 dk	1,284	0,1	0,2	30,9
Climb-out	%85	2,2 dk	1,043	0,1	0,5	23,7
Approach	%30	4,0 dk	0,349	0,1	1,4	11,0
Idle	%7	26,0 dk	0,116	1,7	17,9	4,8



Kaynak: ICAO-3CM034, ölçülmüş veriler tablosu.

Kullanım sınırı: Bu değerler belirli bir test motorunun sertifikasyon verileridir. Güncel üretim standardının veya bütün CFM56-7B27 alt varyantlarının aynı emisyon değerlerine sahip olduğunu varsaymamalıyız.
M4.4. Liner malzemesi, TBC ve soğutma düzeni
Açık eğitim dokümanlarında linerların iç ve dış yüzeyleri, film soğutma delikleri ve TBC açıkça gösteriliyor. Ancak bu araştırmada SAC linerı için alaşım sınıfını, kaplama bileşimini ve kaplama kalınlığını -7B27'ye özgü bir malzeme tablosuyla doğrulayamadım.

Bu nedenle modelde şu ayrım korunmalı:

* Geometrik özellikler: İç/dış liner, dome ve soğutma delikleri.
* Malzeme özellikleri: Henüz doğrulanmamış; tahmin gerekiyorsa ayrı tutulmalı.
* Kaplama: TBC varlığı doğrulanmış, kimyasal bileşim ve kalınlık açık.
* Soğutma: Film soğutma doğrulanmış, delik çapları ve soğutma debileri açık.
M4 için sonuç
Doğrulandı: SAC mimarisi, 20 yakıt enjektörü, liner yapısı, film soğutma ve TBC varlığı; ayrıca CFM56-7B27'ye ait bir ICAO emisyon belgesi.

Açık kalanlar: Yanma odasının gerçek iç ölçüleri, liner malzeme sınıfları, basınç kaybı, yanma verimi ve soğutma debileri.
4. M5 — HP türbin (High-Pressure Turbine)
M5.1. Kademe sayısı ve temel mimari
CFM56-7B ailesinde HPT tek kademelidir. Bu bilgi EASA veri sayfasında ve CFM56-7B motor mimarisini anlatan teknik kaynaklarda belirtilmektedir. (EASA veri sayfası kopyası)

HPT, yanma odasından çıkan sıcak gazın enerjisinin bir bölümünü HP miline aktararak HPC'yi döndürür.
Parametre	Bulgu
HPT kademe sayısı	1
NGV	Tek kademeli HPT nozul sırası
Rotor	Tek kademeli HPT rotor sırası
Soğutma	HPT soğutmalı yapı
Kanat sayıları	Doğrudan doğrulanmış sayısal tablo bulunamadı



NGV, Nozzle Guide Vane anlamına gelir. NGV ve rotor kanat sayılarının ayrı ayrı bilinmesi gerekir; yalnızca tek kademe bilgisi yeterli değildir.
M5.2. Gauntner TM-81453: Soğutma algoritması
NASA TM-81453, türbin kanatlarının soğutulması için gereken kompresör havasını ve bu havanın türbin verimi üzerindeki etkisini hesaplayan bir algoritma sunar. Çalışmada farklı soğutma konfigürasyonları ele alınır. NASA TM-81453

Bu kaynak M5 için özellikle yararlı. Motor modelinde:

* Soğutma havası ihtiyacı,
* Soğutma havasının ana gaz akışına karışmasının etkisi,
* Soğutma nedeniyle oluşan verim kaybı,
* Farklı soğutma düzenlerinin karşılaştırılması
gibi hesaplamalar için kullanılabilir.

Ancak algoritma, CFM56-7B27'nin gerçek soğutma deliklerini veya gerçek soğutma debilerini kendiliğinden sağlamaz. Bunlar için motorun kendi geometrisi ve çalışma koşulları gerekir.
M5.3. Referans HPT, yük katsayısı ve verim
E3 CR-168211, türbin performansı için değerlendirilebilecek araştırma kaynaklarından biridir. Bununla birlikte E3 türbini, CFM56-7B27'nin doğrudan geometrik karşılığı değildir. NASA CR-168211

Bu araştırmada aşağıdaki değerler için CFM56-7B27'ye özgü doğrulanmış sayısal veri bulamadım:

* HPT rotor kanat sayısı.
* NGV kanat sayısı.
* Kademe yük katsayısı.
* Gerçek türbin giriş sıcaklığı ve kademe bazında sıcaklık dağılımı.
* Gerçek HPT soğutma debileri.
Yük katsayısı sınırı da yalnızca tek bir genel sayıyla belirlenmemeli. Kademe yükü; çevresel hız, entalpi düşüşü, gaz akışı ve tasarım koşullarıyla birlikte değerlendirilmelidir.
M5.4. Malzemeler, kaplamalar ve LLP ömürleri
Aircraft Commerce rehberinin Tech Insertion öncesi -7B tablosunda HPT için şu değerler veriliyor:
HPT parçası	CFM56-7B27 için bildirilen ömür
Front shaft	17.300 EFC
Front air seal	17.300 EFC
Disk	19.200 EFC
Rear shaft	20.000 EFC



Kaynak: Aircraft Commerce, CFM56-7B LLP Lives tablosu.

Bu değerler belirli bir konfigürasyon grubuna aittir; bütün -7B27 motorlarına ve bütün revizyonlara otomatik olarak uygulanmamalı.

HPT kanat ve disklerinin malzeme sınıfları, kaplama bileşimleri ve kaplama kalınlıkları için bu araştırmada CFM56-7B27'ye özgü, açık ve doğrulanmış bir tablo bulamadım.
M5 için sonuç
Doğrulandı: Tek kademeli HPT mimarisi, soğutmalı yapı ve belirli bakım ömrü verileri.

Genel referans mevcut: NASA TM-81453 soğutma algoritması ve E3 türbin araştırmaları.

Açık kalanlar: Kanat sayıları, gerçek soğutma debileri, malzeme sınıfları, kaplama özellikleri ve CFM56-7B27'ye özgü kademe yük sınırları.
5. M6 — LP türbin (Low-Pressure Turbine)
M6.1. Kademe sayısı ve temel yapı
CFM56-7B ailesinin LPT'si dört kademelidir. Görevi, gaz akışından enerji çekerek LP milini, fanı ve booster'ı döndürmektir. Bu mimari EASA veri sayfası ve Aircraft Commerce rehberinde doğrulanmaktadır. (EASA veri sayfası kopyası; Aircraft Commerce rehberi)
Parametre	Bulgu
LPT kademe sayısı	4
Her kademedeki rotor sayısı	Her kademede bir rotor sırası
Her kademedeki statör sayısı	Her kademede bir statör/nozul sırası temel alınabilir
Kademe bazında rotor kanat sayısı	Doğrulanmış tablo bulunamadı
Kademe bazında statör kanat sayısı	Doğrulanmış tablo bulunamadı



Son iki parametreyi ayrı ayrı tutmalıyız. Rotor ve statör kanat sayılarının birbirine eşit olması gerektiği gibi bir varsayımda bulunmamalıyız.
M6.2. Referans LPT ve verim
NASA CR-168211, araştırma motorunun türbin performansını ve tasarımını incelemek için kullanılabilir. Ancak E3 LPT'sinin geometrisini doğrudan CFM56-7B27'ye kopyalamak doğru olmaz. NASA CR-168211

LPT tasarımında her kademe için ayrı değerlendirilmesi gereken temel değişkenler şunlardır:

* Kademe entalpi düşüşü.
* Rotor çevresel hızı.
* Kademe yük katsayısı.
* Gaz giriş ve çıkış açıları.
* Kanat katılığı ve kanat açıklığı.
* Kademe verimi ve toplam türbin verimi.
Bu parametreler için doğrudan -7B27 ölçümlerine dayalı bir tablo henüz doğrulanmış değil.
Zweifel ölçütü
Zweifel ölçütü, türbin kanat sıralarındaki aerodinamik yüklenmeyi değerlendirmek için kullanılan boyutsuz bir ölçüttür. M6 modülünde kanat katılığı ve çıkış akış açısıyla birlikte kullanılabilir.

Ancak Zweifel ölçütünü tek başına kanat tasarımını onaylayan bir kriter olarak kullanmamalıyız. Kanat geometrisi, hız üçgenleri, kayıplar, çalışma noktası ve mekanik sınırlar da değerlendirilmelidir.

Bu araştırmada CFM56-7B27'nin dört LPT kademesi için doğrulanmış yük katsayısı veya Zweifel değeri bulamadım.
M6.3. Malzeme ve LLP ömürleri
Aircraft Commerce rehberinde Tech Insertion öncesi -7B27 için LPT LLP tablosunda şu değerler yer alıyor:
LPT parçası	Bildirilen ömür

1. kademe diski	25.000 EFC
2. kademe diski	25.000 EFC
3. kademe diski	25.000 EFC
4. kademe diski	23.900 EFC
LPT şaftı	25.000 EFC
Konik destek (conical support)	16.300 EFC



Kaynak: Aircraft Commerce — CFM56-7B LLP Lives.

Bu tabloyu modelde kullanırken konfigürasyonun Tech Insertion öncesi olduğunu açıkça belirtmeliyiz.

LPT kanatlarının malzeme sınıfları ve kaplama detayları için CFM56-7B27'ye özgü doğrulanmış bir açık kaynak tablosu bulamadım.
M6 için sonuç
Doğrulandı: Dört kademeli LPT mimarisi ve belirli LLP ömürleri.

Genel referans mevcut: E3 türbin performansı ve genel türbin yükleme yöntemleri.

Açık kalanlar: Kanat sayıları, kademe bazında iş dağılımı, gerçek yük katsayıları, malzeme sınıfları ve kaplama detayları.
6. M7 — Nozul, çerçeveler ve bypass kanalı
Bu modülde iki farklı alanı ayırmak gerekir:

1. Motorun gaz yolu ve nozul geometrisi.
2. Motoru taşıyan yapısal çerçeveler ve bypass kanalının yapısı.
M7.1. Motor boyutları ve gaz yolu
EASA veri sayfasında CFM56-7B ailesi için aşağıdaki genel ölçüler veriliyor:
Parametre	Değer
Genel uzunluk	2.508 mm
Genel genişlik	2.118 mm
Genel yükseklik	1.829 mm



Kaynak: EASA CFM56-7B veri sayfası kopyası.

Bunlar motorun genel boyutlarıdır; çekirdek nozulunun, fan nozulunun veya bypass kanalının iç ölçüleri değildir.

Bu araştırmada aşağıdaki CFM56-7B27 değerlerini doğrudan doğrulayamadım:

* Çekirdek nozulunun çıkış alanı (A\_8).
* Fan/bypass nozulunun çıkış alanı (A\_{18}).
* Çekirdek nozulunun iç ve dış çapları.
* Nozul çıkış düzlemlerinin kesin eksenel konumları.
* Plug geometrisinin kesin ölçüleri.
* Bypass kanalının 13–18 istasyonları arasındaki uzunluğu ve yarıçap dağılımı.
Bu nedenle (A\_8) ve (A\_{18}) değerlerini gerçek motor ölçüleri gibi vermek yerine, motor çevrimi ve gaz yolu modelinden hesaplanan değişkenler olarak tutmak daha doğru olur. Üretici geometrisi veya güvenilir bir ölçülü çizim bulunduğunda bunlar doğrulanabilir.
M7.2. Nacelle tezi 247917 ve Lolis çalışması
Petrusson'un Chalmers Üniversitesi'nde hazırladığı tez, nacelle ve bypass kanalı geometrilerini eksenel simetrik bir model içinde ele alır. Çalışmanın temel konusu yüksek bypass oranlı motorların nacelle aerodinamiğidir. (Chalmers tez kaydı)

Bu nedenle tez, şu amaçlar için yararlı olabilir:

* Nacelle profilini modellemek.
* Bypass kanalının iç ve dış yüzeylerini temsil etmek.
* Geometriyi parametrik hâle getirmek.
* Eksenel kesit üzerinden ilk geometrik tahminleri oluşturmak.
Ancak tezdeki geometrinin CFM56-7B27'ye ait olduğu ayrıca doğrulanmadan ölçüler doğrudan motora atfedilmemeli.

Ölçekli çizimden ölçüm yapılırsa veri kaydında şu bilgiler bulunmalı:

* Kaynak belgenin adı ve sayfa/şekil numarası.
* Ölçüm için kullanılan referans boyut.
* Ölçek dönüşüm yöntemi.
* Ölçümün tahmini belirsizliği.
* \[T] etiketi.
Lolis çalışmasından veya başka bir genel turbofan tasarım tezinden elde edilen geometriler de aynı kurala tabi olmalı.
M7.3. Ayrı akışlı nozul düzeni ve mixer
CFM56-7B, yüksek bypass oranlı, iki milli turbofan mimarisine sahiptir. Bununla birlikte bu araştırmada -7B27 için nozul geometrisini, karıştırıcı bulunup bulunmadığını ve (A\_8/A\_{18}) alanlarını birlikte gösteren ölçülü bir üretici çizimi doğrulayamadım.

Bu yüzden ilk geometrik modelde çekirdek ve bypass akış yollarını ayrı bölgeler olarak tutabiliriz; fakat ayrı akışlı nozul düzeni ve karıştırıcı konfigürasyonu, doğrulanmış bir kesit çizimi veya teknik kaynakla ayrıca teyit edilmelidir.
M7.4. Türbin orta ve arka çerçeveler
CFM56-7B eğitim kaynakları fan çerçevesini, türbin arka çerçevesini ve bunların motor yapısındaki görevlerini açıklar. Ancak bu araştırmada türbin orta ve arka çerçevelerinin bütün strut sayılarını, kesitlerini ve malzemelerini veren doğrulanmış bir tablo bulamadım.

Bu başlıkta özellikle şu parametreler açık:
Parametre	Durum
Fan çerçevesi strut sayısı	Eğitim dokümanlarında 12 içi boş strut bilgisi bulunuyor
Türbin orta çerçevesi strut sayısı	Doğrulanmadı
Türbin arka çerçevesi strut sayısı	Doğrulanmadı
Strut kesit geometrileri	Doğrulanmadı
Çerçeve malzemeleri	-7B27'ye özgü tablo bulunamadı
Çerçevelerin kesin eksenel konumları	Ölçülü çizim gerekiyor



Burada fan çerçevesindeki 12 strut bilgisini türbin arka çerçevesine taşımamalıyız. Farklı yapısal bileşenler için ayrı parametreler gerekir.
M7 için sonuç
Doğrulandı: Genel motor ölçüleri ve temel turbofan mimarisi.

Genel referans mevcut: Nacelle geometrisi için Chalmers tezi.

Açık kalanlar: (A\_8), (A\_{18}), çekirdek nozul/plug geometrisi, bypass kanalının kesin boyutları ve türbin çerçevelerinin ayrıntılı yapısı.
7. M8 — Miller ve yataklar
M8.1. Yatak sayısı ve konumları
CFM56-7B motor ailesinin iki bağımsız dönen sistemi vardır:

* LP sistemi: Fanı, booster'ı ve LP türbinini içeren düşük basınçlı rotor sistemi.
* HP sistemi: HPC ve HPT'yi içeren yüksek basınçlı rotor sistemi.
Açık CFM56-7B eğitim materyallerinde motorun beş ana yatakla desteklendiği belirtiliyor. İki ayrı sump bölgesi, yatakların yağlanması ve sızdırmazlığı için kullanılıyor. Bu bilgiler CFM56-7B eğitim dokümanında ve Jet Engines – Bearings, Seals and Oil Consumption çalışmasında yer alıyor.
Yatak	Genel konum	Desteklediği sistem	Yatak tipi
No. 1	Ön sump, fan çerçevesi	LP mili	Bilyalı
No. 2	Ön sump, fan çerçevesi	LP mili	Makaralı
No. 3	Ön sump, fan çerçevesi	HP milinin ön bölgesi	Bilyalı ve makaralı elemanlardan oluşan düzen
No. 4	Arka sump, türbin bölgesi	HP milinin arka bölgesi	Makaralı
No. 5	Arka sump, türbin arka çerçevesi	LP milinin arka bölgesi	Makaralı



Not: Üç numaralı yatak düzeni bazı kaynaklarda çift yatak olarak açıklanır. Bu nedenle fiziksel yatak elemanı sayısı ile bakım dokümanlarındaki numaralandırmayı birbirine karıştırmamak gerekir.
M8.2. LP ve HP mil çapları
Bu araştırmada CFM56-7B27 için LP ve HP millerinin bütün kritik kesit çaplarını veren doğrulanmış bir açık kaynak çizimi bulamadım.

Bu parametreler özellikle önemli, çünkü yalnızca motorun toplam boyutundan veya yatak çaplarından hareketle güvenilir biçimde türetilemez.

Açık kalan parametreler:

* LP milinin yatak bölgelerindeki çapları.
* HP milinin yatak bölgelerindeki çapları.
* Milin iç ve dış çap dağılımı.
* Şaft bağlantı ve geçiş bölgeleri.
* Gerçek rotor kütle dağılımı.
* Rotorun atalet momentleri.
Bunları gerçek ölçü gibi göstermek yerine, geometrik modelde henüz tanımlanmamış parametreler olarak tutmak daha doğru olur.
M8.3. Kritik hız ve rotor dinamiği
Kritik hız hesabı için genel rotor dinamiği literatürü kullanılabilir. Ancak motorun gerçek kritik hızlarını hesaplamak için yalnızca yatak konumları ve şaft çapları yeterli değildir.

Hesaplama en azından şu bilgileri gerektirir:

* Şaftın çap ve et kalınlığı boyunca değişen geometrisi.
* Rotor disklerinin kütleleri ve atalet özellikleri.
* Yatakların dinamik rijitliği ve sönüm özellikleri.
* Çalışma sıcaklığının malzeme özelliklerine etkisi.
* Rotorun bağlantı ve sınır koşulları.
Bu nedenle M8'de iki ayrı sonuç tutulmalı:
1. Genel rotor dinamiği modeli: Literatürden alınan yöntemlerle geliştirilebilir.
2. CFM56-7B27'ye özgü kritik hızlar: Gerçek geometri ve yatak parametreleri olmadan doğrulanmış kabul edilemez.
M8.4. Fan şaftı LLP ömrü
Aircraft Commerce'un CFM56-7B bakım rehberinde fan şaftı için aşağıdaki ömür veriliyor:
Parça	CFM56-7B27 için bildirilen ömür
Fan şaftı	30.000 EFC



Aynı tabloda booster spool için -7B27 varyantında 22.900 EFC değeri veriliyor. Bu değer, diğer varyantlar için listelenen 23.600 EFC değerinden farklıdır.

Kaynak: Aircraft Commerce — CFM56-7B Owner's \& Operator's Guide.

Bunlar bakım rehberinde verilen ömür sınırlarıdır; belirli bir motorun kalan ömrünü göstermez.
M8.5. Fan kanadı kopması ve yatak yükü
Bu konu M1'deki containment çalışmasıyla bağlantılı. Ancak fan kanadı kopması sırasında oluşan yükleri belirlemek için genel bir yatak yükü katsayısı kullanmak yeterli olmaz.

İhtiyaç duyulacak bilgiler:

* Kopan kanadın kütlesi ve kopma yarıçapı.
* Rotorun kopma anındaki açısal hızı.
* Kopmanın meydana geldiği zaman aralığı.
* Rotorun geçici dinamik tepkisi.
* Yatakların yük aktarımı ve dinamik özellikleri.
* Gövde ve containment yapısının deformasyonu.
M8 için sonuç: Beş yatak, yatakların genel yerleşimi, iki sump ve fan şaftının bildirilen LLP ömrü destekleniyor. Gerçek şaft çapları, kritik hızlar ve kopma olayındaki yatak yükleri için daha ayrıntılı geometri ve analiz verileri gerekiyor.
8. M9 — İkincil hava, yağ ve aksesuarlar
M9.1. İkincil hava sistemi
İkincil hava sistemi, motorun ana gaz akışından alınan havayı çeşitli yardımcı işlevlerde kullanır. Bunlar arasında türbin bileşenlerinin soğutulması, boşlukların basınçlandırılması ve sızdırmazlık sistemlerinin desteklenmesi bulunur.

CFM56-7B eğitim materyallerinde kompresörün farklı kademelerinden hava alındığı ve bu havanın motorun çeşitli bölgelerine yönlendirildiği gösteriliyor. Bu başlık için en yararlı adaylardan biri senin de belirttiğin CTC-215 eğitim dokümanıdır. CTC-215 Basic Engine

Ayrıca CFM56-7B eğitim materyalindeki yanma odası ve yanma muhafazası çizimleri, dokuzuncu kademe bleed havasını ve çeşitli soğutma hatlarını gösteriyor. CTC-223 Basic Engine

Bununla birlikte, bu araştırmada bütün bleed noktalarını, her hattın debisini ve toplam çekirdek hava debisine oranını birlikte gösteren doğrulanmış bir -7B27 tablosu elde edemedim.
M9.1.1. Bleed noktaları ve soğutma debileri
İkincil hava modeli için aşağıdaki veri yapısını kullanmak uygun olur:
Parametre	Açıklama	Durum
Bleed noktası	Havanın hangi kompresör kademesinden alındığı	Bazı hatlar için eğitim dokümanı desteği var
Basınç	Bleed hattındaki toplam/statik basınç	Sayısal değerler açık
Sıcaklık	Bleed hattındaki hava sıcaklığı	Sayısal değerler açık
Kütlesel debi	Hattaki hava miktarı	Doğrulanmış tablo bulunamadı
Soğutma hedefi	Havanın hangi bileşene gönderildiği	Şemalardan kısmen izlenebilir
Toplam çekirdek akışına oran	İkincil hava payı	Doğrulanmış tablo bulunamadı



Bu değişkenler yalnızca geometri için değil, motorun termodinamik çevrimi için de önemlidir. Türbine gönderilmeyen veya ana akışa farklı koşullarda karışan hava, toplam verimi etkileyebilir.

NASA TM-81453, türbin soğutma debisi ve bunun türbin verimine etkisini hesaplamak için kullanılabilecek genel bir yöntem sunar. NASA TM-81453
M9.2. Yağ sistemi
CFM56-7B eğitim kaynakları, motorun iki sump bölgesi ve beş ana yatak üzerinden desteklenen kuru karterli yağlama düzenini açıklar.

Bu sistemde genel olarak şu işlevler bulunur:

* Yağın depolanması.
* Basınçlı yağ beslemesi.
* Yatakların yağlanması ve soğutulması.
* Sump bölgelerinden yağın geri toplanması.
* Sump basınçlandırması ve havalandırma.
* Yağ sıcaklığının kontrolü.
Kaynaklar: CFM56-7B Basic Engine eğitim dokümanı ve Jet Engines – Bearings, Seals and Oil Consumption.
Yağ sistemi için açık kalan parametreler
Parametre	Durum
Yağ tankının kesin hacmi	Doğrulanmış değer bulunamadı
Pompa debileri ve basınçları	Doğrulanmış değer bulunamadı
Yağ soğutucusunun ölçüleri	Doğrulanmış değer bulunamadı
Her sump için yağ dönüş debisi	Doğrulanmış değer bulunamadı
Sump basınçlandırma debileri	Doğrulanmış değer bulunamadı
Conta ve sızdırmazlık elemanlarının tam listesi	Doğrulanmış tablo bulunamadı
Onaylı yağ tipi ve spesifikasyonu	Güncel, uygulanabilir üretici dokümanıyla doğrulanmalı



Yağ tipi için yalnızca genel bir havacılık yağı standardına dayanarak seçim yapmak yerine, CFM'nin ilgili motor konfigürasyonu için onayladığı yağ spesifikasyonu kullanılmalı. Üreticinin CFM teknik dokümanları sayfası, bu doğrulama için ilk başvuru noktasıdır.
M9.3. Aksesuar dişli kutusu ve radyal mil
CFM56-7B eğitim materyalinde aksesuar tahrik sistemi, HP rotorundan güç alarak motor ve uçak aksesuarlarını çalıştıran bir sistem olarak tanımlanır.

Temel mimaride şu elemanlar bulunur:

* Inlet Gearbox (IGB).
* Radial Drive Shaft (RDS).
* Transfer Gearbox (TGB).
* Horizontal Drive Shaft (HDS).
* Accessory Gearbox (AGB).
Kaynak: CFM56-7B Basic Engine eğitim dokümanı.

Ancak aksesuarların kesin kütlelerini ve üç boyutlu konumlarını veren bir -7B27 yerleşim tablosunu bu araştırmada doğrulayamadım.

Bu nedenle M9 modelinde aksesuarlar için aşağıdaki parametreler tutulabilir:
Parametre	Kullanım
Aksesuar türü	Başlangıç, elektrik üretimi, yakıt veya yağ sistemi işlevi
Montaj konumu	Ana motor koordinat sistemine göre konum
Kütle	Kütle ve ağırlık merkezi hesabı
Tahrik bağlantısı	İlgili dişli kutusu ve mil bağlantısı
Güç ihtiyacı	Motorun mekanik güç dengesi
Devir oranı	Aksesuar çalışma hızının hesabı



Gerçek kütleler ve koordinatlar bulunana kadar bunlar tahmin olarak tutulmalı.
M9.4. Yakıt pompası ve kontrol ünitesi
Yakıt pompası ve kontrol sistemi için de aynı yöntem geçerli.

İlk geometrik modelde:

* Yakıt pompası.
* Yakıt kontrol sistemi bileşenleri.
* Bağlantı hatları.
* Montaj noktaları.
* Tahmini kütle ve hacim.
ayrı bileşenler olarak tanımlanabilir.

Ancak bu araştırmada CFM56-7B27 için pompa ve kontrol ünitesinin kesin kütlelerini, koordinatlarını ve bağlantı ölçülerini gösteren doğrulanmış bir açık kaynak tablosu bulamadım.

Bu nedenle ilk sürümde kullanılacak değerler açıkça \[T] olarak işaretlenmeli.
M9.5. Yağ sarfı
Motorun yağ sarfı, yağ sisteminin boyutlandırılması ve bakım gereksinimleri açısından önemlidir. Ancak yalnızca tank hacminden veya genel motor boyutlarından hareketle yağ sarfı hesaplanamaz.

Bu araştırmada CFM56-7B27'nin yağ sarfını belirli bir çalışma koşulunda gösteren, doğrulanmış bir üretici tablosu bulamadım.

Modelde yağ sarfını şu değişkenlerle ilişkilendirmek daha doğru olur:

* Çalışma süresi.
* Motor çalışma koşulu.
* Yağ tüketim ölçüm yöntemi.
* Bakım ve sızdırmazlık durumu.
* Üreticinin tanımladığı kabul sınırları.
M9 için sonuç: Beş yatak, iki sump, temel yağlama mimarisi ve aksesuar tahrik düzeni açık eğitim kaynaklarıyla destekleniyor. Bleed debileri, yağ sistemi boyutları, yağ sarfı ve aksesuar kütleleri ise henüz doğrulanmış değil.
9. Toplu durum tablosu: M3–M9
Aşağıdaki tablo, araştırmanın sonunda hangi parametreleri doğrudan kullanabileceğimizi ve hangilerinin açık kaldığını özetliyor.
Modül	Doğrulanmış ana bilgiler	Açık kalan kritik veriler
M3 — HP kompresör	9 kademe; bazı HPC LLP ömürleri; VSV düzenine ilişkin eğitim dokümanı	Kademe bazında kanat sayıları, yarıçaplar, kanat yükleri, bleed debileri, malzeme geçişleri
M4 — Yanma odası	SAC konfigürasyonu, 20 enjektör, film soğutma, TBC varlığı, ICAO emisyon belgesi	Gerçek iç ölçüler, basınç kaybı, yanma verimi, malzeme sınıfları ve soğutma debileri
M5 — HP türbin	1 kademe, soğutmalı yapı, belirli LLP ömürleri	NGV/rotor kanat sayıları, gerçek soğutma debileri, malzeme ve kaplama özellikleri
M6 — LP türbin	4 kademe, belirli LLP ömürleri	Kademe bazında kanat sayıları, yük katsayıları, malzemeler ve kaplamalar
M7 — Nozul ve çerçeveler	Genel motor ölçüleri ve gaz yolu mimarisi	(A\_8), (A\_{18}), nozul ve plug geometrisi, bypass kanalının ölçüleri, türbin çerçevelerinin ayrıntıları
M8 — Miller ve yataklar	5 yatak, 2 sump, yatakların genel konumları, fan şaftı LLP ömrü	Gerçek mil çapları, kritik hızlar, yatak rijitlikleri ve kopma anındaki yükler
M9 — İkincil hava, yağ ve aksesuarlar	Temel bleed ve yağlama sistemi mimarisi, aksesuar tahrik elemanları	Bleed debileri, yağ pompası verileri, yağ sarfı, aksesuar kütleleri ve konumları



9.1. Güven düzeyini nasıl kaydetmeliyiz?
Turbofan Engine Agent'ın veri tabanında her parametreye bir kaynak ve durum alanı eklenmesini öneriyorum:
Etiket	Anlamı	Örnek
\[V1]	Birincil veya güvenilir teknik kaynakta doğrudan doğrulandı	HPC kademe sayısı
\[V2]	Motor ailesi veya benzer motor için doğrulandı; hedef varyanta uygulanabilirliği ayrıca kontrol edilmeli	Genel malzeme veya performans referansı
\[T]	Ölçekli çizimden ölçüldü veya mühendislik tahminiyle elde edildi	Nacelle profilinden türetilen yarıçap
\[A]	Analitik model veya korelasyonla hesaplandı	Tahmini kademe verimi
\[U]	Henüz doğrulanmadı	HPC rotor kanat sayısı



Burada \[A] ile \[V1] özellikle farklı olmalı. Bir değerin matematiksel olarak hesaplanması, onun gerçek motor üzerinde ölçülmüş olduğu anlamına gelmez.

Ayrıca her veri kaydında aşağıdaki bilgilerin tutulması yararlı olacaktır:

* Parametre adı ve birimi.
* Motor modeli ve alt varyantı.
* Kaynak belge ve sayfa/şekil numarası.
* Kaynağın yayımlanma tarihi ve sürümü.
* Doğrulama durumu.
* Tahmin varsa yöntem ve belirsizlik.
* Kullanıldığı CAD, termodinamik veya yapısal analiz modülü.

