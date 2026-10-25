# Ders 01: Fan nasıl iş yapar?

Kaynaklar: `rules/aero_method.md` ve `learning/rotor67_reference.yaml`. Etiketler: [KS] ikincil kaynak, [G] genel mühendislik bilgisi.

## 1. Euler iş denklemi
- Rotor, havaya yalnızca teğetsel hızını (girdap, Vt) değiştirerek iş verir [G].
- Birim kütle başına iş: Δh0 = U2·Vt2 − U1·Vt1 [G]. U = ω·r kanat hızıdır.
- Fanın önünde giriş yönlendirici kanat (IGV) yoksa giriş girdabı sıfırdır (Vt1 = 0). Rotor 67 de IGV'siz test edildi [KS]. O zaman iş Δh0 = U2·Vt2 olur.
- Toplam sıcaklık artışı ΔT0 = Δh0 / cp. Basınç oranı bu sıcaklık artışından ve verimden gelir:
  PR = (1 + η·ΔT0/T01)^(γ/(γ−1)) [G].
- Sonuç: aynı girdap için U büyüdükçe iş ve basınç oranı artar.

## 2. Göbekte basınç oranı neden düşük?
- U = ω·r: göbekte yarıçap küçük, kanat hızı düşük [G].
- Aynı işi göbekte vermek için çok daha büyük girdap (Vt2) gerekir; bu da akışı çok fazla döndürmek ve yavaşlatmak demektir [G].
- Kanat yüklemesi difüzyon faktörüyle ölçülür (DF, Lieblein). DF büyüdükçe sınır tabaka kalınlaşır, kayıp artar, ayrılma riski doğar (Abrisha s. 38) [KS].
- Göbekte kanatlar sık dizilir (yüksek katılık) ki yük paylaşılsın. Rotor 67'de katılık göbekte 3.11, uçta 1.29 [KS].
- Bu yüzden tasarımcı göbekte daha düşük basınç oranı kabul eder. CFM56-7B'de iç fan (çekirdeğe giden hava, istasyon 21) ve dış fan (by-pass, istasyon 13) bütçede ayrı basınç oranlarıyla tanımlı (M0 ICD: `pr_fan_inner`, `FPR`) [H].
- Göbek havası zaten booster'a (M2) gider; orada ek basınç kazanılır.

## 3. Süpersonik uç
- Uçta hem kanat hızı hem eksenel hız yüksek; bağıl hız W ses hızını aşar [G].
- Rotor 67: tasarım devrinde uç bağıl Mach sayısı 1.38 [KS]. Büyük turbofan fanları da transonik/süpersonik uçla çalışır [G].
- Süpersonik akışta kanat geçidinde şok dalgası oluşur. Şok, toplam basınçta ani bir kayıp ve entropi artışı demektir (Visentin s. 31) [KS].
- Meanline modelde şok kaybı, normal şok bağıntısıyla ve "geçit Mach sayısı" ile hesaplanır: giriş bağıl Mach ile emme yüzeyindeki tepe Mach'ın ortalaması (Sjögren s. 24) [KS].
- Şokun iyi tarafı: kısa mesafede büyük basınç artışı sağlar. Kötü tarafı: kayıp, sınır tabaka ile etkileşim ve gürültü [G].
- Uç kanat profilleri bu yüzden ince ve az kamburludur; göbek profilleri kalın ve çok kamburludur [G].

## 4. Fan tasarımını ne belirler?
- **Kütle debisi ve itki:** M0 çevrimi W2 ve FPR'yi verir; fan çapı ve göbek/uç oranı bu debiyi geçirecek alanı sağlamalı [G].
- **Uç hızı:** yüksek uç hızı daha fazla iş verir ama şok kaybı, gürültü ve merkezkaç gerilmesi artar. Merkezkaç gerilmesi devrin karesiyle büyür [G].
- **Göbek/uç oranı:** küçük oran daha fazla akış alanı verir ama göbekte yükleme zorlaşır. Rotor 67'de girişte 0.375 [KS].
- **Kanat sayısı ve katılık:** yükleme (DF) ile sürtünme kaybı arasında denge. CFM56-7B'de 24 kanat [KS], Rotor 67'de 22 [KS].
- **Uç boşluğu:** büyük boşluk kaçak akış ve kayıp; küçük boşluk sürtme riski. Rotor 67'de çalışırken yaklaşık 1 mm [KS].
- **Yapısal sınırlar:** kanat kökü (dovetail) en kritik bölge. CFM56-7B'de iki kaza, kırlangıç kuyruğu temas yüzeyinde başlayan düşük çevrimli yorulmadan oldu (Fox 2023) [KS]. Ayrıntı: `rules/failure_modes.md`.
- **Kuş çarpması ve kanat kopması:** kanat kuş çarpmasında kopmamalı, kopan kanadı kasa tutmalı (`rules/bird_strike.md`) [G].
- **Titreşim:** kanat doğal frekansları motor harmoniklerinden uzak olmalı (Campbell diyagramı), flutter olmamalı [G].

## 5. Sonraki adım
- M1 meanline kodu: önce Rotor 67'yi doğrula (`rules/analyses.md` A-1), sonra CFM56-7B fanını bütçeye göre boyutla.
