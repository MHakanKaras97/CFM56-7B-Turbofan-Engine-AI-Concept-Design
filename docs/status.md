# Proje durumu

## Amaç
CFM56-7B27 sınıfı (temel, SAC) turbofan için konsept seviyesinde çoklu agent tasarım sistemi.
M0 motor agent'ı + M1–M9 modül agent'ları (Claude Code subagent). Öğrenmek + belgelemek.

## Temel kararlar
- Mimari: docs/architecture.md, ADR-001..011.
- Tek doğru kaynak: bom.yaml + kod; Fusion sadece görünüm (STEP).
- Revizyonlar değişmez; aktif = records/ACTIVE. Değişiklik yalnızca CR + kullanıcı onayı.
- Güven etiketleri: K, KS, H, G, T. Sayılar koddan gelir, LLM metninden değil.
- Telif: kendi cümlelerimiz, kaynaklar docs/sources.md'de lisansıyla; PDF/xlsx git'e girmez.
- Tasarım noktası: deniz seviyesi, ISA, maksimum kalkış. Seyir noktası sonra.
- M8 devir referansları M0 kurallarında (girao_2023.yaml); M8'e aktarım M8'in işi.
- Çalışma döngüsü (her modül): ders -> araştırma -> rule book -> kod -> kabul testi. Testsiz sonraki modüle geçilmez.

## Kararlar (2026-10-18, UI öncesi)
- "Fusion'da aç": kullanıcı Windows'ta .step dosyalarını Fusion ile ilişkilendirir; UI işletim sistemi ilişkilendirmesini kullanır, sabit yol yok.
- CR şeması: yapısal "impact" alanı (metrik -> {value, unit, tag}); UI kartları buradan okur.
- core: Revizyonlar sayfası için revizyon farkı fonksiyonu.
- Araç yolları: config/tools.local.yaml (git dışı, makineye özel) + config/tools.example.yaml (commit). Kod araç yollarını yalnızca buradan okur (core/toolpaths.py).
- Talepler sayfası: tek "Kararı kaydet" düğmesi; (b) seçeneği = ret. Kabul edildi.

