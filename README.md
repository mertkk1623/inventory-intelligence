# Inventory Intelligence

A single-SKU inventory and material planning workspace built with Python and
Streamlit. It reads a structured Excel workbook, validates it, calculates stock
and replenishment metrics, explains them across six analytics screens, and
exports the result as an Excel workbook or a PDF report. An optional AI layer
adds narrative interpretation on top of the deterministic engine.

> **Version:** Inventory Intelligence V1
> **Status:** Development Complete — Pre-Release (local demo build)
>
> V1 scope is complete. The application runs locally; it is not deployed to a
> public environment and is not published as a live product. Roadmap items for
> V2 and later are planned enhancements and are not currently available.

**Languages:** English (default) · Türkçe — switchable in the sidebar.

---

## Contents

1. [Overview](#1-overview)
2. [Key Features](#2-key-features)
3. [How It Works](#3-how-it-works)
4. [Screens](#4-screens)
5. [Excel Data Structure](#5-excel-data-structure)
6. [Demo Data](#6-demo-data)
7. [AI Layer](#7-ai-layer)
8. [Reports](#8-reports)
9. [Tech Stack](#9-tech-stack)
10. [Installation](#10-installation)
11. [Configuration](#11-configuration)
12. [Usage](#12-usage)
13. [Roadmap](#13-roadmap)
14. [Limitations](#14-limitations)
15. [Current Status](#15-current-status)

---

## 1. Overview

Inventory Intelligence turns one Excel workbook into a decision workspace for a
single stock-keeping unit. Instead of rebuilding stock maths in a spreadsheet,
you upload the workbook once and the application derives the whole picture from
it: how much stock you hold, how fast it is consumed, when you need to order,
and how much.

The design principle is a strict separation between calculation and
interpretation:

- **The engine owns every number.** Current stock, consumption, thresholds and
  order suggestions are computed by a framework-independent Python layer that
  has no UI imports. The same result object drives every screen, chart, table
  and report.
- **The interface only presents.** No screen recalculates a metric.
- **The AI layer only explains.** When enabled, the model receives the engine
  values and writes prose about them. It cannot change a value.

V1 is deliberately narrow: one product, one warehouse, one workbook. That
constraint keeps the calculation auditable and the scope honest.

---

## 2. Key Features

- **Structured Excel contract.** Three required sheets with fixed names and
  columns, validated before anything is calculated.
- **Row-level validation feedback.** Every problem is reported with a code, a
  severity and a plain-language message in the selected language.
- **Deterministic calculation engine.** Current stock, rolling average daily
  consumption, days of supply, reorder point, target stock, inventory position
  and suggested order quantity.
- **Seven screens.** Getting Started, Overview Dashboard, Stock Analysis,
  Consumption Analysis, Replenishment Planning, Reports and AI Analyst.
- **Interactive charts.** Stock balance trend, daily and weekly consumption, and
  a safety-stock-versus-reorder-point comparison.
- **Excel and PDF reporting.** A five-sheet workbook and a seven-section A4 PDF,
  both generated from the same calculation result.
- **Optional AI interpretation.** Inventory insights, consumption insights, a
  replenishment explanation and free-form questions — cached per dataset and
  report date.
- **Bilingual interface.** Complete English and Turkish UI with locale-aware
  number and date formatting.
- **Demo and upload isolation.** Demo data and your own uploads never coexist in
  the same workspace.
- **Historical report handling.** Pick a past report date and the screen explains
  which planning values are intentionally unavailable instead of guessing.
- **No silent failures.** A missing API key, an unreachable provider or a
  truncated response produces a visible message; deterministic values stay
  intact.

---

## 3. How It Works

The workflow has eight steps, and the same eight steps are shown on the Getting
Started screen.

1. **Download Excel Template** — start from the workbook that already contains
   the required sheets and columns.
2. **Enter Product and Stock Data** — add your SKU, opening stock, safety stock
   and planning parameters.
3. **Upload Excel File** — every sheet is validated before the file becomes
   active.
4. **Review Inventory Dashboard** — check current stock, days of supply, the
   reorder point and the suggested order quantity.
5. **Analyze Consumption** — inspect daily and weekly OUT consumption, including
   days with no movement.
6. **Review Replenishment Recommendations** — compare inventory position with the
   reorder point and review open purchase orders.
7. **Ask AI Analyst** — optionally ask for a plain-language explanation (requires
   an API key).
8. **Export Excel or PDF Reports** — download a formatted workbook or a
   presentation-ready PDF for the selected report date.

### Calculation model

All formulas use the validated workbook and the report date selected in the
sidebar.

| Metric | Formula |
| --- | --- |
| Current Stock | Opening Stock + IN movements − OUT movements, up to the report date |
| Average Daily Consumption | OUT quantity in the consumption window ÷ calendar days in that window |
| Days of Supply | Current Stock ÷ Average Daily Consumption (`—` when consumption is zero) |
| Reorder Point | Average Daily Consumption × Lead Time Days + Safety Stock |
| Target Stock | Average Daily Consumption × (Lead Time Days + Target Coverage Days) + Safety Stock |
| Inventory Position | Current Stock + all open order quantities |
| Reorder Required | Inventory Position ≤ Reorder Point (inclusive) |
| Suggested Order Quantity | `0` when no reorder is required; otherwise ceil(Target Stock − Inventory Position) |

The consumption window is a rolling **30 calendar days**, clamped to the range
between the Opening Stock Date and the report date. Days without OUT movements
count as zero consumption rather than being skipped.

### A worked example

Using the bundled demo workbook with a report date of 13 November 2026:

| Value | Result |
| --- | --- |
| Current Stock | 449 Adet |
| Average Daily Consumption | 9.37 Adet/day |
| Days of Supply | 47.9 days |
| Reorder Point | 212.4 Adet |
| Target Stock | 399.7 Adet |
| Open Order Quantity | 300 Adet |
| Inventory Position | 749 Adet |
| Suggested Order Quantity | 0 Adet |

Inventory Position (749) is above the Reorder Point (212.4), so no reorder is
required and the suggestion is zero. These numbers are reproducible from the
bundled file; they are not hard-coded.

---

## 4. Screens

The sidebar holds the language switch, the workspace navigation, the shared
report date, the active-dataset card and a "Clear workspace" button. The report
date is global: changing it recalculates every screen and both reports.

| Screen | Purpose |
| --- | --- |
| **Getting Started** | Product front door: hero, the eight-step workflow, the Excel contract, the synthetic demo disclosure, the data-privacy statement, the roadmap and the version/status card. Also the place to download the template, load the demo or upload a workbook. |
| **Overview Dashboard** | The summary screen. Four KPI cards (current stock, average daily consumption, days of supply, suggested order), a stock level trend, a safety-stock-versus-reorder-point comparison, a daily consumption chart, a stock status table and the open purchase order table. |
| **Stock Analysis** | Opening and current stock with total IN and OUT, a filterable movement history (date range and transaction type) and a balance trend chart that always reflects both directions. |
| **Consumption Analysis** | Average daily consumption, total consumption, highest and lowest consumption day, a daily line chart, a weekly bar chart and an expandable table of daily values. Days without movements remain visible as zero. |
| **Replenishment Planning** | Reorder point, safety stock, lead time, current stock, open order quantity, inventory position, target stock, suggested order quantity, reorder status, overdue orders, an explanation of how Inventory Position is built and the open-order table. |
| **Reports** | Descriptions of both output formats, the report context strip and the two download buttons. |
| **AI Analyst** | The deterministic supporting data panel, then the optional AI sections: inventory overview, key findings, inventory risks, recommended actions, consumption insights, replenishment explanation and a natural-language question box. |

Warnings are always visible rather than hidden: negative stock, a historical
report date, a missing API key and a failed AI request each render a banner
while the deterministic values remain on screen.

---

## 5. Excel Data Structure

The workbook must contain exactly these three sheets. Sheet names and column
names are part of the contract and must not be renamed. Additional columns are
preserved but not used.

### Product Master — one row

| Column | Type | Rules |
| --- | --- | --- |
| `Product Code` | text | Required, unique. Exactly one product row. |
| `Product Name` | text | Required. |
| `Unit` | text | Required (for example `Adet`, `pcs`, `kg`). |
| `Opening Stock` | whole number | Zero or greater. |
| `Opening Stock Date` | date | Required; no movement may be dated before it. |
| `Safety Stock` | whole number | Zero or greater. |
| `Lead Time Days` | whole number | Zero or greater. |
| `Target Coverage Days` | whole number | One or greater. |

### Stock Movements — one row per movement

| Column | Type | Rules |
| --- | --- | --- |
| `Date` | date | Valid Excel date, on or after the Opening Stock Date. |
| `Transaction Type` | text | `IN` or `OUT`. |
| `Quantity` | whole number | Positive integer. |
| `Description` | text | Optional. |

### Open Orders — one row per purchase order

| Column | Type | Rules |
| --- | --- | --- |
| `Order No` | text | Required, unique. |
| `Order Quantity` | whole number | Positive integer. |
| `Expected Delivery Date` | date | Valid Excel date. |

Supported date formats: `YYYY-MM-DD`, `DD.MM.YYYY`, `DD/MM/YYYY`,
`YYYY/MM/DD`, `DD-MM-YYYY`.

The validator reports, among other checks: missing sheets, missing columns,
duplicate product codes, duplicate order numbers, invalid transaction types,
non-integer or negative quantities, invalid dates, and movements dated before
the opening stock date. A file that fails validation never becomes the active
dataset.

### The template

`templates/inventory-intelligence-template.xlsx` contains the three sheets with
the exact columns above and an empty product row. The Welcome screen offers it
as a download. Uploading the untouched template is correctly rejected with an
`empty_product_master` error rather than producing a misleading empty dashboard.

---

## 6. Demo Data

`templates/inventory-intelligence-demo.xlsx` is a **synthetic** workbook
generated for demonstration only. It is not real company data.

- One product: `PRF-4040-02` — "Galvanizli Kare Profil 40x40x2 mm - 6m",
  unit `Adet`.
- 18 stock movements and 2 open purchase orders.
- Opening stock 500 Adet on 1 October 2026.

**Demo and uploads never mix.** Loading the demo replaces any active upload, and
uploading a file replaces the demo. The sidebar always states which dataset is
active.

The demo is useful for a portfolio walkthrough because it exercises the real
path: it is read from a real `.xlsx` file and pushed through the same validation
and calculation code as an uploaded workbook.

---

## 7. AI Layer

The AI layer is **optional and off unless configured**. It is a thin, bounded
client, not an autonomous planner.

### What it does

- **AI Inventory Overview** — narrative findings, risks and suggested actions
  derived from the engine values.
- **Consumption Insights** — a summary of the consumption window, peak/lowest
  day notes, zero-consumption notes and observed patterns.
- **Replenishment Explanation** — why a reorder is or is not required, with
  supporting data and caveats.
- **Natural-language questions** — ask about the active dataset; six suggested
  questions are offered as buttons.

### What it cannot do

- It cannot change a calculation. Every number in the supporting-data panel comes
  from `InventoryCalculation`.
- It cannot run on its own. A request is sent only when you press an AI button.
- It cannot produce a purchase order, a multi-SKU plan or a forecast. Those are
  out of V1 scope.
- It cannot silently fail. A provider error or a truncated response shows a
  banner and leaves the deterministic values untouched.

### How requests are controlled

- Responses are validated against strict schemas with length caps; lists are
  capped at 15 items and text fields at 1,200 characters.
- Every successful result is cached by a context fingerprint plus operation, so
  a rerun never repeats a request and the same question is never billed twice.
  Failures are never cached.
- A response that hits the token ceiling (`finish_reason == "length"`) is
  rejected as truncated rather than shown as complete.
- Open orders are never folded into current stock anywhere in the pipeline, and
  the AI is told so.

### Language

The **interface** is fully translated. The **model output is English**: the
prompt requests English prose and answers are rendered verbatim. The AI Analyst
screen states this so a Turkish interface is never surprising.

---

## 8. Reports

Two outputs are produced from the same `ReportContext`, so the downloaded files
always agree with the dashboard.

### Excel report — five sheets

1. `Executive Summary` — product, stock, consumption and replenishment values on
   one page.
2. `Stock Movements` — every IN and OUT movement in range with its closing
   balance.
3. `Consumption Analysis` — average, total, highest and lowest day plus the daily
   and weekly series.
4. `Replenishment Plan` — planning thresholds, inventory position and the
   suggested order.
5. `Open Purchase Orders` — order quantity, expected delivery date and overdue
   status.

### PDF report — seven sections

Report header, executive summary, stock analysis, consumption analysis,
replenishment planning, open purchase orders, and methodology and notes.

The PDF is A4 portrait with numbered pages, charts drawn from the same series as
the dashboard, and an embedded TrueType font so Turkish characters render
correctly.

### Report language scope

**Excel and PDF files are generated in English**, regardless of the interface
language. Dashboard values, charts and the interface follow the selected
language; the report files do not. The Reports screen states this explicitly so
the scope is never ambiguous. Sheet and section names are kept in English on
screen so they match the file you download.

Reports are static snapshots of the current calculation. They contain no
formulas.

---

## 9. Tech Stack

| Layer | Choice |
| --- | --- |
| Language | Python 3.11+ (verified on 3.11, 3.12 and 3.13) |
| UI | Streamlit (verified on 1.53 and 1.67) |
| Data | pandas, openpyxl |
| Charts | Plotly |
| PDF | ReportLab |
| AI validation | Pydantic v2 |
| AI transport | Python standard library `urllib` only |
| Tests | pytest with Streamlit's `AppTest` |
| Lint | Ruff |
| CI | GitHub Actions, Python 3.11/3.12/3.13 matrix |

The AI client deliberately has no vendor SDK dependency: one small
OpenAI-compatible `chat/completions` caller keeps the dependency surface and the
review surface small.

### Project layout

```text
inventory-intelligence/
├── app.py                    Streamlit entry point and page routing
├── config.py                 Paths, app metadata, upload limits
├── pyproject.toml            Ruff and pytest configuration
├── requirements.txt          Runtime dependencies
├── requirements-dev.txt      Runtime + pytest + Ruff
├── .streamlit/config.toml    Theme and upload configuration
├── .github/workflows/ci.yml  Lint and test matrix
├── core/                     Framework-independent domain layer
│   ├── schema.py             Canonical Excel sheet/column contract
│   ├── models.py             Domain models and the calculation result
│   ├── excel_reader.py       Workbook reader
│   ├── validation.py         Validation engine and issue reporting
│   ├── inventory.py          Current stock and balance history
│   ├── consumption.py        Rolling average daily consumption
│   ├── replenishment.py      Reorder point, target stock, order suggestion
│   └── calculations.py       Composes the single InventoryCalculation
├── analytics/series.py       Display series derived from the result
├── ai/                       Optional AI layer (client, prompts, schemas, cache)
├── reports/                  Excel and PDF builders plus PDF theme/charts
├── components/               Screens, charts, sidebar, styles, UI helpers
├── utils/                    i18n, session state, data loading, calculation cache
├── templates/                Excel template and synthetic demo workbook
└── tests/                    pytest suite
```

The `core/` package never imports Streamlit. That boundary is what makes the
engine testable without a browser and keeps the screens as presentation only.

---

## 10. Installation

Requirements: **Python 3.11 or newer**.

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

For development, including the test suite and the linter:

```bash
pip install -r requirements-dev.txt
```

### Run the application

```bash
streamlit run app.py
```

If `streamlit` is not on your PATH:

```bash
python -m streamlit run app.py
```

The app opens at `http://localhost:8501`.

### Run the tests

```bash
python -m pytest -q
```

### Lint

```bash
python -m ruff check .
```

---

## 11. Configuration

### Upload limits

`.streamlit/config.toml` sets the theme and the 10 MB upload limit; `config.py`
holds `MAX_UPLOAD_SIZE_MB` and the allowed extension (`.xlsx` only).

### AI provider

The AI layer reads its configuration from, in order of precedence:

1. `.streamlit/secrets.toml` (never committed),
2. environment variables,
3. built-in defaults.

```toml
# .streamlit/secrets.toml  — never commit this file
AI_API_KEY = "your-key-here"
```

The accepted key names are `AI_API_KEY` and `DEPLOY_API_KEY`. Optional
overrides: `AI_BASE_URL` and `AI_MODEL`.

Defaults:

| Setting | Value |
| --- | --- |
| Base URL | `https://api-cdn.deploy.com/api/v1` |
| Endpoint | `POST /chat/completions` |
| Auth | `Authorization: Bearer <key>` |
| Model | `deepseek-ai/deepseek-v4.1-flash-1017` |
| `max_tokens` | 4000 (a 3000 floor is enforced as the minimum useful budget) |
| `temperature` | 0.2 |
| Timeout | 60 s |
| Retries | 2, on 429/500/502/503/504 only |

**Without a key the application is fully usable**: every deterministic screen and
both reports work, and the AI Analyst screen explains that AI is unavailable.

### Secrets

`.gitignore` excludes `.streamlit/secrets.toml`, `.env`, `.env.*`, `*.pem` and
`*.key`. The API key is never logged and never rendered. Do not commit a key.

---

## 12. Usage

1. Open the app. The Getting Started screen loads in English.
2. Optionally switch the language to **Türkçe** in the sidebar. The switch
   applies immediately, keeps you on the current screen and persists for the
   session.
3. Choose one path:
   - **Download Template** and fill in your own workbook, or
   - **Load Demo Data** to explore with the synthetic dataset, or
   - **Upload Your Excel** to validate and activate a real file.
4. Set the **report date** in the sidebar. Every screen and both reports follow
   it.
5. Walk the screens: Overview → Stock Analysis → Consumption Analysis →
   Replenishment Planning.
6. Optionally open **AI Analyst**. With no key configured you will see the
   deterministic data and an "AI unavailable" notice. With a key, press a
   generate button to spend one request; the result is cached.
7. Open **Reports** to download the Excel workbook and the PDF.
8. Use **Clear workspace** to remove the active dataset and start again.

Everything is held in the browser session. A full page reload returns the
application to its default state, which is the documented behaviour for V1.

---

## 13. Roadmap

### Completed — V1

| Package | Scope |
| --- | --- |
| Package 1 | Foundation: shell, Excel contract, validation engine, Welcome screen |
| Package 2 | Inventory Calculation Engine |
| Package 3 | Analytics and Dashboard |
| Package 4 | Excel and PDF Reporting |
| Package 5 | AI Intelligence Layer |

V1 is feature-complete and development is finished. It is a local, pre-release
build.

### Planned — future versions

| Version | Scope | Status |
| --- | --- | --- |
| V2 | ABC Analysis and Demand Forecasting | Planned |
| V3 | Stock Optimization | Planned |
| V4 | Multi-SKU and Multi-Warehouse Support | Planned |
| V5 | ERP Integration and Advanced Automation | Planned |

The current V1 scope is complete. Future roadmap items are planned enhancements
and are not currently available.

No dates are attached to the planned items, and nothing in this section is
implemented in the current build.

---

## 14. Limitations

These are intentional V1 boundaries, not defects.

- **Single SKU, single warehouse.** One product row per workbook.
- **No forecasting.** Consumption is measured historically; it is not projected.
- **No ABC analysis, no stock optimisation.** Both are V2/V3 scope.
- **No ERP or accounting integration.** The workbook is the only input.
- **Historical report dates do not produce order suggestions.** Current open
  orders describe today's supply, not the supply that existed on a past date, so
  they are excluded from Inventory Position and the suggestion is suppressed
  with an explanation.
- **Excel and PDF reports are English-only.** The interface and dashboards are
  bilingual; the report files are not.
- **AI output is English-only** and depends on an external provider.
- **Session-only state.** A full page reload clears the workspace.
- **No authentication.** V1 is a local single-user tool and ships no login.
- **The AI layer is decision support.** It is not automated planning and every
  output requires human review.
- **A historical consumption window can be short.** If the workbook covers fewer
  than 30 days, the average is computed over the days that exist.

---

## 15. Current Status

| Item | Value |
| --- | --- |
| Product | Inventory Intelligence V1 |
| Version | 1.0.0 |
| Status | Development Complete — Pre-Release |
| Build | Local demo |
| Completed packages | 5 / 5 |
| Screens | 7 |
| Interface languages | English · Türkçe |
| Automated tests | 190 |
| Verified Python | 3.11, 3.12, 3.13 |
| Verified Streamlit | 1.53, 1.67 |
| Lint | Ruff, clean |

What this means:

- The V1 feature set is implemented and the automated suite passes on every
  supported Python version and on both verified Streamlit releases.
- The application is intended to run **locally**. It is not deployed to a public
  environment, has no public URL and is not published as a live product.
- The demo dataset is synthetic and is clearly labelled as such in the interface.
- Known limitations are listed in [section 14](#14-limitations) and are stated in
  the interface where they matter.

---

## Türkçe

# Inventory Intelligence

Python ve Streamlit ile geliştirilmiş, tek SKU'lu stok ve malzeme planlama
çalışma alanı. Yapılandırılmış bir Excel çalışma kitabını okur, doğrular, stok ve
ikmal metriklerini hesaplar, altı analiz ekranında açıklar ve sonucu Excel
çalışma kitabı ya da PDF raporu olarak dışa aktarır. İsteğe bağlı AI katmanı,
deterministik motorun üzerine anlatı yorumu ekler.

> **Sürüm:** Inventory Intelligence V1
> **Durum:** Geliştirme Tamamlandı — Yayın Öncesi (yerel demo sürümü)
>
> V1 kapsamı tamamlanmıştır. Uygulama yerel olarak çalışır; herkese açık bir
> ortama dağıtılmamıştır ve canlı bir ürün olarak yayımlanmamıştır. V2 ve
> sonrasına ait yol haritası maddeleri planlanan geliştirmelerdir ve şu anda
> kullanıma açık değildir.

**Diller:** İngilizce (varsayılan) · Türkçe — kenar çubuğundan değiştirilebilir.

---

## İçindekiler

1. [Genel Bakış](#1-genel-bakış)
2. [Öne Çıkan Özellikler](#2-öne-çıkan-özellikler)
3. [Nasıl Çalışır](#3-nasıl-çalışır)
4. [Ekranlar](#4-ekranlar)
5. [Excel Veri Yapısı](#5-excel-veri-yapısı)
6. [Demo Verisi](#6-demo-verisi)
7. [AI Katmanı](#7-ai-katmanı)
8. [Raporlar](#8-raporlar)
9. [Teknoloji Yığını](#9-teknoloji-yığını)
10. [Kurulum](#10-kurulum)
11. [Yapılandırma](#11-yapılandırma)
12. [Kullanım](#12-kullanım)
13. [Yol Haritası](#13-yol-haritası)
14. [Sınırlamalar](#14-sınırlamalar)
15. [Mevcut Durum](#15-mevcut-durum)

---

## 1. Genel Bakış

Inventory Intelligence, tek bir stok kalemi için bir Excel çalışma kitabını
karar çalışma alanına dönüştürür. Stok matematiğini elektronik tabloda yeniden
kurmak yerine çalışma kitabını bir kez yüklersiniz ve uygulama tüm resmi ondan
türetir: ne kadar stok tuttuğunuz, ne hızda tüketildiği, ne zaman sipariş
vermeniz gerektiği ve ne kadar.

Tasarım ilkesi, hesaplama ile yorum arasında kesin bir ayrımdır:

- **Her sayının sahibi motordur.** Mevcut stok, tüketim, eşikler ve sipariş
  önerileri, arayüz içe aktarımı yapmayan ve çerçeveden bağımsız bir Python
  katmanında hesaplanır. Aynı sonuç nesnesi her ekranı, grafiği, tabloyu ve
  raporu besler.
- **Arayüz yalnızca sunar.** Hiçbir ekran bir metriği yeniden hesaplamaz.
- **AI katmanı yalnızca açıklar.** Etkinleştirildiğinde model motor değerlerini
  alır ve bunlar hakkında metin yazar. Bir değeri değiştiremez.

V1 bilinçli olarak dardır: tek ürün, tek depo, tek çalışma kitabı. Bu kısıt
hesaplamayı denetlenebilir ve kapsamı dürüst tutar.

---

## 2. Öne Çıkan Özellikler

- **Yapılandırılmış Excel sözleşmesi.** Sabit adlara ve sütunlara sahip üç
  zorunlu sayfa; herhangi bir hesaplamadan önce doğrulanır.
- **Satır düzeyinde doğrulama geri bildirimi.** Her sorun bir kod, bir önem
  düzeyi ve seçilen dilde anlaşılır bir mesajla bildirilir.
- **Deterministik hesaplama motoru.** Mevcut stok, hareketli ortalama günlük
  tüketim, stok yeterlilik günü, yeniden sipariş noktası, hedef stok, envanter
  pozisyonu ve önerilen sipariş miktarı.
- **Yedi ekran.** Başlangıç, Genel Bakış Paneli, Stok Analizi, Tüketim Analizi,
  İkmal Planlaması, Raporlar ve AI Analisti.
- **Etkileşimli grafikler.** Stok bakiye eğilimi, günlük ve haftalık tüketim ile
  güvenlik stoğu–yeniden sipariş noktası karşılaştırması.
- **Excel ve PDF raporlama.** Beş sayfalık bir çalışma kitabı ve yedi bölümlük A4
  bir PDF; ikisi de aynı hesaplama sonucundan üretilir.
- **İsteğe bağlı AI yorumu.** Envanter içgörüleri, tüketim içgörüleri, ikmal
  açıklaması ve serbest sorular — veri seti ve rapor tarihi bazında önbelleğe
  alınır.
- **İki dilli arayüz.** Eksiksiz İngilizce ve Türkçe arayüz, yerel ayara uygun
  sayı ve tarih biçimlendirmesi.
- **Demo ve yükleme ayrımı.** Demo verisi ile kendi yüklemeleriniz aynı çalışma
  alanında asla bir arada bulunmaz.
- **Geçmiş dönem raporu davranışı.** Geçmiş bir rapor tarihi seçtiğinizde ekran,
  hangi planlama değerlerinin bilinçli olarak üretilmediğini tahmin yürütmek
  yerine açıklar.
- **Sessiz hata yok.** Eksik API anahtarı, erişilemeyen sağlayıcı veya kesilmiş
  yanıt görünür bir mesaj üretir; deterministik değerler bozulmadan kalır.

---

## 3. Nasıl Çalışır

İş akışı sekiz adımdır ve aynı sekiz adım Başlangıç ekranında gösterilir.

1. **Excel Şablonunu İndirin** — gerekli sayfaları ve sütunları zaten içeren
   çalışma kitabıyla başlayın.
2. **Ürün ve Stok Verisini Girin** — SKU'nuzu, açılış stoğunu, güvenlik stoğunu
   ve planlama parametrelerini ekleyin.
3. **Excel Dosyasını Yükleyin** — dosya etkinleşmeden önce her sayfa doğrulanır.
4. **Envanter Panelini İnceleyin** — mevcut stoğu, stok yeterlilik gününü,
   yeniden sipariş noktasını ve önerilen sipariş miktarını kontrol edin.
5. **Tüketimi Analiz Edin** — hareket olmayan günler dahil günlük ve haftalık
   çıkış tüketimini inceleyin.
6. **İkmal Önerilerini Gözden Geçirin** — envanter pozisyonunu yeniden sipariş
   noktasıyla karşılaştırın ve açık satın alma siparişlerini inceleyin.
7. **AI Analistine Sorun** — isteğe bağlı olarak sade dille bir açıklama isteyin
   (API anahtarı gerektirir).
8. **Excel veya PDF Raporlarını Dışa Aktarın** — seçilen rapor tarihi için
   biçimlendirilmiş bir çalışma kitabı ya da sunuma hazır bir PDF indirin.

### Hesaplama modeli

Tüm formüller doğrulanmış çalışma kitabını ve kenar çubuğunda seçilen rapor
tarihini kullanır.

| Metrik | Formül |
| --- | --- |
| Mevcut Stok | Açılış Stoğu + giriş hareketleri − çıkış hareketleri (rapor tarihine kadar) |
| Ortalama Günlük Tüketim | Tüketim penceresindeki çıkış miktarı ÷ penceredeki takvim günü |
| Stok Yeterlilik Günü | Mevcut Stok ÷ Ortalama Günlük Tüketim (tüketim sıfırsa `—`) |
| Yeniden Sipariş Noktası | Ortalama Günlük Tüketim × Tedarik Süresi (gün) + Güvenlik Stoğu |
| Hedef Stok | Ortalama Günlük Tüketim × (Tedarik Süresi + Hedef Kapsam Günü) + Güvenlik Stoğu |
| Envanter Pozisyonu | Mevcut Stok + tüm açık sipariş miktarları |
| Yeniden Sipariş Gerekli | Envanter Pozisyonu ≤ Yeniden Sipariş Noktası (sınır dahil) |
| Önerilen Sipariş Miktarı | Yeniden sipariş gerekmiyorsa `0`; aksi hâlde yukarı yuvarla(Hedef Stok − Envanter Pozisyonu) |

Tüketim penceresi hareketli **30 takvim günü**dür ve Açılış Stok Tarihi ile rapor
tarihi arasındaki aralığa sıkıştırılır. Çıkış hareketi olmayan günler atlanmaz,
sıfır tüketim olarak sayılır.

### Örnek hesap

13 Kasım 2026 rapor tarihiyle paketle gelen demo çalışma kitabı kullanıldığında:

| Değer | Sonuç |
| --- | --- |
| Mevcut Stok | 449 Adet |
| Ortalama Günlük Tüketim | 9,37 Adet/gün |
| Stok Yeterlilik Günü | 47,9 gün |
| Yeniden Sipariş Noktası | 212,4 Adet |
| Hedef Stok | 399,7 Adet |
| Açık Sipariş Miktarı | 300 Adet |
| Envanter Pozisyonu | 749 Adet |
| Önerilen Sipariş Miktarı | 0 Adet |

Envanter Pozisyonu (749) Yeniden Sipariş Noktasının (212,4) üzerinde olduğu için
yeniden sipariş gerekmez ve öneri sıfırdır. Bu sayılar paketle gelen dosyadan
yeniden üretilebilir; sabit kodlanmamıştır.

---

## 4. Ekranlar

Kenar çubuğu dil değiştiriciyi, çalışma alanı gezinmesini, ortak rapor tarihini,
etkin veri seti kartını ve "Çalışma alanını temizle" düğmesini barındırır. Rapor
tarihi geneldir: değiştirilmesi her ekranı ve iki raporu da yeniden hesaplar.

| Ekran | Amaç |
| --- | --- |
| **Başlangıç** | Ürünün giriş kapısı: hero, sekiz adımlık iş akışı, Excel sözleşmesi, sentetik demo açıklaması, veri gizliliği bildirimi, yol haritası ve sürüm/durum kartı. Şablonu indirme, demoyu yükleme ve çalışma kitabı yükleme de burada yapılır. |
| **Genel Bakış Paneli** | Özet ekranı. Dört KPI kartı (mevcut stok, ortalama günlük tüketim, stok yeterlilik günü, önerilen sipariş), stok seviyesi eğilimi, güvenlik stoğu–yeniden sipariş noktası karşılaştırması, günlük tüketim grafiği, stok durumu tablosu ve açık satın alma siparişleri tablosu. |
| **Stok Analizi** | Açılış ve mevcut stok ile toplam giriş ve çıkış, filtrelenebilir hareket geçmişi (tarih aralığı ve hareket tipi) ve her iki yönü de yansıtan bakiye eğilimi grafiği. |
| **Tüketim Analizi** | Ortalama günlük tüketim, toplam tüketim, en yüksek ve en düşük tüketim günü, günlük çizgi grafiği, haftalık çubuk grafiği ve açılabilir günlük değerler tablosu. Hareket olmayan günler sıfır olarak görünür. |
| **İkmal Planlaması** | Yeniden sipariş noktası, güvenlik stoğu, tedarik süresi, mevcut stok, açık sipariş miktarı, envanter pozisyonu, hedef stok, önerilen sipariş miktarı, yeniden sipariş durumu, gecikmiş siparişler, Envanter Pozisyonunun nasıl oluştuğunun açıklaması ve açık sipariş tablosu. |
| **Raporlar** | Her iki çıktı biçiminin açıklaması, rapor bağlamı şeridi ve iki indirme düğmesi. |
| **AI Analisti** | Deterministik destekleyici veri paneli, ardından isteğe bağlı AI bölümleri: envanter genel görünümü, öne çıkan bulgular, envanter riskleri, önerilen eylemler, tüketim içgörüleri, ikmal açıklaması ve serbest soru kutusu. |

Uyarılar gizlenmez, her zaman görünür: negatif stok, geçmiş dönem rapor tarihi,
eksik API anahtarı ve başarısız AI isteği birer uyarı şeridi gösterir; deterministik
değerler ekranda kalır.

---

## 5. Excel Veri Yapısı

Çalışma kitabı tam olarak şu üç sayfayı içermelidir. Sayfa adları ve sütun adları
sözleşmenin parçasıdır ve değiştirilmemelidir. Ek sütunlar korunur ancak
kullanılmaz.

### Product Master — tek satır

| Sütun | Tür | Kurallar |
| --- | --- | --- |
| `Product Code` | metin | Zorunlu, benzersiz. Tam olarak bir ürün satırı. |
| `Product Name` | metin | Zorunlu. |
| `Unit` | metin | Zorunlu (örneğin `Adet`, `pcs`, `kg`). |
| `Opening Stock` | tam sayı | Sıfır veya daha büyük. |
| `Opening Stock Date` | tarih | Zorunlu; hiçbir hareket bu tarihten önce olamaz. |
| `Safety Stock` | tam sayı | Sıfır veya daha büyük. |
| `Lead Time Days` | tam sayı | Sıfır veya daha büyük. |
| `Target Coverage Days` | tam sayı | Bir veya daha büyük. |

### Stock Movements — her hareket için bir satır

| Sütun | Tür | Kurallar |
| --- | --- | --- |
| `Date` | tarih | Geçerli Excel tarihi, Açılış Stok Tarihinde veya sonrasında. |
| `Transaction Type` | metin | `IN` veya `OUT`. |
| `Quantity` | tam sayı | Pozitif tam sayı. |
| `Description` | metin | İsteğe bağlı. |

### Open Orders — her satın alma siparişi için bir satır

| Sütun | Tür | Kurallar |
| --- | --- | --- |
| `Order No` | metin | Zorunlu, benzersiz. |
| `Order Quantity` | tam sayı | Pozitif tam sayı. |
| `Expected Delivery Date` | tarih | Geçerli Excel tarihi. |

Desteklenen tarih biçimleri: `YYYY-MM-DD`, `DD.MM.YYYY`, `DD/MM/YYYY`,
`YYYY/MM/DD`, `DD-MM-YYYY`.

Doğrulayıcı diğer kontrollerin yanı sıra şunları bildirir: eksik sayfalar, eksik
sütunlar, yinelenen ürün kodları, yinelenen sipariş numaraları, geçersiz hareket
tipleri, tam sayı olmayan veya negatif miktarlar, geçersiz tarihler ve açılış
stok tarihinden önce tarihlenmiş hareketler. Doğrulamadan geçemeyen bir dosya
asla etkin veri seti olmaz.

### Şablon

`templates/inventory-intelligence-template.xlsx`, yukarıdaki sütunları tam olarak
içeren üç sayfayı ve boş bir ürün satırını barındırır. Başlangıç ekranı bunu
indirilebilir olarak sunar. Hiç dokunulmamış şablonun yüklenmesi, yanıltıcı bir
boş panel üretmek yerine `empty_product_master` hatasıyla doğru şekilde reddedilir.

---

## 6. Demo Verisi

`templates/inventory-intelligence-demo.xlsx`, yalnızca gösterim amacıyla
üretilmiş **sentetik** bir çalışma kitabıdır. Gerçek şirket verisi değildir.

- Tek ürün: `PRF-4040-02` — "Galvanizli Kare Profil 40x40x2 mm - 6m", birim
  `Adet`.
- 18 stok hareketi ve 2 açık satın alma siparişi.
- 1 Ekim 2026 tarihinde 500 Adet açılış stoğu.

**Demo ve yüklemeler asla karışmaz.** Demoyu yüklemek etkin yüklemeyi, bir dosya
yüklemek de demoyu değiştirir. Kenar çubuğu hangi veri setinin etkin olduğunu her
zaman belirtir.

Demo, portföy sunumunda işe yarar çünkü gerçek yolu çalıştırır: gerçek bir
`.xlsx` dosyasından okunur ve yüklenen bir çalışma kitabıyla aynı doğrulama ve
hesaplama kodundan geçer.

---

## 7. AI Katmanı

AI katmanı **isteğe bağlıdır ve yapılandırılmadıkça kapalıdır**. Özerk bir
planlayıcı değil, sınırları belirli ince bir istemcidir.

### Ne yapar

- **AI Envanter Genel Görünümü** — motor değerlerinden türetilen anlatı bulgular,
  riskler ve önerilen eylemler.
- **Tüketim İçgörüleri** — tüketim penceresinin özeti, en yüksek/en düşük gün
  notları, sıfır tüketim notları ve gözlenen desenler.
- **İkmal Açıklaması** — yeniden siparişin neden gerekli olduğu ya da olmadığı;
  destekleyici veri ve kısıtlarla birlikte.
- **Serbest sorular** — etkin veri seti hakkında soru sorun; altı önerilen soru
  düğme olarak sunulur.

### Ne yapamaz

- Bir hesaplamayı değiştiremez. Destekleyici veri panelindeki her sayı
  `InventoryCalculation` nesnesinden gelir.
- Kendi kendine çalışamaz. İstek yalnızca bir AI düğmesine bastığınızda gönderilir.
- Satın alma siparişi, çok SKU'lu plan veya tahmin üretemez. Bunlar V1 kapsamı
  dışındadır.
- Sessizce başarısız olamaz. Sağlayıcı hatası veya kesilmiş yanıt bir uyarı
  şeridi gösterir ve deterministik değerler dokunulmadan kalır.

### İstekler nasıl kontrol edilir

- Yanıtlar, uzunluk sınırları olan katı şemalara göre doğrulanır; liste en fazla
  15 öğe, metin alanları en fazla 1.200 karakterdir.
- Her başarılı sonuç, bağlam parmak izi ve işlem adıyla önbelleğe alınır; böylece
  bir yeniden çalıştırma isteği tekrarlamaz ve aynı soru iki kez faturalanmaz.
  Hatalar asla önbelleğe alınmaz.
- Token tavanına takılan yanıt (`finish_reason == "length"`) tamam sanılıp
  gösterilmek yerine kesilmiş olarak reddedilir.
- Açık siparişler hiçbir aşamada mevcut stoğa eklenmez ve yapay zekâya da bu
  böyle bildirilir.

### Dil

**Arayüz** tamamen çevrilmiştir. **Model çıktısı İngilizcedir**: istem İngilizce
metin ister ve yanıtlar olduğu gibi gösterilir. AI Analisti ekranı bunu belirtir,
böylece Türkçe arayüz sürpriz yaratmaz.

---

## 8. Raporlar

İki çıktı aynı `ReportContext` nesnesinden üretilir; dolayısıyla indirilen
dosyalar her zaman panel ile aynı fikirde olur.

### Excel raporu — beş sayfa

1. `Executive Summary` — ürün, stok, tüketim ve ikmal değerleri tek sayfada.
2. `Stock Movements` — aralıktaki her giriş ve çıkış hareketi, kapanış bakiyesiyle.
3. `Consumption Analysis` — ortalama, toplam, en yüksek ve en düşük gün ile
   günlük ve haftalık seriler.
4. `Replenishment Plan` — planlama eşikleri, envanter pozisyonu ve önerilen
   sipariş.
5. `Open Purchase Orders` — sipariş miktarı, beklenen teslim tarihi ve gecikme
   durumu.

### PDF raporu — yedi bölüm

Rapor başlığı, yönetici özeti, stok analizi, tüketim analizi, ikmal planlaması,
açık satın alma siparişleri ile metodoloji ve notlar.

PDF, A4 dikey yönelimde, numaralı sayfalarla, panel ile aynı serilerden çizilen
grafiklerle ve Türkçe karakterlerin doğru görünmesi için gömülü bir TrueType
yazı tipiyle üretilir.

### Rapor dil kapsamı

**Excel ve PDF dosyaları, arayüz dilinden bağımsız olarak İngilizce üretilir.**
Panel değerleri, grafikler ve arayüz seçilen dili izler; rapor dosyaları izlemez.
Raporlar ekranı bunu açıkça belirtir, böylece kapsam hiçbir zaman belirsiz
kalmaz. Sayfa ve bölüm adları, indirdiğiniz dosyayla eşleşmesi için ekranda da
İngilizce tutulur.

Raporlar mevcut hesaplamanın statik anlık görüntüleridir. Formül içermezler.

---

## 9. Teknoloji Yığını

| Katman | Seçim |
| --- | --- |
| Dil | Python 3.11+ (3.11, 3.12 ve 3.13 üzerinde doğrulandı) |
| Arayüz | Streamlit (1.53 ve 1.67 üzerinde doğrulandı) |
| Veri | pandas, openpyxl |
| Grafikler | Plotly |
| PDF | ReportLab |
| AI doğrulama | Pydantic v2 |
| AI taşıma | Yalnızca Python standart kütüphanesi `urllib` |
| Testler | pytest ve Streamlit `AppTest` |
| Lint | Ruff |
| CI | GitHub Actions, Python 3.11/3.12/3.13 matrisi |

AI istemcisinde bilinçli olarak sağlayıcı SDK bağımlılığı yoktur: küçük ve
OpenAI uyumlu tek bir `chat/completions` çağrısı, bağımlılık yüzeyini ve
incelenecek yüzeyi küçük tutar.

### Proje düzeni

```text
inventory-intelligence/
├── app.py                    Streamlit giriş noktası ve sayfa yönlendirme
├── config.py                 Yollar, uygulama meta verisi, yükleme sınırları
├── pyproject.toml            Ruff ve pytest yapılandırması
├── requirements.txt          Çalışma zamanı bağımlılıkları
├── requirements-dev.txt      Çalışma zamanı + pytest + Ruff
├── .streamlit/config.toml    Tema ve yükleme yapılandırması
├── .github/workflows/ci.yml  Lint ve test matrisi
├── core/                     Çerçeveden bağımsız alan katmanı
│   ├── schema.py             Kanonik Excel sayfa/sütun sözleşmesi
│   ├── models.py             Alan modelleri ve hesaplama sonucu
│   ├── excel_reader.py       Çalışma kitabı okuyucu
│   ├── validation.py         Doğrulama motoru ve sorun bildirimi
│   ├── inventory.py          Mevcut stok ve bakiye geçmişi
│   ├── consumption.py        Hareketli ortalama günlük tüketim
│   ├── replenishment.py      Yeniden sipariş noktası, hedef stok, sipariş önerisi
│   └── calculations.py       Tek InventoryCalculation nesnesini oluşturur
├── analytics/series.py       Sonuçtan türetilen gösterim serileri
├── ai/                       İsteğe bağlı AI katmanı (istemci, istemler, şemalar, önbellek)
├── reports/                  Excel ve PDF üreticileri ile PDF teması/grafikleri
├── components/               Ekranlar, grafikler, kenar çubuğu, stiller, yardımcılar
├── utils/                    i18n, oturum durumu, veri yükleme, hesaplama önbelleği
├── templates/                Excel şablonu ve sentetik demo çalışma kitabı
└── tests/                    pytest takımı
```

`core/` paketi Streamlit'i asla içe aktarmaz. Bu sınır, motoru tarayıcı olmadan
test edilebilir kılan ve ekranları yalnızca sunum katmanı olarak tutan şeydir.

---

## 10. Kurulum

Gereksinim: **Python 3.11 veya daha yeni**.

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

Geliştirme için, test takımı ve linter dahil:

```bash
pip install -r requirements-dev.txt
```

### Uygulamayı çalıştırma

```bash
streamlit run app.py
```

`streamlit` PATH'te değilse:

```bash
python -m streamlit run app.py
```

Uygulama `http://localhost:8501` adresinde açılır.

### Testleri çalıştırma

```bash
python -m pytest -q
```

### Lint

```bash
python -m ruff check .
```

---

## 11. Yapılandırma

### Yükleme sınırları

`.streamlit/config.toml` temayı ve 10 MB yükleme sınırını ayarlar; `config.py`
`MAX_UPLOAD_SIZE_MB` değerini ve izin verilen uzantıyı (yalnızca `.xlsx`) tutar.

### AI sağlayıcısı

AI katmanı yapılandırmasını şu öncelik sırasıyla okur:

1. `.streamlit/secrets.toml` (asla commit edilmez),
2. ortam değişkenleri,
3. yerleşik varsayılanlar.

```toml
# .streamlit/secrets.toml  — bu dosya asla commit edilmemeli
AI_API_KEY = "your-key-here"
```

Kabul edilen anahtar adları `AI_API_KEY` ve `DEPLOY_API_KEY`'dir. İsteğe bağlı
geçersiz kılmalar: `AI_BASE_URL` ve `AI_MODEL`.

Varsayılanlar:

| Ayar | Değer |
| --- | --- |
| Temel URL | `https://api-cdn.deploy.com/api/v1` |
| Uç nokta | `POST /chat/completions` |
| Kimlik doğrulama | `Authorization: Bearer <key>` |
| Model | `deepseek-ai/deepseek-v4.1-flash-1017` |
| `max_tokens` | 4000 (en az kullanışlı bütçe olarak 3000 tabanı uygulanır) |
| `temperature` | 0.2 |
| Zaman aşımı | 60 sn |
| Yeniden deneme | Yalnızca 429/500/502/503/504 için 2 kez |

**Anahtar olmadan uygulama tamamen kullanılabilir**: tüm deterministik ekranlar
ve iki rapor çalışır, AI Analisti ekranı AI'ın kullanılamadığını açıklar.

### Sırlar

`.gitignore`; `.streamlit/secrets.toml`, `.env`, `.env.*`, `*.pem` ve `*.key`
dosyalarını dışlar. API anahtarı asla günlüğe yazılmaz ve asla ekranda
gösterilmez. Anahtarı commit etmeyin.

---

## 12. Kullanım

1. Uygulamayı açın. Başlangıç ekranı İngilizce yüklenir.
2. İsteğe bağlı olarak kenar çubuğundan dili **Türkçe** yapın. Değişiklik hemen
   uygulanır, bulunduğunuz ekranda kalırsınız ve oturum boyunca korunur.
3. Bir yol seçin:
   - **Şablonu İndir** ve kendi çalışma kitabınızı doldurun, veya
   - **Demo Verisini Yükle** ile sentetik veri setini keşfedin, veya
   - **Excel Dosyanızı Yükleyin** ile gerçek bir dosyayı doğrulayıp etkinleştirin.
4. Kenar çubuğunda **rapor tarihini** ayarlayın. Her ekran ve iki rapor bu tarihi
   izler.
5. Ekranları sırayla gezin: Genel Bakış → Stok Analizi → Tüketim Analizi →
   İkmal Planlaması.
6. İsteğe bağlı olarak **AI Analisti** ekranını açın. Anahtar yapılandırılmamışsa
   deterministik verileri ve "AI kullanılamıyor" bildirimini görürsünüz. Anahtar
   varsa bir üret düğmesine basarak tek bir istek harcarsınız; sonuç önbelleğe
   alınır.
7. **Raporlar** ekranını açıp Excel çalışma kitabını ve PDF'i indirin.
8. Etkin veri setini kaldırıp yeniden başlamak için **Çalışma alanını temizle**
   düğmesini kullanın.

Her şey tarayıcı oturumunda tutulur. Sayfanın tamamen yenilenmesi uygulamayı
varsayılan durumuna döndürür; V1 için belgelenmiş davranış budur.

---

## 13. Yol Haritası

### Tamamlandı — V1

| Paket | Kapsam |
| --- | --- |
| Paket 1 | Temel: kabuk, Excel sözleşmesi, doğrulama motoru, Başlangıç ekranı |
| Paket 2 | Envanter Hesaplama Motoru |
| Paket 3 | Analitik ve Panel |
| Paket 4 | Excel ve PDF Raporlama |
| Paket 5 | AI Zekâ Katmanı |

V1 özellik olarak tamdır ve geliştirme bitmiştir. Yerel, yayın öncesi bir
sürümdür.

### Planlandı — gelecek sürümler

| Sürüm | Kapsam | Durum |
| --- | --- | --- |
| V2 | ABC Analizi ve Talep Tahmini | Planlandı |
| V3 | Stok Optimizasyonu | Planlandı |
| V4 | Çok SKU ve Çok Depo Desteği | Planlandı |
| V5 | ERP Entegrasyonu ve İleri Otomasyon | Planlandı |

Mevcut V1 kapsamı tamamlanmıştır. Gelecek yol haritasındaki maddeler planlanan
geliştirmelerdir ve şu anda kullanıma açık değildir.

Planlanan maddelere tarih verilmemiştir ve bu bölümdeki hiçbir şey mevcut sürümde
uygulanmamıştır.

---

## 14. Sınırlamalar

Bunlar kusur değil, bilinçli V1 sınırlarıdır.

- **Tek SKU, tek depo.** Çalışma kitabı başına tek ürün satırı.
- **Tahmin yok.** Tüketim geçmişe dönük ölçülür; ileriye yansıtılmaz.
- **ABC analizi ve stok optimizasyonu yok.** İkisi de V2/V3 kapsamıdır.
- **ERP veya muhasebe entegrasyonu yok.** Tek girdi çalışma kitabıdır.
- **Geçmiş dönem rapor tarihleri sipariş önerisi üretmez.** Mevcut açık siparişler
  bugünün tedarikini anlatır, geçmiş bir tarihte var olan tedariki değil; bu
  yüzden Envanter Pozisyonundan çıkarılır ve öneri bir açıklamayla birlikte
  üretilmez.
- **Excel ve PDF raporları yalnızca İngilizcedir.** Arayüz ve paneller iki
  dillidir; rapor dosyaları değildir.
- **AI çıktısı yalnızca İngilizcedir** ve harici bir sağlayıcıya bağlıdır.
- **Durum yalnızca oturumda tutulur.** Sayfanın tamamen yenilenmesi çalışma
  alanını temizler.
- **Kimlik doğrulama yok.** V1 yerel, tek kullanıcılı bir araçtır ve giriş ekranı
  içermez.
- **AI katmanı karar desteğidir.** Otomatik planlama değildir ve her çıktı insan
  incelemesi gerektirir.
- **Geçmiş dönem tüketim penceresi kısa olabilir.** Çalışma kitabı 30 günden az
  kapsıyorsa ortalama, var olan günler üzerinden hesaplanır.

---

## 15. Mevcut Durum

| Öğe | Değer |
| --- | --- |
| Ürün | Inventory Intelligence V1 |
| Sürüm | 1.0.0 |
| Durum | Geliştirme Tamamlandı — Yayın Öncesi |
| Sürüm türü | Yerel demo |
| Tamamlanan paketler | 5 / 5 |
| Ekranlar | 7 |
| Arayüz dilleri | İngilizce · Türkçe |
| Otomatik testler | 190 |
| Doğrulanan Python | 3.11, 3.12, 3.13 |
| Doğrulanan Streamlit | 1.53, 1.67 |
| Lint | Ruff, temiz |

Bunun anlamı:

- V1 özellik seti uygulanmıştır ve otomatik takım desteklenen her Python
  sürümünde ve doğrulanan iki Streamlit sürümünde de geçer.
- Uygulama **yerel** olarak çalışmak üzere tasarlanmıştır. Herkese açık bir ortama
  dağıtılmamıştır, genel bir URL'si yoktur ve canlı bir ürün olarak
  yayımlanmamıştır.
- Demo veri seti sentetiktir ve arayüzde bu şekilde açıkça etiketlenmiştir.
- Bilinen sınırlamalar [14. bölümde](#14-sınırlamalar) listelenmiştir ve önemli
  oldukları yerlerde arayüzde de belirtilmiştir.
