# AI Turbofan Engine Agent - CFM56-7B27

CFM56-7B27 sınıfı bir turbofan motorun konsept seviyesinde tasarımı için çok agentlı bir sistem.
M0 motor agent'ı, M1-M9 modül agent'larını (fan, booster, kompresör, yanma odası, türbinler, lüle, şaft/yatak, ikincil hava/yağ) koordine eder.
Her modülün tek doğru kaynağı `bom.yaml` dosyasıdır; geometri koddan üretilir.
Modüller arası değişiklikler M0'a değişiklik talebi (CR) olarak gelir ve kullanıcı onayı gerektirir.
Ayrıntılar: [docs/architecture.md](docs/architecture.md)

## Arayüz
Depo kökünden çalıştırın:

```
streamlit run ui/app.py
```

`.venv` etkin olmalı (ya da `.venv\Scripts\streamlit.exe run ui/app.py`). Arayüz şimdilik salt okunur; tasarım: [docs/design/ui_spec.md](docs/design/ui_spec.md).
