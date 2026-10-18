# Arayüz spesifikasyonu (Streamlit)

Kaynak maketler: `ui_genel_bakis.png`, `ui_m0.png`, `ui_modul.png`, `ui_talepler.png` (bu klasörde). Karar: ADR-003 (Streamlit).

## 1. Temel kurallar
- **Arayüz hiçbir dosyaya doğrudan yazmaz.** Bütün yazma işlemleri `core/` üzerinden yapılır: `core.requests` (decide, apply), `core.records` (revert). Her yazma bir onay penceresinden geçer (`ui/widgets.py`: `request` → `confirm_pending`); "Vazgeç" veya pencereyi kapatmak hiçbir şey yazmaz. Sonuç sayfanın üstünde başarı/hata kutusuyla gösterilir. Okuma doğrudan dosyalardan yapılabilir.
- Türetilmiş dosyalar (`results.yaml`, `icd.yaml`, `section.svg`, `engine_reference.svg`) yalnızca gösterilir; düzenleme alanı olmaz.
- Gösterilen her sayının yanında etiketi ([K], [KS], [H], [G], [T]) ve kaynağı (ör. "kaynak rev005") bulunur. Etiketi [T] olan değerler turuncu rozetle vurgulanır.
- Sayılar dosyalardan okunur; arayüz hesap yapmaz. Tek istisna birim dönüşümüdür (ör. kN gösterimi).
- Dil: Türkçe arayüz metinleri; kimlikler (M1.1.1, CR-004, rev005) olduğu gibi kalır.

## 2. Görsel dil (maketlerden)
- Açık ve koyu tema: yalnızca Streamlit bileşenleri ve tema uyumlu renkler; koyu gri zemin, ince kenarlı yuvarlatılmış kartlar.
- Sayfa başlığı küçük (`st.subheader`); üst çubuk sayfa adını da gösterir. Bölüm başlıkları daha küçük (`#####`).
- Metrik kartları: etiket küçük gri rozet olarak başlığın yanında ([T] turuncu); değer etiketsiz ve büyük. 5 karakterden uzun birim başlığa taşınır (ör. "SFC (g/(kN s))").
- Durum renkleri: yeşil = geçti / tamam / aktif; turuncu = bekliyor / [T] / uyarı; kırmızı = kaldı; mavi = bilgi / seçili revizyon; gri = başlamadı.
- Metrik kartlarında küçük başlık ve büyük değer kullanılır (ör. "İtki / 121,4 kN"). Ondalık ayırıcı virgüldür.

## 3. Her sayfada
- **Üst çubuk:** proje adı ("CFM56-7B27 konsept"), aktif konsept (`records/ACTIVE_CONCEPT`, ör. concept001), aktif modül durum rozeti (ör. "M0 · tamam"), bekleyen onay rozeti ("N onay bekliyor": `status: open` olan CR sayısı). Rozete tıklanınca Talepler açılır.
- **Sol menü:** Genel bakış, M0 motor, Modüller, Talepler, Revizyonlar, Öğrenme.

## 4. Sayfalar

