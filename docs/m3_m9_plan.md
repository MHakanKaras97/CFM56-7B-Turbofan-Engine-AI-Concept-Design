# M3-M9 planı (konsept geometri ve son montaj)

Kullanıcı kararı (2026-10-31): M0, M1, M2 know-how kabul edildi; M3-M9 planlaması ve yürütmesi M0 ana oturumuna
bırakıldı (soru yok). Sıra: her modül için önce BOM, sonra sistem (boyutlandırma + akış yolu), sonra parça
STEP'leri; en sonda M0 son montaj STEP'i. Testler tüm modüller bittikten sonra modül modül yazılır ve koşulur.

## Yöntem (tüm modüller)
- Girdi: yalnız `read_icd("<M> design")` (istasyon Tt/Pt/W/FAR, bütçeler) + yukarı akış modülünün türetilmiş
  `geometry/flowpath.yaml` arayüzü (salt okunur). Elle yazılmış tasarım sayısı yok; kurallar `rules/design.md`'de
  [T]/[G]/[KS] etiketli, koddan önce.
- Ortak araç: `tools/concept.py` (anülüs boyutlandırma: kütle akısı fonksiyonu, malzeme yoğunlukları [G],
  döner katı, kanat, disk, montaj ve STEP dışa aktarımı, BOM yazımı `core.bom.write` ile).
- Modül dosyaları: `analysis/design.py` (sistem: params -> results, `geometry/flowpath.yaml` çıkış arayüzü),
  `geometry/parts.py` (parçalar), `geometry/build.py` (BOM + parça STEP'leri + modül montajı).
- Kayıt: her modül rev001 (tasarım kaydı, kabul değil); `create_revision` kod commit'inden sonra.
- Konsept derinliği: kanatlar dairesel yay profilli göbek-uç loft, diskler rim/gövde/göbek döner katı, kasalar
  döner kabuk. Yapısal analiz yok (ADR-016 kabulü sonraki aşama); kütle = hacim x yoğunluk [H], bilgi.

## Arayüz zinciri (X ekseni M1 çerçevesi, fan istifleme düzleminden geriye)
- M3: ist. 25 (M2 flowpath.yaml) -> giriş S-kanalı -> IGV + 9 kademe -> ist. 3 (çıkış arayüzü M4'e).
- M4: ist. 3 -> difüzör, SAC (20 enjektör [KS]) -> ist. 4 (M5'e).
- M5: ist. 4 -> NGV + 80 rotor kanadı [KS] -> ist. 44 (M6'ya).
- M6: ist. 44 -> geçiş kanalı 45 -> 4 kademe (162/150/150/134 [KS]) -> ist. 5 (M7'ye).
- M7: ist. 5 -> türbin arka çerçevesi -> çekirdek lülesi (A8 ICD) ; ist. 13 (M1) -> baypas kanalı -> fan lülesi (A18 ICD).
- M8: LP mili (fan diski -> LPT), yataklar #1-#5, ön/arka hazne destekleri (M1 göbek halkası flanşı r 0.151065, M7 TRF).
- M9: dişli kutusu (AGB, TGB, IGB, radyal mil), yağ tankı ve boruları, HPC hava alma boruları (ICD secondary_air).
- M0: `engine/M0_engine/geometry/final_assembly.py` M1 rev015 + M2 rev002 + M3-M9 rev001 montajlarını tek STEP'te birleştirir.

## Sapmalar ve sınırlar
- Ayrıntılı aero (DF, kayıp korelasyonları) M3/M5/M6'da yok: kademe başına eşit iş, sabit eksenel Mach [T];
  verimler M0 bütçesinden (ADR-015 emsali). Bilinen sapma olarak open_issues'a yazılır.
- Mimari belgesi türbin çerçevesini M6'ya veriyordu; 2026-10-29 kararıyla M7 (architecture.md düzeltildi).