## Son yapılanlar
- M1 adım 4b: kayıp modeli incelemesi (PDF sayfa): (i) profil kaybı 2B kaskat verisinden (Sjögren 22-23, Abrisha 37), çift sayım yok; (ii) şok: Schwenk/MLH geçit şoku (Sjögren 24, Visentin 32, Zanoni 20), Boyer-Miller-Bloch (Abrisha 40); bizimki zaten geçit şoku; (iii) uç kaybı %80 açıklığın üstünde (Zanoni 16) -> uygulandı (ağırlık 5, şekil [T]). Kayıp dağılımı (loss_review) tasarım noktası 1-η 0.163: profil 0.028, şok 0.068, uç duvar 0.030, uç 0.024 (ölçülen tepe açığı 0.072). RE uç tüplerine alan verip orta açıklık işini düşürüyor. A-1 kaldı: tasarım PR -%5.9, stall yakını PR -%9.1, η 0.834 (0.901). ADR-014 taslağı (mekanizma başına çarpan; tasarım noktasında yalnız PR var -> belirlenemez, seçenek (a): tepe verim profili ile) uygulanmadı. B çalıştırılmadı.
- M1 adım 4: M0 rev008 bakım (fan_diameter T -> K, #42; core.diff: T'den yeniden etiketlenen varsayımın sonuçlardan düşmesi 'retagged', engellemez), ICD rev008'den (bütçeler aynı). Kayıp korelasyonlarının kitap formu meanline docstring'inde [G] (Howell: Saravanamuttoo, Dixon & Hall; Lakshminarayana 1970). tools/meanline.py solve_rotor_re: basit radyal denge (h0, s gradyanlı), çıkış tüp alanları/yarıçapları kayar, gevşetme 0.1, eğrilik ihmal. Rotor 67 A-1 (radial_equilibrium_diagnostic): RE kayıpsız PR +%1.3 geçer; RE + kayıplar uç tıkanmasını kaldırır ama PR -%4.5, η 0.850 -> KALDI, durduruldu, ayar yok; tepe verimde göbek 1.744 -> 1.666 (ölçüm 1.609), orta/uç 0.13-0.22 düşük. B (fan yeniden tasarımı) çalıştırılmadı. R-AM.9 onaylı (%45 altı DF, üstü DF + solidite Rotor 67'den az olmaz). CR-001 kullanıcı tarafından UI'da reddedildi (b), commit edildi.
- M1 adım 3b: create_revision commit edilmemiş kodu (core/, tools/, engine/*/analysis/*.py) reddeder (testli; CLAUDE.md: her commit öncesi tam test). M1 rev002 yeniden üretilemez (code_commit fan_design.py'den önce; M1 REVIEW.md) -> rev003 bakım (aynı sayılar, 091135c). ADR-013: genel modül hesap arayüzü (calc.py). Fan çapı 61 in [K] (CFM 1997 makalesi, sources #42); aynı makale 22 kanat diyor, Fox 2023 üretim motorlarında 24 [KS] -> 24 kalır; 24 kanat 118 kg [KS zayıf, Mirghani] kontrol değeri. tools/meanline.py: Howell uç duvar + Lakshminarayana uç boşluğu kaybı [G] (kaynak setinde katsayılı form yok), parabolik açıklık ağırlığı [T]. Açıkken Rotor 67 tasarım PR -%7.0 (uç tüpler çıkışta tıkanıyor), göbek 1.744 -> 1.721 (ölçüm 1.609): kayıplar KAPALI, önce radyal denge (kullanıcı kararı); B (fan yeniden tasarımı) durduruldu. Rotor 67 DF tüp başına rotor67_reference.yaml `computed_diffusion_factor` [H]: 0.39 göbek, 0.46 orta, 0.39-0.40 üst; R-AM.9 önerisi (aynı bağıl açıklıkta Rotor 67'yi aşma). CR-001 depoda hâlâ açık (UI kararı kaydedilmemiş; kullanıcı: açık kalsın).
- M1 adım 3: Rotor 67 override dosyası (s7 LE 51.41, s9 0.42137), açı duyarlılığı ±0.22° (ΔPR ≤ 0.0077, Δη ≤ 0.0009), kuş sınıfı zarfı (vekille aynı). m1-inlet-fan ilk fan tasarımı (rev002): uç Mrel 1.436, dış FPR 1.765 η 0.8906, iç PR 1.344 η 0.978, kök gerilmesi 239 MPa pay 2.07; DF uçta geçmiyor. Bütçe 9/10 (eta_fan_inner +0.091). Entegrasyon: SFC -%0.52, EGT -6.0 K -> CR-001 (a)/(b).
- M1 adım 2b: Rotor 67 Tablo I temiz sayısal kopyası (BladeAtlas, commit sabit, sha256 kontrollü; sources #41): Z, R, THSP1, THSP2, kenar daireleri [KS]. İşaretsiz OCR ile 1774 değerde 1554 eşit, kalan 220 yalnızca 3/5, 4/6, 8/3 rakam karışıklığı. TNPC/BETA OCR'dan; temiz koordinatlardan hesaplanan referansa göre rakam değişimiyle onarıldı (154 + 103 son basamak), 6 çözülemedi (modelde kullanılmıyor). Tablo II Z: 4 onarım, K15 okunamadı. Kullanıcı kontrolleri tuttu; yalnız s9 en büyük kalınlık 0.42137 (sayfa görüntüsü; koordinat referansı 0.42139), kontroldeki 0.42157 değil; K=20 aynı. A-1 tam geometriyle: tasarım noktası geçti (PR -%1.75, uç Mrel +%1.84); tepe verim beklenen hata (PR -%6.4, η -2.8 puan; choke'un %99'u). Uç duvar blokajı Tablo IV alanlarında zaten var (istasyon 2: %0.3); iki kez uygulanmadı. Kuş sınıfı (analysis/bird_class.py, CS-E 800 Amdt 5, A vekili fan yüzü 1.716 m2 [T]): büyük 2.75 kg, büyük sürü yok, orta 1x1.15+4x0.70 kg, küçük 16x85 g.
- M1 adım 1: `.claude/agents/m1-inlet-fan.md` (Agent aracı yok; ADR-002'ye iç içe subagent cevabı eklendi), `learning/rotor67_reference.yaml` [KS] (Tablo I/II OCR güvenilmez, aktarılmadı; tepe verim OCR belirsiz, PR/TR'den testte kontrol), M1 rule book (index, bom, materials, joints, analyses, failure_modes, bird_strike, aero_method, budget), `tools/data/materials.yaml` (Ti-6Al-4V; Mirghani Ek A PDF'te yok), M1 rev001 (taslak BOM, geometri yok, CR'siz), ders01_fan.md, sources.md #22-38. Test: tests/test_m1_sources.py.
- Geri dönüş koruması: yalnızca yeniden üretilebilir revizyonlara (rev004-rev007); rev001-003 geçmiş kaydı (arayüzde düğme gerekçeyle devre dışı). ICD kaynak kontrolü: bütçeler yalnızca core.budgets.read_icd ile; icd.yaml kaynağı aktif M0 revizyonu değilse ret. CLAUDE.md güncellendi.
- Tam durum geri dönüşü (ADR-013): revert bom, params, results'u kayıttan getirir, icd.yaml'ı yeniden üretir (çözülemezse kaydın çalışma noktasından), güncel kodla doğrular (fark = uyarı). Arayüz geri dönüşü revert CR'si (impact.by M0 revert) ile; konsept geri dönüşü de. Bakımda `moved` için REVIEW.md'de eski -> yeni satırı şart. rev005/006 yeniden çalışabilir (eski w2_ref.tolerance okunur).
- ADR-012 revizyon türleri: tasarım / bakım; core bakım revizyonunu sayısal farkta reddeder, kabul edilmiş modülde CR'siz tasarım revizyonunu reddeder. M0 kabulü: rev005 (records/ACCEPTED). rev001-006 REVIEW.md'de sınıflandırıldı (rev006 bakım).
- Params şeması (core/params.py, params.schema.json): büyüklük girdisi yalnızca value, unit, tag, note, source. cycle_params notları tırnaklandı, W2 toleransı `checks.w2_tolerance` oldu. M0 rev007 = bakım (sayısal fark yok; 0.1 yalnızca taşındı), concept003.
- UI faz 3b: Talepler "Uygula", Revizyonlar "Bu revizyona dön" / "Doğrula", konsept farkından modül farkına geçiş; hepsi onay penceresiyle ve core üzerinden.
- UI görsel düzeltmeler: tam genişlik renkli motor şeridi, metrik etiketleri rozet (değer temiz), küçük sayfa başlıkları, Bilgi sekmesinde küçük başlıklar. engine_reference.svg: şeffaf zemin, currentColor, Türkçe etiketler (label_tr, rules_tr), mil açıklamaları eksen altında, 3/31/44 etiketleri ayrık. Ekran görüntüleri localhost:8501'de açık ve koyu temada alındı (başsız Chrome, DevTools).
- UI faz 3: Talepler (etki kartları, seçenekler, zorunlu not, onay penceresi -> yalnızca decide, decided_by "user (UI)", geçmiş), Revizyonlar (modül/konsept zaman çizelgesi, A->B farkı), Öğrenme (notlar, kaynaklar, etiket açıklaması), Modüller (liste + modül şablonu), şerit/kart tıklama ile gezinme, M0 Bilgi sekmesi. Uygula, geri dönüş ve doğrulama düğmeleri henüz yok.
- M0 rev006 + concept002: results.yaml'a `assumptions` ([T] girdiler) ve kontrollerde `ref_tag`; sayılar rev005 ile aynı (core/diff ile doğrulandı). icd.yaml rev006'dan yeniden üretildi.
- UI faz 2 (salt okunur): ui/app.py (st.navigation), ui/pages/ (6 sayfa), ui/data.py (core üzerinden okuma, mtime anahtarlı önbellek), ui/widgets.py (üst çubuk). Genel bakış ve M0 motor dolu; diğerleri "3. aşamada". core: revision_ids, read_revision, read_concept, list_crs. Çalıştırma: depo kökünden `streamlit run ui/app.py`. Tarayıcıda görsel kontrol yapılmadı (yalnızca AppTest + headless sağlık kontrolü).
- Fusion MCP kullanılabilir: http://127.0.0.1:27182/mcp (HTTP, Fusion eklentisi; yerel kapsamda kayıtlı, commit edilmez). Araçlar: fusion_mcp_read (belge/proje/lisans/API dokümanı/ekran görüntüsü, salt okunur), fusion_mcp_execute (modelde işlem), fusion_mcp_update (model güncelleme), fusion_mcp_electronics_read. Salt okunur test: açık belge listesi -> 0 belge. Fusion MCP için Fusion açık olmalı; ona ihtiyaç duyan testler aksi halde atlanır. Araçlar Claude Code yeniden başlatılınca oturuma yüklenir.
- CR kuralı: impact.by (üretici) kaydedilir; onay için impact.affected_modules boş olmamalı. Önceden doldurulmuş etki yalnızca bütçe CR'lerinde (M0 integration_check); modül CR'leri M0 set_impact bekler.
- UI faz 1: CR `impact.metrics` (isteğe bağlı; bütçe CR'leri dSFC %, dEGT K, dT41 K ile doldurur, onay için etki hazır). core/diff.py: diff_revisions, diff_concepts (saf veri). .cache/geometry/test_box.step üretildi (Fusion ilişkilendirme testi).
- Araç yolları: core/toolpaths.py (ccx 2.22 çalıştı; pdftotext eklendi). UI spesifikasyonu (docs/design/ui_spec.md); ADR-011. Kavramsal düzen: concept_reference.yaml -> tools/reference.py -> engine_reference.svg.
- Araçlar (.venv, Python 3.13): streamlit 1.65.0, cadquery 2.8.0 (OCP 7.9.3.1.1), gmsh 4.15.2; smoke testleri geçti. Harici: PrePoMax 2.6.0 (C:\Tools, ccx 2.22), ParaView 6.2.0, Autodesk Fusion (MCP).
- ADR-010: entegrasyon kontrolü tasarım noktası yeniden dengelemesi; geçici EGT toleransı 5 K [T].
- **M0 v1 tamam.** concept001: M0 rev005, M1-M9 null. Kabul listesi 6/6, kabul testleri 5/5.
- Params CR'leri (apply: params -> yeniden hesap -> revizyon -> results.yaml + icd.yaml); bütçe CR'si seçenekleri (a)/(b).
- M0 ICD ve bütçeler, belirsizlik bandı, ders 02; rev005 benzerlik koşulu (ADR-009), Girão 18/19.

## M0 v1 özeti (rev005 = rev006 = rev007 sayıları) [H]
- W2 345.4 kg/s, W2/A 201.3, FPR 1.765 [KS], HPC PR 10.85, T3 817.5 K, T4 1670.7 K, T41 1629.2 K.
- W31 50.08 kg/s, SFC 10.574, EGT gösterilen 874.9 °C (pay 75 K), ideal V18/V8 0.6036, itki tavanına pay %7.8.
- Belirsizlik bandı: T4 1659-1682 K (Δη'nın hangi gruba uygulandığına göre).
- Verim -0.01 (itki sabit) ΔEGT, model / Martins: fan 3.1/4, booster 1.9/3, HPC 4.3/8, HPT 5.3/12, LPT 5.5/6 K.

## Açık konular
- HPC ve HPT verim kaybının EGT etkisi Martins'in yaklaşık yarısı: sabit geometri yok (ADR-010). M0 v2 ile çözülecek.
- Δη = +0.017 sınanmamış bir varsayım; tolerans ve entegrasyon sınırları [T].
- .step ilişkilendirmesi kullanıcıda bekliyor. Bennett künyesi doğrulanmadı. Indriyati HPC havası tanım farkı.
- M1: motor giriş boğaz alanı (vekil fan yüzü [T]; orta kuş bandı kenarına %0.9) ve 7B27 SAC özel koşul No. 1 metni, Ti-6Al-4V yorulma değeri koşulsuz, OGV sayısı, kasa/spinner/OGV malzemesi: doğrulanmadı. Rotor 67: OCR açı sütunlarında %6 son basamak hatası kaldı (en çok 0.22°; etkisi küçük, duyarlılık bkz. adım 3). M1 fan: RE + kayıplarla A-1 kalıyor (ADR-014 kararı bekliyor; şok payı en büyük, geçit Mach tahmini [T] ayrıca incelenmeli), OGV kaybı yok, kanat sayısı çelişkisi (CFM 1997: 22; NTSB üretim motorları: 24, 1997 makalesi daha erken bir tasarımı anlatıyor olabilir). Kanca ve agent için Claude Code yeniden başlatılmalı.

## Sıradaki adımlar
1. M1 adım 5: ADR-014 kararı (kalibrasyon verisi seçeneği a/b/c); onaylanırsa kalibrasyon betiği, stall yakını kabul; geçerse R-AM.9 ile fan yeniden tasarımı (m1-inlet-fan, rev004).

Yol haritası: M0 v2 off-design modeli (sabit A8, A18, HPT NGV kapasitesi, bileşen haritaları); entegrasyon kontrolü ve seyir noktası bunun üzerine kurulur.

## Çalışma kuralları
- Görev sonu raporu: Commit / Done / Decisions for user / Tests (max 15 satır).
- Kaynak bulunamazsa uydurma; "doğrulanamadı" yaz.