### 4.1 Genel bakış (`ui_genel_bakis.png`)
- **Motor şeridi:** M0-M9 kutuları gaz yolu sırasıyla dizilir (`docs/design/concept_reference.yaml`). Renk modül durumunu gösterir: aktif revizyonu olan yeşil, başlamamış (konseptte null) gri, açık CR'si olan (veya aktif revizyonu konseptten farklı olan) turuncu. Kutu bir düğmedir: M0 → M0 motor sayfası, M1-M9 → modül sayfası (`pages/moduller.py?m=Mx`). Şerit tam genişlikte, eşit genişlikli renkli dilimlerden oluşur; etiketler (M0..M9) dilimin içindedir; altında renk açıklaması.
- **Metrik kartları:** itki, SFC, EGT payı, W2. Kaynak: aktif M0 revizyonunun `results.yaml` dosyası (`performance.thrust`, `performance.sfc`, EGT sınır kontrolünün `margin` değeri, `calibration.W2`).
- **Modül kartları:** her modül için ad ve durum ("Başlamadı · sıradaki", "revNNN aktif"); "Aç" düğmesi modül sayfasını açar.
- **Son revizyonlar:** M0'ın revizyon zinciri (`parent_revision` ile), aktif olan mavi.
- Ek (maketin dışında): kavramsal düzen referansı `engine_reference.svg` katlanabilir bir panelde satır içi SVG olarak gösterilir (şeffaf zemin, nötr çizgi ve yazılar `currentColor` ile temaya uyar, Türkçe etiketler; `tools/reference.py` ile `concept_reference.yaml`'dan üretilir).

### 4.2 M0 motor (`ui_m0.png`)
- **Başlık:** aktif revizyon rozeti, doğrulama özeti ("Girão 18/19", kaynak `analysis/validation_girao.md`), "Revizyonları karşılaştır" düğmesi (Revizyonlar sayfasındaki fark görünümüne gider).
- **İstasyon tablosu:** istasyon, sahip modül, Tt, Pt, W, FAR. Kaynak `rules/icd.yaml` (`stations`). Altında not: "Her değerin yanında etiket: H · kaynak revNNN". Kısaltılmış görünümde ana istasyonlar, genişletince hepsi gösterilir.
- **Kontroller:** `results.yaml` içindeki `checks`. Her satırda ad, değer ve rozet (geçti / kaldı / bilgi). HARD kontroller "(sert)" etiketi taşır. Değerin altında referans ve referansın etiketi (`ref_tag`) gösterilir (ör. "ref 950 [K]"; birden çok referansta "[KS/T]").
- **Varsayımlar [T]:** `results.yaml` → `assumptions` (sonucun dayandığı [T] params girdileri; kontrol referansları ve çözücü başlangıç değerleri hariç). Her satır turuncu T rozeti, yol, değer ve not (ipucu). Δη çözülen bir değerdir [H]; dayandığı benzerlik koşulu `rated_case.similarity` [T] olarak listelenir.
- **Modül bütçeleri (ICD):** her modül için kart: ana bütçe kalemleri ve izin verilen sapmalar (`icd.yaml` → `modules.<Mx>.budget`, `tolerances`). Kart tıklanınca tüm kalemler listelenir.
- **Bilgi sekmesi:** belirsizlik bandı (`rules/cycle_inputs.md` → "Belirsizlik bandı" bölümü), verim duyarlılığı ve Martins karşılaştırması (`analysis/acceptance_M0.md` → "Makullük" bölümü), ADR-010 sınır notu (uyarı kutusu + tam metin). Arayüz bu tabloları hesaplamaz, belgelerden gösterir.

### 4.3 Modül sayfası, M1-M9 (`ui_modul.png`)
- **Başlık:** modül adı; "Karşılaştır: [rev A] → [rev B]" seçicileri (varsayılan: önceki → aktif); düğmeler: Kesit, 3B, Fusion'da aç.
- **BOM ağacı (solda):** `bom/bom.yaml` parçaları, kimliğe göre hiyerarşik (M1.1 → M1.1.1); tekrar eden parçada "×qty". Seçilen parça kesitte vurgulanır.
- **Kesit görünümü:** iki revizyonun `records/revNNN/section.svg` dosyaları üst üste çizilir (ADR-011). Eski revizyon kesikli gri, yeni revizyon renkli. Değişen ölçüler için ok ve etiket gösterilir (ör. "Δr uç = +13 mm"). Motor ekseni kesikli çizgiyle gösterilir.
- **3B görünüm:** GLB dosyası yerel önbellekten (`.cache/geometry/<modül>/<rev>/`) okunur. Önbellekte yoksa kayıttaki `code_commit` ve parametrelerle yeniden üretilir, SHA-256 kayıtla karşılaştırılır.
- **Değişen ölçüler:** A ile B arasındaki parametre ve BOM farkı (`core.diff.diff_revisions`); ad, eski → yeni, fark (ör. "Fan çapı 1549 → 1575 mm").
- **Analizler:** seçili revizyonun analiz kontrolleri (ör. santrifüj gerilme, uç hızı, Campbell), her biri rozetle.
- **Fusion'da aç:** STEP dosyası önbelleğe dışa aktarılır ve işletim sisteminin dosya ilişkilendirmesiyle açılır (Windows'ta `os.startfile`). İlişkilendirme yoksa arayüz dosya yolunu gösterir ve uyarı verir. Fusion'da yapılan değişiklikler geri yazılmaz; tek kaynak koddur.
- Başlamamış modülde sayfa, ICD bütçesini ve "Başlamadı" durumunu gösterir.
- **Faz 3 durumu (şablon):** başlık, durum rozeti, A/B revizyon seçicileri, BOM ağacı (`bom.yaml`, şimdilik boş), kesit yer tutucusu, ICD bütçe tablosu. Kesit, 3B ve Fusion'da aç düğmeleri devre dışı; değişen ölçüler ve analizler henüz yok.

### 4.4 Talepler (`ui_talepler.png`)
- Başlıkta açık ve kapalı CR sayıları. Liste `engine/M0_engine/requests/CR-*.yaml` dosyalarından okunur; açık CR'ler önce gelir.
- **CR kartı:** kimlik, yön ("M3 → M0"), tür ("bütçe ihlali"), gerekçe, etki rozeti ("etki analizi hazır" = `impact` dolu ve `affected_modules` boş değil), yanında üretici (`impact.by`, ör. "M0 integration_check").
- **Etki metrikleri:** ΔSFC, ΔEGT, ΔT41 kartları. Kaynak: CR'nin `impact.metrics` alanı (metrik adı → {value, unit, tag}); bütçe CR'lerinde `dSFC` [%], `dEGT` [K], `dT41` [K], operating_point modunda ayrıca `dThrust` [%]. Alan isteğe bağlıdır: `impact` boş ya da `metrics` yoksa kartlar gösterilmez, yalnızca `impact.notes` görünür.
- **Seçenekler:** CR'deki `options` radyo düğmeleriyle gösterilir: (a) M0 değeri kabul etsin ve çevrimi yeniden dengelesin; (b) modül tasarımını düzeltsin.
- **Karar notu:** zorunlu metin alanı.
- **Karar:** "Kararı kaydet" bir onay penceresi (`st.dialog`) açar: CR, onay/ret, seçenek ve not gösterilir. "Kaydet" yalnızca `core.requests.decide(cr, approve, note, option=..., decided_by="user (UI)")` çağırır; "Vazgeç" veya pencereyi kapatmak hiçbir şey yazmaz. Not boşsa düğme devre dışıdır (`decide` de boş notu reddeder). Kararda `decision.decided_by` kaydedilir.
  - Maketten farkı: (b) bir ret kararıdır, (a) onaydır. Bu yüzden "Onayla / Reddet" yerine tek bir **"Kararı kaydet"** düğmesi olur; onay mı ret mi olduğu seçilen seçenekten çıkar. Seçeneği olmayan CR'lerde Onayla ve Reddet düğmeleri kalır.
  - Etki analizi yoksa veya `impact.affected_modules` boşsa onay seçeneği devre dışıdır (`core.requests` zaten reddeder).
- **Uygulama:** onaylanmış CR'de "Uygula" düğmesi onay penceresini açar; onayda `core.requests.apply` çağrılır. Oluşan revizyonlar (her biri ADR-012 tasarım revizyonu, CR bağlantılı) başarı mesajında gösterilir.
- Kapalı CR'ler karar (tarih, seçenek, not, `decided_by`) ve uygulanan revizyonlarla salt okunur listelenir. Her CR'de geçmiş (`history`) tablosu katlanabilir panelde.

### 4.5 Revizyonlar
- **Modül zaman çizelgesi:** her revizyon bir satır (`records/revNNN/manifest.yaml`): kimlik rozeti (aktif mavi), özet, tarih, revizyon türü (ADR-012: tasarım / bakım; eski kayıtlarda "REVIEW.md"), CR, kod commit'i, gerekçe. Satırda "Bu revizyona dön" (aktif olanda devre dışı) ve "Doğrula" düğmeleri.
- **Konsept zaman çizelgesi:** `conceptNNN` manifestleri ve sabitlenen modül revizyonları.
- **Fark görünümü:** `core.diff.diff_revisions(modül, revA, revB)` sonucundan:
  - `params`: [{path, old, new}] (None = yok; eklenen/silinen anahtar),
  - `results`: [{key, old, new, delta, pct}] (delta ve yüzde yalnızca iki değer de sayıysa),
  - `bom`: {header, added, removed, changed: {parça kimliği: [{path, old, new}]}},
  - `outputs`: [{file, old, new}] (SHA-256 değişimi).
  Yollar noktalıdır (ör. `calibration.W2.value`); kimlik anahtarı olan listeler kimlikle yazılır (ör. `stations[2].W_kg_s`). Boş fark `core.diff.is_empty` ile anlaşılır. Biçimlendirme (ondalık virgül, birim) arayüzün işidir.
- **Konsept farkı:** `core.diff.diff_concepts(cA, cB)` → [{module, old, new}] satırları; "Modül farkını göster" o modülü ve A/B revizyonlarını fark görünümüne yükler (iki taraf da varsa).
- Fark sekmeleri: Parametreler, Sonuçlar (fark ve %), BOM (eklenen/silinen/değişen), Çıktılar (sha256). Varsayılan B = aktif revizyon, A = bir önceki.
- **Geri dönüş:** "Bu revizyona dön" onay penceresinden sonra `core.records.revert` çağırır. Yalnızca `records/ACTIVE` ve `bom.yaml` değişir; kayıtlar silinmez. Analiz dosyaları (params, results.yaml, icd.yaml) ve aktif konsept değişmez; pencere bunu yazar. Konsept geri dönüşü (`revert_concept`) henüz yok.
- **Doğrulama:** "Doğrula" onay penceresinden sonra `core.records.verify` çalışır (yalnızca okuma); sonuç başarı veya hata kutusunda (uyuşmayan dosyalar listelenir).

### 4.6 Öğrenme
- `docs/learning/` ve `engine/*/learning/` altındaki `.md` dosyaları markdown olarak gösterilir; `.txt` dosyaları (ör. parça bilgi dokümanı) sabit genişlikli metin olarak gösterilir.
- Solda modüle göre gruplanmış dosya listesi bulunur. `learning/sources/` (indirilen kaynaklar, git dışı) listelenmez.
- **Kaynaklar sekmesi:** `docs/sources.md` tablosu (kaynak, kullanım, lisans).
- **Etiketler sekmesi:** K, KS, H, G, T açıklamaları; T turuncu rozetli.

## 5. Uygulama notları
- Streamlit çok sayfalı uygulama: `ui/app.py` ve `ui/pages/`. Kurulu sürüm `pyproject.toml` içinde sabitlenir.
- Okuma katmanı (`ui/data.py`) yalnızca okur ve önbelleğe alır (`st.cache_data`; ACTIVE işaretçileri, bom.yaml, CR dosyaları ve icd.yaml değişiklik zamanı anahtarlı, bir yazmadan sonraki çalıştırmada kendiliğinden yenilenir). Yazma düğmeleri yalnızca `core` fonksiyonlarını çağırır.
- Depo kökü `TURBOFAN_UI_ROOT` ortam değişkeniyle değiştirilebilir (testler geçici kopya kullanır; gerçek depoya yazılmaz). `docs/` her zaman gerçek kökten okunur.
- Ortak parçalar `ui/widgets.py` içinde (üst çubuk, rozetler, modül sayfasına geçiş).
- 3B görünüm için GLB görüntüleyici olarak tarayıcıda çalışan bir bileşen (ör. model-viewer) kullanılabilir. Eklenecek bağımlılık için önce onay alınır.

## 6. Açık noktalar
1. ~~Etki metrikleri CR'de yapısal değil~~ — çözüldü (UI faz 1): `impact.metrics`, bütçe CR'lerinde `integration_check` doldurur.
2. **`.step` dosya ilişkilendirmesi:** bu makinede `.step` ve `.stp` uzantıları hiçbir uygulamayla ilişkili değil. "Fusion'da aç" çalışması için ya ilişkilendirme yapılmalı ya da Fusion'ın çalıştırılabilir dosya yolu ayarlardan verilmeli.
3. ~~Revizyon farkı fonksiyonu~~ — çözüldü (UI faz 1): `core/diff.py` (`diff_revisions`, `diff_concepts`).
