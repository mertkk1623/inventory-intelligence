"""Central bilingual text and locale layer (English + Türkçe).

Design notes
------------
* The module is framework-independent. ``t()`` resolves the active language
  from the Streamlit session when a script run is active, and otherwise falls
  back to a module-level default. Pure-Python callers (the validation engine,
  the report builders, the test suite) therefore never import Streamlit.
* English is the default and every English string is byte-identical to the
  literal it replaced, so the pre-existing English UI — and the assertions in
  the existing test suite — are unchanged by this layer.
* Translations are keyed by the English source string. A missing key degrades
  to the English text instead of raising, which keeps the application usable
  even if a new label is added without a translation.
* Formatting helpers change presentation only. No calculation value is ever
  modified: English renders ``1,234.5`` and ``13 Nov 2026``; Turkish renders
  ``1.234,5`` and ``13.11.2026``.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

DEFAULT_LANGUAGE = "en"
LANGUAGES: tuple[str, ...] = ("en", "tr")
LANGUAGE_NAMES: dict[str, str] = {"en": "English", "tr": "Türkçe"}

LANGUAGE_KEY = "ii_language"
LANGUAGE_WIDGET_KEY = "ii_language_widget"

DASH = "—"
_EMPTY = "—"

_current: str = DEFAULT_LANGUAGE


# ---------------------------------------------------------------------------
# Language resolution
# ---------------------------------------------------------------------------


def resolve_language(code: object) -> str:
    """Return a supported language code, defaulting to English."""

    return code if isinstance(code, str) and code in LANGUAGES else DEFAULT_LANGUAGE


def _session_language() -> str | None:
    """Return the language stored in the active Streamlit session, if any.

    ``get_script_run_ctx()`` is ``None`` outside a Streamlit script run, which
    lets the same module serve plain-Python callers without emitting the
    "missing ScriptRunContext" warnings Streamlit would otherwise print.
    """

    try:  # pragma: no cover - depends on the Streamlit runtime
        import streamlit as st
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        if get_script_run_ctx() is None:
            return None
        return resolve_language(st.session_state.get(LANGUAGE_KEY))
    except Exception:  # noqa: BLE001 - never fail because of a UI concern
        return None


def get_language() -> str:
    """Return the active language code (``"en"`` or ``"tr"``)."""

    return _session_language() or _current


def set_language(code: object) -> str:
    """Set the language for the current Streamlit session.

    Inside a script run the choice belongs to the session, so it is written to
    ``st.session_state`` only. The module-level default is updated only when
    there is no script run (pure-Python callers), which keeps one browser
    session from leaking its language into another.
    """

    global _current
    resolved = resolve_language(code)
    try:  # pragma: no cover - depends on the Streamlit runtime
        import streamlit as st
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        if get_script_run_ctx() is not None:
            st.session_state[LANGUAGE_KEY] = resolved
            return resolved
    except Exception:  # noqa: BLE001 - never fail because of a UI concern
        pass
    _current = resolved
    return resolved


def is_turkish() -> bool:
    return get_language() == "tr"


def language_label(code: object) -> str:
    """Return the display name of a language code."""

    return LANGUAGE_NAMES[resolve_language(code)]


# ---------------------------------------------------------------------------
# Text lookup
# ---------------------------------------------------------------------------


def t(text: str, **kwargs: object) -> str:
    """Translate an English UI string into the active language.

    ``kwargs`` are formatted into the result, so a template such as
    ``"As of {date}"`` works in both languages.
    """

    if not text:
        return text
    translated = _TRANSLATIONS.get(text) if is_turkish() else None
    result = translated if translated is not None else text
    if kwargs:
        try:
            return result.format(**kwargs)
        except (KeyError, IndexError, ValueError):  # pragma: no cover - safety net
            return result
    return result


def has_translation(text: str) -> bool:
    """Return True when a Turkish translation exists for ``text``."""

    return text in _TRANSLATIONS


class LocalisedMessage(str):
    """A message that remembers its template so it can be re-translated.

    Domain modules (the validation engine, the calculation engine) build these
    instead of plain strings. The value behaves exactly like ``str`` and always
    holds the *English* sentence, so logs, tests and any pure-Python caller are
    stable. The UI calls :meth:`render` to display the message in the language
    active now, even if the message was created earlier in the session.
    """

    template: str
    params: dict

    def __new__(cls, template: str, /, **params: object) -> LocalisedMessage:
        try:
            rendered = template.format(**params)
        except (KeyError, IndexError, ValueError):  # pragma: no cover - safety net
            rendered = template
        obj = super().__new__(cls, rendered)
        obj.template = template
        obj.params = dict(params)
        return obj

    def render(self) -> str:
        """Return the message in the active language."""

        return t(self.template, **self.params)


def translate_message(message: object) -> str:
    """Translate a domain message, with a safe fallback for plain strings."""

    if isinstance(message, LocalisedMessage):
        return message.render()
    return t(str(message))


def missing_translations(texts: list[str] | tuple[str, ...]) -> list[str]:
    """Return the strings that still need a Turkish translation."""

    return [text for text in texts if text and text not in _TRANSLATIONS]


# ---------------------------------------------------------------------------
# Locale-aware formatting (display only)
# ---------------------------------------------------------------------------


def format_number(
    value: int | float | Decimal | None,
    *,
    places: int = 0,
) -> str:
    """Format a number with the separators of the active language."""

    if value is None:
        return _EMPTY
    text = f"{float(value):,.{places}f}"
    if is_turkish():
        return text.translate(str.maketrans({",": ".", ".": ","}))
    return text


def format_quantity(value: int | float | Decimal | None, unit: str = "") -> str:
    """Format a whole-unit quantity, for example ``449 Adet``."""

    if value is None:
        return _EMPTY
    number = format_number(round(float(value)))
    return f"{number} {unit}".strip()


def format_decimal(
    value: Decimal | float | int | None,
    unit: str = "",
    *,
    places: int = 1,
) -> str:
    """Format a decimal value for KPI and table display."""

    if value is None:
        return _EMPTY
    number = format_number(value, places=places)
    return f"{number} {unit}".strip()


def format_days(value: Decimal | float | int | None) -> str:
    """Format days of supply, including the zero-consumption case."""

    if value is None:
        return _EMPTY
    return f"{format_number(value, places=1)} {t('days')}"


def format_date(value: date | None) -> str:
    """Format a calendar date with the active language's convention."""

    if value is None:
        return _EMPTY
    return value.strftime("%d.%m.%Y" if is_turkish() else "%d %b %Y")


def per_day(unit: str) -> str:
    """Return a per-day rate unit such as ``Adet/day`` or ``Adet/gün``."""

    return f"{unit}/{t('day')}"


def chart_date_formats() -> tuple[str, str]:
    """Return ``(tick_format, hover_format)`` for Plotly date axes."""

    if is_turkish():
        return "%d.%m", "%d.%m.%Y"
    return "%d %b", "%d %b %Y"


def table_date_format() -> str:
    """Return the Streamlit ``DateColumn`` format for the active language."""

    return "DD.MM.YYYY" if is_turkish() else "YYYY-MM-DD"


def localise_columns(
    frame,
    columns: dict[str, int] | tuple[str, ...] | list[str],
):
    """Return a copy of ``frame`` with numeric columns rendered as text.

    Streamlit's ``NumberColumn`` always uses English separators, so Turkish
    tables would otherwise show ``1,234.5``. Converting the affected columns
    to locale-formatted strings keeps the visible table consistent with the
    KPI cards. English keeps the numeric dtype so the tables stay sortable.
    """

    if not is_turkish():
        return frame

    places = columns if isinstance(columns, dict) else {name: 0 for name in columns}
    localised = frame.copy()
    for name, decimals in places.items():
        if name not in localised.columns:
            continue
        localised[name] = localised[name].map(
            lambda value, digits=decimals: (
                _EMPTY
                if value is None or value != value
                else format_number(value, places=digits)
            )
        )
    return localised


# ---------------------------------------------------------------------------
# Translation table
# ---------------------------------------------------------------------------

_TRANSLATIONS: dict[str, str] = {
    # -- Language selector -------------------------------------------------
    "Language": "Dil",
    "Application language": "Uygulama dili",
    "Language preference is kept for this session.": (
        "Dil tercihi bu oturum boyunca korunur."
    ),
    # -- Navigation and page titles ---------------------------------------
    "Getting Started": "Başlangıç",
    "Dashboard": "Panel",
    "Stock Analysis": "Stok Analizi",
    "Consumption Analysis": "Tüketim Analizi",
    "Replenishment Planning": "İkmal Planlaması",
    "Reports": "Raporlar",
    "AI Analyst": "AI Analisti",
    "Overview Dashboard": "Genel Bakış Paneli",
    "Workspace": "Çalışma Alanı",
    "Workspace navigation": "Çalışma alanı gezinmesi",
    "Single-SKU planning workspace": "Tek SKU planlama çalışma alanı",
    # -- Shared vocabulary -------------------------------------------------
    "Current Stock": "Mevcut Stok",
    "Average Daily Consumption": "Günlük Ortalama Tüketim",
    "Reorder Point": "Yeniden Sipariş Noktası",
    "Safety Stock": "Güvenlik Stoğu",
    "Days of Supply": "Stokta Kalma Süresi",
    "Suggested Order Quantity": "Önerilen Sipariş Miktarı",
    "Inventory Position": "Envanter Pozisyonu",
    "Target Stock": "Hedef Stok",
    "Open Order Quantity": "Açık Sipariş Miktarı",
    "Open Purchase Orders": "Açık Satın Alma Siparişleri",
    "Lead Time": "Tedarik Süresi",
    "Opening Stock": "Açılış Stoğu",
    "Total IN": "Toplam Giriş",
    "Total OUT": "Toplam Çıkış",
    "Total Consumption": "Toplam Tüketim",
    "Highest Consumption Day": "En Yüksek Tüketim Günü",
    "Lowest Consumption Day": "En Düşük Tüketim Günü",
    "Reorder Required": "Yeniden Sipariş Gerekli",
    "Overdue Orders": "Gecikmiş Siparişler",
    "Stock Status": "Stok Durumu",
    "Stock Level Trend": "Stok Seviyesi Eğilimi",
    "Safety Stock vs Reorder Point": "Güvenlik Stoğu ve Yeniden Sipariş Noktası",
    "Daily Consumption Trend": "Günlük Tüketim Eğilimi",
    "Daily Consumption": "Günlük Tüketim",
    "Weekly Consumption": "Haftalık Tüketim",
    "Stock Movement History": "Stok Hareket Geçmişi",
    "Stock Balance Trend": "Stok Bakiye Eğilimi",
    "Movement filters": "Hareket filtreleri",
    "Report date": "Rapor tarihi",
    "Product Master": "Ürün Ana Verisi",
    "Stock Movements": "Stok Hareketleri",
    "Open Orders": "Açık Siparişler",
    "Executive Summary": "Yönetici Özeti",
    "Replenishment Plan": "İkmal Planı",
    "Product": "Ürün",
    "Unit": "Birim",
    "Quantity": "Miktar",
    "Description": "Açıklama",
    "Date": "Tarih",
    "Status": "Durum",
    "Product Code": "Ürün Kodu",
    "Product Name": "Ürün Adı",
    "Opening Stock Date": "Açılış Stok Tarihi",
    "Lead Time Days": "Tedarik Süresi (Gün)",
    "Target Coverage Days": "Hedef Kapsam (Gün)",
    "Order No": "Sipariş No",
    "Order Quantity": "Sipariş Miktarı",
    "Expected Delivery Date": "Beklenen Teslim Tarihi",
    "Transaction Type": "Hareket Türü",
    "Consumption": "Tüketim",
    "Days of Supply ": "Stokta Kalma Süresi ",
    "days": "gün",
    "day": "gün",
    "{unit}/day": "{unit}/gün",
    # -- Status vocabulary -------------------------------------------------
    "Healthy": "Sağlıklı",
    "Negative stock": "Negatif stok",
    "Reorder required": "Yeniden sipariş gerekli",
    "Below safety stock": "Güvenlik stoğunun altında",
    "Overdue": "Gecikmiş",
    "Scheduled": "Planlandı",
    "Not included": "Dahil edilmedi",
    "Not evaluated": "Değerlendirilmedi",
    "Not supported": "Desteklenmiyor",
    "Not generated": "Oluşturulmadı",
    "No": "Hayır",
    "Yes": "Evet",
    "No consumption": "Tüketim yok",
    "Historical report": "Geçmiş dönem raporu",
    "Current report": "Güncel rapor",
    "Historical report date": "Geçmiş dönem rapor tarihi",
    "Historical report limitation": "Geçmiş dönem raporu kısıtı",
    "Demo data": "Demo verisi",
    "Demo dataset": "Demo veri seti",
    "Uploaded file": "Yüklenen dosya",
    "Uploaded workbook": "Yüklenen çalışma kitabı",
    "Data Overview": "Veri Özeti",
    "As of {date}": "{date} itibarıyla",
    # -- Sidebar -----------------------------------------------------------
    "All calculations use movements up to this date. The earliest selectable "
    "date is the Opening Stock Date.": (
        "Tüm hesaplamalar bu tarihe kadarki hareketleri kullanır. Seçilebilecek "
        "en erken tarih Açılış Stok Tarihi'dir."
    ),
    "Calculations use movements up to {date}.": (
        "Hesaplamalar {date} tarihine kadarki hareketleri kullanır."
    ),
    "Clear workspace": "Çalışma alanını temizle",
    "No dataset loaded": "Veri seti yüklenmedi",
    "Start from Getting Started": "Başlangıç ekranından başlayın",
    "Download the template, try the demo, or upload your own workbook.": (
        "Şablonu indirin, demoyu deneyin veya kendi çalışma kitabınızı yükleyin."
    ),
    "Active dataset": "Etkin veri seti",
    "movement": "hareket",
    "movements": "hareket",
    "open orders": "açık sipariş",
    "{code} · {movements} movements · {orders} open orders": (
        "{code} · {movements} hareket · {orders} açık sipariş"
    ),
    # -- Welcome: hero -----------------------------------------------------
    "Inventory Intelligence · V1": "Inventory Intelligence · V1",
    "AI-powered inventory analytics and replenishment decision support.": (
        "AI destekli stok analizi ve ikmal karar destek sistemi."
    ),
    "The application helps users understand stock levels, consumption patterns, "
    "replenishment requirements and inventory risks using structured Excel "
    "data.": (
        "Uygulama, yapılandırılmış Excel verilerini kullanarak stok "
        "seviyelerini, tüketim eğilimlerini, ikmal ihtiyaçlarını ve envanter "
        "risklerini analiz etmeye yardımcı olur."
    ),
    "Single-SKU workspace": "Tek SKU çalışma alanı",
    "Local validation": "Yerel doğrulama",
    "Excel-native": "Excel tabanlı",
    "Your workbook": "Çalışma kitabınız",
    "Product & planning parameters": "Ürün ve planlama parametreleri",
    "Dated IN and OUT records": "Tarihli giriş ve çıkış kayıtları",
    "Incoming purchase orders": "Yoldaki satın alma siparişleri",
    # -- Welcome: How It Works --------------------------------------------
    "How It Works": "Nasıl Çalışır",
    "Eight steps from workbook to decision": (
        "Çalışma kitabından karara sekiz adım"
    ),
    "Inventory Intelligence validates your Excel file before any analysis "
    "starts, so every later decision is based on clean data.": (
        "Inventory Intelligence, analiz başlamadan önce Excel dosyanızı "
        "doğrular; böylece sonraki her karar temiz veriye dayanır."
    ),
    "Download Excel Template": "Excel Şablonunu İndir",
    "Start with the workbook that already contains the required sheets and "
    "columns.": (
        "Gerekli sayfaları ve kolonları içeren çalışma kitabıyla başlayın."
    ),
    "Enter Product and Stock Data": "Ürün ve Stok Verilerini Gir",
    "Add your SKU, opening stock, safety stock and planning parameters.": (
        "SKU'nuzu, açılış stoğunu, güvenlik stoğunu ve planlama "
        "parametrelerini girin."
    ),
    "Upload Excel File": "Excel Dosyasını Yükle",
    "Drop in the completed workbook. Every sheet is validated before loading.": (
        "Tamamlanmış çalışma kitabını yükleyin. Her sayfa yüklenmeden önce "
        "doğrulanır."
    ),
    "Review Inventory Dashboard": "Stok Panelini İncele",
    "Check current stock, days of supply, the reorder point and the suggested "
    "order quantity.": (
        "Mevcut stoğu, stokta kalma süresini, yeniden sipariş noktasını ve "
        "önerilen sipariş miktarını kontrol edin."
    ),
    "Analyze Consumption": "Tüketimi Analiz Et",
    "Inspect daily and weekly OUT consumption, including zero-consumption "
    "days.": (
        "Sıfır tüketimli günler dahil günlük ve haftalık çıkış tüketimini "
        "inceleyin."
    ),
    "Review Replenishment Recommendations": "İkmal Önerilerini İncele",
    "Compare inventory position with the reorder point and review open "
    "purchase orders.": (
        "Envanter pozisyonunu yeniden sipariş noktasıyla karşılaştırın ve açık "
        "satın alma siparişlerini gözden geçirin."
    ),
    "Ask AI Analyst": "AI Analisti Kullan",
    "Optionally ask the AI analyst to explain the numbers in plain language.": (
        "İsterseniz AI analistinden sayıları sade bir dille açıklamasını "
        "isteyin."
    ),
    "Export Excel or PDF Reports": "Excel veya PDF Raporlarını Dışa Aktar",
    "Download a formatted Excel workbook or a presentation-ready PDF for the "
    "selected report date.": (
        "Seçilen rapor tarihi için biçimlendirilmiş bir Excel çalışma kitabı "
        "veya sunuma hazır bir PDF indirin."
    ),
    # -- Welcome: Get started ---------------------------------------------
    "Get Started": "Başlayın",
    "Choose how you want to begin": "Nasıl başlamak istediğinizi seçin",
    "Upload your own workbook, or load the bundled demo workbook to compare "
    "it with the sample scenarios above.": (
        "Kendi çalışma kitabınızı yükleyin veya paketle gelen demo çalışma "
        "kitabını yükleyerek yukarıdaki örnek senaryolarla karşılaştırın."
    ),
    "Try Demo Data": "Demo Verisini Dene",
    "Explore the workspace with a synthetic single-SKU dataset. Demo data is "
    "generated for demonstration only and is not real company data.": (
        "Çalışma alanını sentetik tek SKU veri setiyle keşfedin. Demo verisi "
        "yalnızca gösterim amacıyla üretilmiştir ve gerçek şirket verisi "
        "değildir."
    ),
    "Load Demo Data": "Demo Verisini Yükle",
    "Upload Your Excel": "Excel Dosyanızı Yükleyin",
    "Already have a completed workbook? Upload it and we will validate every "
    "sheet before it becomes active. XLSX only, up to {size} MB.": (
        "Tamamlanmış bir çalışma kitabınız var mı? Yükleyin; etkinleşmeden önce "
        "her sayfayı doğrularız. Yalnızca XLSX, en fazla {size} MB."
    ),
    "Upload your Excel workbook": "Excel çalışma kitabınızı yükleyin",
    "Use the Inventory Intelligence template. Only .xlsx files up to {size} MB "
    "are supported.": (
        "Inventory Intelligence şablonunu kullanın. Yalnızca {size} MB'a kadar "
        ".xlsx dosyaları desteklenir."
    ),
    # -- Welcome: Excel requirements --------------------------------------
    "Excel Data Requirements": "Excel Veri Gereksinimleri",
    "A simple three-sheet workbook": "Üç sayfalık basit bir çalışma kitabı",
    "Keep the template structure intact. The validator checks sheet names, "
    "column names, data types and cross-sheet rules.": (
        "Şablon yapısını bozmayın. Doğrulayıcı sayfa adlarını, kolon adlarını, "
        "veri türlerini ve sayfalar arası kuralları kontrol eder."
    ),
    "One row describing your single SKU, its opening stock and the planning "
    "parameters used by later modules.": (
        "Tek SKU'nuzu, açılış stoğunu ve sonraki modüllerin kullandığı planlama "
        "parametrelerini tanımlayan tek satır."
    ),
    "Dated IN and OUT transactions recorded on or after the opening stock "
    "date.": (
        "Açılış stok tarihinde veya sonrasında kaydedilen tarihli giriş ve "
        "çıkış hareketleri."
    ),
    "Purchase orders that have not been delivered yet. They are treated as "
    "incoming supply and never added to Current Stock.": (
        "Henüz teslim edilmemiş satın alma siparişleri. Yoldaki tedarik olarak "
        "değerlendirilir ve Mevcut Stoğa asla eklenmez."
    ),
    "Data rules": "Veri kuralları",
    "Exactly one product row with a unique Product Code.": (
        "Benzersiz Ürün Kodu ile tam olarak bir ürün satırı."
    ),
    "Movement and order quantities must be positive whole numbers.": (
        "Hareket ve sipariş miktarları pozitif tam sayı olmalıdır."
    ),
    "Opening Stock and Safety Stock must be zero or greater.": (
        "Açılış Stoğu ve Güvenlik Stoğu sıfır veya daha büyük olmalıdır."
    ),
    "Transaction Type must be IN or OUT.": "Hareket Türü IN veya OUT olmalıdır.",
    "Dates must be valid Excel dates.": "Tarihler geçerli Excel tarihleri olmalıdır.",
    "No movement may be dated before the Opening Stock Date.": (
        "Hiçbir hareket Açılış Stok Tarihi'nden önce olamaz."
    ),
    "Order numbers must be unique.": "Sipariş numaraları benzersiz olmalıdır.",
    "Required sheet and column names must stay unchanged.": (
        "Gerekli sayfa ve kolon adları değiştirilmemelidir."
    ),
    # -- Welcome: privacy --------------------------------------------------
    "Data Privacy": "Veri Gizliliği",
    "What happens to your workbook": "Çalışma kitabınıza ne olur",
    "Your workbook is read and validated inside this session. The file is "
    "never written to disk, never uploaded to a database and is discarded when "
    "the session ends. The AI layer is optional: it stays switched off unless "
    "an API key is configured, and it only runs when you press an AI button. "
    "When it runs, the request contains the calculated engine values plus "
    "short, length-limited text fields (product name, movement descriptions) "
    "sent to the configured provider. No API key is configured in this "
    "deployment, so no data leaves this session.": (
        "Çalışma kitabınız bu oturum içinde okunur ve doğrulanır. Dosya diske "
        "yazılmaz, bir veritabanına yüklenmez ve oturum sona erdiğinde atılır. "
        "AI katmanı isteğe bağlıdır: bir API anahtarı yapılandırılmadıkça kapalı "
        "kalır ve yalnızca bir AI düğmesine bastığınızda çalışır. Çalıştığında "
        "istek, hesaplanan motor değerlerini ve kısa, uzunluğu sınırlandırılmış "
        "metin alanlarını (ürün adı, hareket açıklamaları) yapılandırılmış "
        "sağlayıcıya gönderir. Bu kurulumda API anahtarı tanımlı değildir; bu "
        "nedenle bu oturumdan hiçbir veri dışarı çıkmaz."
    ),
    "Your workbook is read and validated inside this session. The file is "
    "never written to disk, never uploaded to a database and is discarded when "
    "the session ends. The AI layer is optional: it stays switched off unless "
    "an API key is configured, and it only runs when you press an AI button. "
    "When it runs, the request contains the calculated engine values plus "
    "short, length-limited text fields (product name, movement descriptions) "
    "sent to the configured provider. An API key is configured in this "
    "deployment, so an AI request is sent only when you click an AI button.": (
        "Çalışma kitabınız bu oturum içinde okunur ve doğrulanır. Dosya diske "
        "yazılmaz, bir veritabanına yüklenmez ve oturum sona erdiğinde atılır. "
        "AI katmanı isteğe bağlıdır: bir API anahtarı yapılandırılmadıkça kapalı "
        "kalır ve yalnızca bir AI düğmesine bastığınızda çalışır. Çalıştığında "
        "istek, hesaplanan motor değerlerini ve kısa, uzunluğu sınırlandırılmış "
        "metin alanlarını (ürün adı, hareket açıklamaları) yapılandırılmış "
        "sağlayıcıya gönderir. Bu kurulumda bir API anahtarı tanımlıdır; "
        "dolayısıyla AI isteği yalnızca bir AI düğmesine tıkladığınızda "
        "gönderilir."
    ),
    # -- Welcome: roadmap --------------------------------------------------
    "Roadmap": "Yol Haritası",
    "Where the product stands today": "Ürünün bugünkü durumu",
    "Completed": "Tamamlandı",
    "Planned": "Planlandı",
    "FUTURE": "GELECEK",
    "Current version: V1": "Mevcut sürüm: V1",
    "Package 1 — Foundation": "Paket 1 — Temel Altyapı",
    "Package 2 — Inventory Calculation Engine": "Paket 2 — Stok Hesaplama Motoru",
    "Package 3 — Analytics and Dashboard": "Paket 3 — Analitik ve Panel",
    "Package 4 — Excel and PDF Reporting": "Paket 4 — Excel ve PDF Raporlama",
    "Package 5 — AI Intelligence Layer": "Paket 5 — AI Zeka Katmanı",
    "V2 — ABC Analysis and Demand Forecasting": "V2 — ABC Analizi ve Talep Tahmini",
    "V3 — Stock Optimization": "V3 — Stok Optimizasyonu",
    "V4 — Multi-SKU and Multi-Warehouse Support": (
        "V4 — Çoklu SKU ve Çoklu Depo Desteği"
    ),
    "V5 — ERP Integration and Advanced Automation": (
        "V5 — ERP Entegrasyonu ve İleri Otomasyon"
    ),
    "The current V1 scope is complete. Future roadmap items are planned "
    "enhancements and are not currently available.": (
        "Mevcut V1 kapsamı tamamlanmıştır. Gelecek yol haritasındaki maddeler "
        "planlanan geliştirmelerdir ve şu anda kullanıma açık değildir."
    ),
    # -- Welcome: version / status ----------------------------------------
    "Project Status": "Proje Durumu",
    "Version": "Sürüm",
    "Inventory Intelligence V1": "Inventory Intelligence V1",
    "Development Complete — Pre-Release": (
        "Geliştirme Tamamlandı — Yayın Öncesi"
    ),
    "Local demo build. Not deployed to a public environment and not published "
    "as a live product.": (
        "Yerel demo sürümü. Herkese açık bir ortama kurulmamıştır ve canlı ürün "
        "olarak yayınlanmamıştır."
    ),
    "Packages": "Paketler",
    "Completed packages": "Tamamlanan paketler",
    "Automated tests": "Otomatik testler",
    "Screens": "Ekranlar",
    "Interface languages": "Arayüz dilleri",
    # -- Dashboard ---------------------------------------------------------
    "{code} · {name} · {unit} planning workspace.": (
        "{code} · {name} · {unit} planlama çalışma alanı."
    ),
    "Negative stock detected": "Negatif stok tespit edildi",
    "The running balance dropped below zero at some point up to the report "
    "date. Lowest balance: {balance} {unit}.": (
        "Rapor tarihine kadar bakiye bir noktada sıfırın altına düştü. En düşük "
        "bakiye: {balance} {unit}."
    ),
    "Inventory position is at or below the reorder point. Suggested order "
    "quantity: {quantity} {unit}.": (
        "Envanter pozisyonu yeniden sipariş noktasında veya altında. Önerilen "
        "sipariş miktarı: {quantity} {unit}."
    ),
    "Opening {opening} · IN {inbound} · OUT {outbound}": (
        "Açılış {opening} · Giriş {inbound} · Çıkış {outbound}"
    ),
    "{days} calendar days covered": "{days} takvim günü kapsandı",
    "No consumption in the window": "Pencere içinde tüketim yok",
    "At the current consumption rate": "Mevcut tüketim hızında",
    "Not generated for historical reports": (
        "Geçmiş dönem raporları için oluşturulmaz"
    ),
    "No reorder required": "Yeniden sipariş gerekli değil",
    "Daily closing balance with safety stock and reorder point.": (
        "Güvenlik stoğu ve yeniden sipariş noktası ile günlük kapanış bakiyesi."
    ),
    "Current stock is shown as a reference line.": (
        "Mevcut stok referans çizgisi olarak gösterilir."
    ),
    "OUT movements in the rolling consumption window. Days without consumption "
    "are shown as zero.": (
        "Hareketli tüketim penceresindeki çıkış hareketleri. Tüketim olmayan "
        "günler sıfır olarak gösterilir."
    ),
    "Current stock, planning thresholds and stock health.": (
        "Mevcut stok, planlama eşikleri ve stok sağlığı."
    ),
    "Purchase orders awaiting delivery.": "Teslim bekleyen satın alma siparişleri.",
    "No open purchase orders": "Açık satın alma siparişi yok",
    "This workbook contains no incoming purchase orders.": (
        "Bu çalışma kitabında yolda olan satın alma siparişi yok."
    ),
    "Current open orders are not included": "Mevcut açık siparişler dahil edilmez",
    "These orders are shown for reference only. Historical reports exclude "
    "current open orders from Inventory Position.": (
        "Bu siparişler yalnızca referans için gösterilir. Geçmiş dönem raporları "
        "mevcut açık siparişleri Envanter Pozisyonuna dahil etmez."
    ),
    "Total open order quantity: {quantity} {unit}.": (
        "Toplam açık sipariş miktarı: {quantity} {unit}."
    ),
    # -- Stock analysis ----------------------------------------------------
    "Review every IN and OUT movement, then inspect how the balance developed "
    "through the report date.": (
        "Her giriş ve çıkış hareketini inceleyin, ardından bakiyenin rapor "
        "tarihine kadar nasıl geliştiğini görün."
    ),
    "Lowest running balance: {balance} {unit}. The balance is not clamped to "
    "zero.": (
        "En düşük bakiye: {balance} {unit}. Bakiye sıfıra sabitlenmez."
    ),
    "At {date}": "{date} itibarıyla",
    "Up to the report date": "Rapor tarihine kadar",
    "Newest movements first. Use the filters above to narrow the list.": (
        "En yeni hareket önce. Listeyi daraltmak için yukarıdaki filtreleri "
        "kullanın."
    ),
    "{count} movements · IN {inbound} · OUT {outbound} {unit}": (
        "{count} hareket · Giriş {inbound} · Çıkış {outbound} {unit}"
    ),
    "{count} movement · IN {inbound} · OUT {outbound} {unit}": (
        "{count} hareket · Giriş {inbound} · Çıkış {outbound} {unit}"
    ),
    "No movements match these filters": "Bu filtrelerle eşleşen hareket yok",
    "Adjust the date range or include IN and OUT movements.": (
        "Tarih aralığını değiştirin veya giriş ve çıkış hareketlerini dahil "
        "edin."
    ),
    "The balance always includes both IN and OUT movements, even when the "
    "history table is filtered to one direction.": (
        "Bakiye, geçmiş tablosu tek yöne filtrelenmiş olsa bile her zaman hem "
        "giriş hem çıkış hareketlerini içerir."
    ),
    "No balance points in this range": "Bu aralıkta bakiye noktası yok",
    "Choose a date range within the dataset history.": (
        "Veri seti geçmişi içinde bir tarih aralığı seçin."
    ),
    "Dates are limited to the validated dataset history.": (
        "Tarihler doğrulanmış veri seti geçmişiyle sınırlıdır."
    ),
    "From": "Başlangıç",
    "To": "Bitiş",
    "Transaction type": "Hareket türü",
    "The start date is after the end date. The range has been reversed for "
    "this view.": (
        "Başlangıç tarihi bitiş tarihinden sonra. Bu görünüm için aralık ters "
        "çevrildi."
    ),
    "No description": "Açıklama yok",
    # -- Consumption analysis ---------------------------------------------
    "Understand OUT consumption in the rolling calculation window. Days "
    "without movements remain visible as zero.": (
        "Hareketli hesaplama penceresindeki çıkış tüketimini anlayın. Hareket "
        "olmayan günler sıfır olarak görünür."
    ),
    "No consumption window": "Tüketim penceresi yok",
    "The report date does not provide a consumption window for this dataset.": (
        "Rapor tarihi bu veri seti için bir tüketim penceresi sağlamıyor."
    ),
    "No consumption recorded": "Tüketim kaydı yok",
    "There are no OUT movements in the consumption window. Average daily "
    "consumption is zero and every day is shown as zero.": (
        "Tüketim penceresinde çıkış hareketi yok. Günlük ortalama tüketim "
        "sıfırdır ve her gün sıfır olarak gösterilir."
    ),
    "Window {window}": "Pencere {window}",
    "No OUT movements in the window": "Pencerede çıkış hareketi yok",
    "Zero-consumption days included": "Sıfır tüketimli günler dahil",
    "OUT units per calendar day. Missing days are explicitly zero.": (
        "Takvim günü başına çıkış miktarı. Eksik günler açıkça sıfırdır."
    ),
    "Monday-based weekly totals across the consumption window.": (
        "Tüketim penceresi boyunca pazartesi başlangıçlı haftalık toplamlar."
    ),
    "Daily consumption values": "Günlük tüketim değerleri",
    # -- Replenishment -----------------------------------------------------
    "Compare stock, open supply and planning thresholds to decide whether a "
    "new purchase order is needed.": (
        "Yeni bir satın alma siparişi gerekip gerekmediğine karar vermek için "
        "stoğu, yoldaki tedariği ve planlama eşiklerini karşılaştırın."
    ),
    "The planning values below use the unclamped current stock.": (
        "Aşağıdaki planlama değerleri sıfıra sabitlenmemiş mevcut stoğu "
        "kullanır."
    ),
    "Inventory position ({position} {unit}) is at or below the reorder point "
    "({point} {unit}). Suggested order quantity: {quantity} {unit}.": (
        "Envanter pozisyonu ({position} {unit}) yeniden sipariş noktasında "
        "veya altında ({point} {unit}). Önerilen sipariş miktarı: "
        "{quantity} {unit}."
    ),
    "Inventory position ({position} {unit}) is above the reorder point "
    "({point} {unit}).": (
        "Envanter pozisyonu ({position} {unit}) yeniden sipariş noktasının "
        "üzerinde ({point} {unit})."
    ),
    "Average consumption × lead time + safety stock": (
        "Ortalama tüketim × tedarik süresi + güvenlik stoğu"
    ),
    "Minimum planning buffer": "Asgari planlama tamponu",
    "Expected supplier lead time": "Beklenen tedarikçi süresi",
    "Open orders are not added to stock": "Açık siparişler stoğa eklenmez",
    "Excluded from historical inventory position": (
        "Geçmiş dönem envanter pozisyonundan hariç tutulur"
    ),
    "All open orders are included": "Tüm açık siparişler dahil edilir",
    "Current stock + all open orders": "Mevcut stok + tüm açık siparişler",
    "Current stock only (historical report)": (
        "Yalnızca mevcut stok (geçmiş dönem raporu)"
    ),
    "Average consumption × (lead + coverage) + safety stock": (
        "Ortalama tüketim × (tedarik + kapsam) + güvenlik stoğu"
    ),
    "Order up to target stock": "Hedef stoğa kadar sipariş ver",
    "Inventory position is at or below the reorder point": (
        "Envanter pozisyonu yeniden sipariş noktasında veya altında"
    ),
    "Inventory position is above the reorder point": (
        "Envanter pozisyonu yeniden sipariş noktasının üzerinde"
    ),
    "Expected delivery date before the report date": (
        "Beklenen teslim tarihi rapor tarihinden önce"
    ),
    "How Inventory Position works": "Envanter Pozisyonu nasıl çalışır",
    "Inventory Position = Current Stock + all open order quantities. Open "
    "orders are treated as incoming supply and are never added to Current "
    "Stock.": (
        "Envanter Pozisyonu = Mevcut Stok + tüm açık sipariş miktarları. Açık "
        "siparişler yoldaki tedarik olarak değerlendirilir ve Mevcut Stoğa asla "
        "eklenmez."
    ),
    "Order number, quantity and expected delivery date.": (
        "Sipariş numarası, miktar ve beklenen teslim tarihi."
    ),
    "Inventory Position therefore equals Current Stock.": (
        "Bu nedenle Envanter Pozisyonu Mevcut Stoka eşittir."
    ),
    "Reference only": "Yalnızca referans",
    "Current open orders are shown for reference but are excluded from this "
    "historical report's Inventory Position.": (
        "Mevcut açık siparişler referans için gösterilir ancak bu geçmiş dönem "
        "raporunun Envanter Pozisyonundan hariç tutulur."
    ),
    "{count} open order · Total quantity {quantity} {unit}.": (
        "{count} açık sipariş · Toplam miktar {quantity} {unit}."
    ),
    "{count} open orders · Total quantity {quantity} {unit}.": (
        "{count} açık sipariş · Toplam miktar {quantity} {unit}."
    ),
    # -- Reports screen ----------------------------------------------------
    "Download a formatted Excel workbook or a presentation-ready PDF for the "
    "selected report date. Both files are generated from the same calculation "
    "result.": (
        "Seçilen rapor tarihi için biçimlendirilmiş bir Excel çalışma kitabı "
        "veya sunuma hazır bir PDF indirin. Her iki dosya da aynı hesaplama "
        "sonucundan üretilir."
    ),
    "The report could not be prepared for this dataset and report date. "
    "Details: {error}": (
        "Bu veri seti ve rapor tarihi için rapor hazırlanamadı. Ayrıntı: {error}"
    ),
    "Replenishment planning is supported only for the current report date. "
    "This report keeps the stock and consumption history up to {date} and "
    "explains the planning limitation instead of showing order suggestions.": (
        "İkmal planlaması yalnızca güncel rapor tarihi için desteklenir. Bu "
        "rapor {date} tarihine kadarki stok ve tüketim geçmişini korur ve "
        "sipariş önerileri göstermek yerine planlama kısıtını açıklar."
    ),
    "Report date {date}": "Rapor tarihi {date}",
    "Current stock {quantity}": "Mevcut stok {quantity}",
    "{count} movements in range": "Aralıkta {count} hareket",
    "Static snapshots.": "Statik görüntüler.",
    "Reports are built from the workbook currently loaded in the workspace. "
    "Changing the report date in the sidebar regenerates both files with a new "
    "date, so the download always matches what the dashboard shows.": (
        "Raporlar çalışma alanında yüklü olan çalışma kitabından üretilir. "
        "Kenar çubuğundaki rapor tarihini değiştirmek her iki dosyayı yeni "
        "tarihle yeniden üretir; böylece indirme her zaman panelde görünenle "
        "eşleşir."
    ),
    "Spreadsheet": "Elektronik tablo",
    "Document": "Belge",
    "Excel Report": "Excel Raporu",
    "PDF Report": "PDF Raporu",
    "A structured workbook for analysis and sharing. Five sheets cover the "
    "executive summary, every movement, consumption detail, the replenishment "
    "plan and open purchase orders. Values are static so the file matches the "
    "calculation engine exactly.": (
        "Analiz ve paylaşım için yapılandırılmış bir çalışma kitabı. Beş sayfa "
        "yönetici özetini, tüm hareketleri, tüketim ayrıntısını, ikmal planını "
        "ve açık satın alma siparişlerini kapsar. Değerler statiktir; dosya "
        "hesaplama motoruyla birebir eşleşir."
    ),
    "A presentation-ready A4 document for management review. Seven sections "
    "combine the key position, a stock balance trend and the consumption "
    "charts with the planning methodology behind them.": (
        "Yönetim incelemesi için sunuma hazır A4 belge. Yedi bölüm; temel "
        "durumu, stok bakiye eğilimini ve tüketim grafiklerini arkalarındaki "
        "planlama metodolojisiyle birleştirir."
    ),
    "Frozen header rows, filters on table sheets, consistent date and number "
    "formats. No formulas; every value is written by Python.": (
        "Sabit başlık satırları, tablo sayfalarında filtreler, tutarlı tarih ve "
        "sayı biçimleri. Formül yok; her değer Python tarafından yazılır."
    ),
    "A4 portrait, navy and primary blue, numbered pages and charts drawn from "
    "the same series as the dashboard.": (
        "A4 dikey, lacivert ve ana mavi, numaralı sayfalar ve panelle aynı "
        "serilerden çizilen grafikler."
    ),
    "Sheets included": "İçerdiği sayfalar",
    "Sections included": "İçerdiği bölümler",
    "Product, stock, consumption and replenishment values on one page.": (
        "Ürün, stok, tüketim ve ikmal değerleri tek sayfada."
    ),
    "Every IN and OUT movement in range with its closing balance.": (
        "Aralıktaki her giriş ve çıkış hareketi kapanış bakiyesiyle."
    ),
    "Average, total, highest and lowest day plus daily and weekly series.": (
        "Ortalama, toplam, en yüksek ve en düşük gün ile günlük ve haftalık "
        "seriler."
    ),
    "Planning thresholds, inventory position and the suggested order.": (
        "Planlama eşikleri, envanter pozisyonu ve önerilen sipariş."
    ),
    "Order quantity, expected delivery date and overdue status.": (
        "Sipariş miktarı, beklenen teslim tarihi ve gecikme durumu."
    ),
    "Report header": "Rapor başlığı",
    "Product, report date and generation date.": (
        "Ürün, rapor tarihi ve üretim tarihi."
    ),
    "Current stock, consumption, supply and suggested order.": (
        "Mevcut stok, tüketim, tedarik ve önerilen sipariş."
    ),
    "Opening and current stock, IN/OUT totals and balance trend.": (
        "Açılış ve mevcut stok, giriş/çıkış toplamları ve bakiye eğilimi."
    ),
    "Daily and weekly charts with the consumption summary.": (
        "Tüketim özetiyle birlikte günlük ve haftalık grafikler."
    ),
    "Thresholds, inventory position and reorder status.": (
        "Eşikler, envanter pozisyonu ve yeniden sipariş durumu."
    ),
    "Delivery schedule and overdue status.": "Teslim programı ve gecikme durumu.",
    "Methodology & notes": "Metodoloji ve notlar",
    "Formulas, report window and reporting limitations.": (
        "Formüller, rapor penceresi ve raporlama kısıtları."
    ),
    "Download Excel Report": "Excel Raporunu İndir",
    "Download PDF Report": "PDF Raporunu İndir",
    "The Excel report could not be generated. Details: {error}": (
        "Excel raporu üretilemedi. Ayrıntı: {error}"
    ),
    "The PDF report could not be generated. Details: {error}": (
        "PDF raporu üretilemedi. Ayrıntı: {error}"
    ),
    "Report language": "Rapor dili",
    "Excel and PDF files are generated in English for both interface "
    "languages. Dashboard values and the interface follow the selected "
    "language.": (
        "Excel ve PDF dosyaları her iki arayüz dili için de İngilizce üretilir. "
        "Panel değerleri ve arayüz seçilen dili izler."
    ),
    # -- AI Analyst --------------------------------------------------------
    "AI interpretations of the deterministic calculation result. The engine "
    "owns every number; the model explains what those numbers mean.": (
        "Deterministik hesaplama sonucunun AI yorumları. Her sayı hesaplama "
        "motoruna aittir; model bu sayıların ne anlama geldiğini açıklar."
    ),
    "Decision support, not automated planning": (
        "Otomatik planlama değil, karar desteği"
    ),
    "AI-generated interpretations are decision-support suggestions and must be "
    "reviewed by a human.": (
        "AI tarafından üretilen yorumlar karar destek önerileridir ve bir insan "
        "tarafından incelenmelidir."
    ),
    "The AI context could not be prepared. Details: {error}": (
        "AI bağlamı hazırlanamadı. Ayrıntı: {error}"
    ),
    "Replenishment planning is not supported for a historical report date. The "
    "AI layer is told about this limitation and will not produce an order "
    "quantity.": (
        "Geçmiş dönem rapor tarihi için ikmal planlaması desteklenmez. AI "
        "katmanı bu kısıttan haberdardır ve sipariş miktarı üretmez."
    ),
    "AI unavailable": "AI kullanılamıyor",
    "No API key is configured, so only the deterministic values above are "
    "shown. Add AI_API_KEY to .streamlit/secrets.toml or set the "
    "DEPLOY_API_KEY environment variable to enable AI interpretation.": (
        "API anahtarı yapılandırılmadığı için yalnızca yukarıdaki deterministik "
        "değerler gösterilir. AI yorumunu etkinleştirmek için "
        ".streamlit/secrets.toml dosyasına AI_API_KEY ekleyin veya DEPLOY_API_KEY "
        "ortam değişkenini tanımlayın."
    ),
    "01 · Deterministic input": "01 · Deterministik girdi",
    "Supporting data": "Destekleyici veriler",
    "Every value below is produced by the calculation engine. These are the "
    "only numbers the AI is allowed to cite.": (
        "Aşağıdaki her değer hesaplama motoru tarafından üretilir. AI'ın "
        "başvurmasına izin verilen tek sayılar bunlardır."
    ),
    "Opening + IN − OUT up to the report date": (
        "Rapor tarihine kadar açılış + giriş − çıkış"
    ),
    "Current stock / average consumption": "Mevcut stok / ortalama tüketim",
    "Current stock + open orders": "Mevcut stok + açık siparişler",
    "Incoming supply, never added to current stock": (
        "Yoldaki tedarik, mevcut stoğa asla eklenmez"
    ),
    "Suggested Order": "Önerilen Sipariş",
    "Unit of measure": "Ölçü birimi",
    "Overdue orders": "Gecikmiş siparişler",
    "Movements in range": "Aralıktaki hareketler",
    "{count} in workbook": "çalışma kitabında {count}",
    "02 · AI interpretation": "02 · AI yorumu",
    "AI Inventory Overview": "AI Stok Genel Görünümü",
    "Generated from the values above. Nothing here changes the engine result.": (
        "Yukarıdaki değerlerden üretilir. Buradaki hiçbir şey hesaplama motoru "
        "sonucunu değiştirmez."
    ),
    "Regenerate": "Yeniden üret",
    "Generate AI overview": "AI genel görünümü üret",
    "Reusing the cached result for this dataset and report date.": (
        "Bu veri seti ve rapor tarihi için önbellekteki sonuç kullanılıyor."
    ),
    "One API request is sent for this dataset and report date, then cached.": (
        "Bu veri seti ve rapor tarihi için bir API isteği gönderilir ve "
        "ardından önbelleğe alınır."
    ),
    "The AI analysis failed unexpectedly. Details: {error}": (
        "AI analizi beklenmedik şekilde başarısız oldu. Ayrıntı: {error}"
    ),
    "Generated just now · {tokens} tokens": (
        "Az önce üretildi · {tokens} token"
    ),
    "Served from cache · no API request was sent.": (
        "Önbellekten sunuldu · API isteği gönderilmedi."
    ),
    "No AI interpretation yet": "Henüz AI yorumu yok",
    "The deterministic values above are complete on their own. Generate an AI "
    "overview to add narrative findings, risks and suggested actions.": (
        "Yukarıdaki deterministik değerler kendi başlarına tamdır. Anlatı "
        "bulguları, riskler ve önerilen eylemler eklemek için bir AI genel "
        "görünümü üretin."
    ),
    "Limitations": "Kısıtlar",
    "AI overview": "AI genel görünümü",
    "03 · AI interpretation": "03 · AI yorumu",
    "Key Findings": "Öne Çıkan Bulgular",
    "04 · AI interpretation": "04 · AI yorumu",
    "Inventory Risks": "Envanter Riskleri",
    "05 · AI interpretation": "05 · AI yorumu",
    "Recommended Actions": "Önerilen Eylemler",
    "Each suggestion carries its finding, supporting data, reason, confidence "
    "and limitation.": (
        "Her öneri; bulgusunu, destekleyici verisini, gerekçesini, güven "
        "düzeyini ve kısıtını birlikte taşır."
    ),
    "Finding": "Bulgu",
    "Reason": "Gerekçe",
    "Confidence": "Güven düzeyi",
    "Limitation": "Kısıt",
    "Not stated.": "Belirtilmedi.",
    "Low": "Düşük",
    "Medium": "Orta",
    "High": "Yüksek",
    "06 · AI interpretation": "06 · AI yorumu",
    "Consumption and replenishment": "Tüketim ve ikmal",
    "Two optional analyses. Each spends one API request and is cached "
    "afterwards.": (
        "İki isteğe bağlı analiz. Her biri bir API isteği harcar ve ardından "
        "önbelleğe alınır."
    ),
    "Regenerate consumption analysis": "Tüketim analizini yeniden üret",
    "Analyse consumption": "Tüketimi analiz et",
    "Regenerate replenishment explanation": (
        "İkmal açıklamasını yeniden üret"
    ),
    "Explain replenishment": "İkmali açıkla",
    "The consumption analysis failed. Details: {error}": (
        "Tüketim analizi başarısız oldu. Ayrıntı: {error}"
    ),
    "The replenishment explanation failed. Details: {error}": (
        "İkmal açıklaması başarısız oldu. Ayrıntı: {error}"
    ),
    "Consumption Insights": "Tüketim İçgörüleri",
    "Peak day": "En yüksek gün",
    "Lowest day": "En düşük gün",
    "Zero consumption": "Sıfır tüketim",
    "Patterns": "Örüntüler",
    "Replenishment Explanation": "İkmal Açıklaması",
    "Caveats": "Uyarılar",
    "07 · Ask the analyst": "07 · Analiste sorun",
    "Natural-language question": "Doğal dil sorusu",
    "Ask about the active dataset. Answers are cached per question, so asking "
    "the same thing twice costs nothing.": (
        "Etkin veri seti hakkında soru sorun. Yanıtlar soru başına önbelleğe "
        "alınır; aynı soruyu iki kez sormak ek maliyet doğurmaz."
    ),
    "Your question": "Sorunuz",
    "Why is replenishment not required?": "Neden yeniden sipariş gerekli değil?",
    "Suggested questions": "Önerilen sorular",
    "Ask the analyst": "Analiste sor",
    "The analyst could not answer. Details: {error}": (
        "Analist yanıt veremedi. Ayrıntı: {error}"
    ),
    "AI request failed": "AI isteği başarısız oldu",
    "{error} The deterministic values above are unaffected.": (
        "{error} Yukarıdaki deterministik değerler etkilenmedi."
    ),
    "Model {model}": "Model {model}",
    "Provider configured": "Sağlayıcı yapılandırıldı",
    "Provider not configured": "Sağlayıcı yapılandırılmadı",
    "Context {fingerprint}": "Bağlam {fingerprint}",
    "Untrusted text flagged": "Güvenilmeyen metin işaretlendi",
    "AI interpretations are generated in English regardless of the interface "
    "language.": (
        "AI yorumları, arayüz dilinden bağımsız olarak İngilizce üretilir."
    ),
    # -- Validation --------------------------------------------------------
    "{count} issues found in {filename}": (
        "{filename} dosyasında {count} sorun bulundu"
    ),
    "{count} issue found in {filename}": (
        "{filename} dosyasında {count} sorun bulundu"
    ),
    "The workbook was not loaded. Fix the items below and upload the file "
    "again.": (
        "Çalışma kitabı yüklenmedi. Aşağıdaki maddeleri düzeltip dosyayı "
        "yeniden yükleyin."
    ),
    "Worksheets found in this file: {sheets}": (
        "Bu dosyada bulunan çalışma sayfaları: {sheets}"
    ),
    "Workbook validated successfully": "Çalışma kitabı başarıyla doğrulandı",
    "{filename} passed every validation rule.": (
        "{filename} tüm doğrulama kurallarını geçti."
    ),
    "Warnings ({count})": "Uyarılar ({count})",
    "Workbook loaded with {count} warnings": (
        "Çalışma kitabı {count} uyarı ile yüklendi"
    ),
    "Workbook loaded with {count} warning": (
        "Çalışma kitabı {count} uyarı ile yüklendi"
    ),
    "The dataset is usable, but review the notes below.": (
        "Veri seti kullanılabilir, ancak aşağıdaki notları gözden geçirin."
    ),
    "Review warnings": "Uyarıları inceleyin",
    "Severity": "Önem",
    "Error": "Hata",
    "Warning": "Uyarı",
    "Sheet": "Sayfa",
    "Workbook": "Çalışma kitabı",
    "Excel Row": "Excel Satırı",
    "Column": "Kolon",
    "Issue": "Sorun",
    "Excel Row refers to the row number in the original worksheet.": (
        "Excel Satırı, orijinal çalışma sayfasındaki satır numarasını belirtir."
    ),
    # -- Validation engine messages ---------------------------------------
    "The workbook does not contain any worksheets.": (
        "Çalışma kitabı hiçbir çalışma sayfası içermiyor."
    ),
    "Required worksheet '{sheet}' is missing.": (
        "Gerekli '{sheet}' çalışma sayfası eksik."
    ),
    "Missing required column(s): {columns}. Keep the template column names "
    "unchanged.": (
        "Eksik zorunlu kolon(lar): {columns}. Şablon kolon adlarını "
        "değiştirmeyin."
    ),
    "Extra column(s) will be ignored: {columns}": (
        "Fazla kolon(lar) yok sayılacak: {columns}"
    ),
    "Product Master must contain exactly one product row. No product data was "
    "found.": (
        "Ürün Ana Verisi tam olarak bir ürün satırı içermelidir. Ürün verisi "
        "bulunamadı."
    ),
    "V1 supports a single product, but {count} product rows were found (Excel "
    "rows: {rows}). Keep exactly one row.": (
        "V1 tek ürün destekler, ancak {count} ürün satırı bulundu (Excel "
        "satırları: {rows}). Tam olarak bir satır bırakın."
    ),
    "Product Code is required.": "Ürün Kodu zorunludur.",
    "Product Name is required.": "Ürün Adı zorunludur.",
    "Unit is required (for example: pcs, kg, m).": (
        "Birim zorunludur (örneğin: adet, kg, m)."
    ),
    "Opening Stock must be a whole number of 0 or greater.": (
        "Açılış Stoğu 0 veya daha büyük bir tam sayı olmalıdır."
    ),
    "Opening Stock Date is missing or invalid. Use a valid Excel date (for "
    "example 2026-10-01).": (
        "Açılış Stok Tarihi eksik veya geçersiz. Geçerli bir Excel tarihi "
        "kullanın (örneğin 2026-10-01)."
    ),
    "Safety Stock must be a whole number of 0 or greater.": (
        "Güvenlik Stoğu 0 veya daha büyük bir tam sayı olmalıdır."
    ),
    "Lead Time Days must be a whole number of 0 or greater.": (
        "Tedarik Süresi (Gün) 0 veya daha büyük bir tam sayı olmalıdır."
    ),
    "Target Coverage Days must be a whole number greater than 0.": (
        "Hedef Kapsam (Gün) 0'dan büyük bir tam sayı olmalıdır."
    ),
    "Product Code must be unique. Duplicate value found in Excel rows: "
    "{rows}.": (
        "Ürün Kodu benzersiz olmalıdır. Excel satırlarında tekrarlanan değer "
        "bulundu: {rows}."
    ),
    "No stock movements were found. The workbook is valid, but analysis will "
    "be limited without movement history.": (
        "Hiç stok hareketi bulunamadı. Çalışma kitabı geçerli, ancak hareket "
        "geçmişi olmadan analiz sınırlı kalır."
    ),
    "Date is missing or invalid. Use a valid Excel date (for example "
    "2026-10-03).": (
        "Tarih eksik veya geçersiz. Geçerli bir Excel tarihi kullanın (örneğin "
        "2026-10-03)."
    ),
    "Movement date {movement_date} is before the Opening Stock Date "
    "{opening_date}. Movements cannot predate the opening balance.": (
        "Hareket tarihi {movement_date}, Açılış Stok Tarihi {opening_date} "
        "tarihinden önce. Hareketler açılış bakiyesinden önce olamaz."
    ),
    "Transaction Type must be IN or OUT. Received '{value}'.": (
        "Hareket Türü IN veya OUT olmalıdır. Alınan değer: '{value}'."
    ),
    "blank": "boş",
    "Quantity must be a positive whole number.": (
        "Miktar pozitif bir tam sayı olmalıdır."
    ),
    "No open orders were found. The workbook is valid, but incoming supply "
    "will not be included in later planning.": (
        "Hiç açık sipariş bulunamadı. Çalışma kitabı geçerli, ancak yoldaki "
        "tedarik sonraki planlamaya dahil edilmez."
    ),
    "Order No is required.": "Sipariş No zorunludur.",
    "Order Quantity must be a positive whole number.": (
        "Sipariş Miktarı pozitif bir tam sayı olmalıdır."
    ),
    "Expected Delivery Date is missing or invalid. Use a valid Excel date.": (
        "Beklenen Teslim Tarihi eksik veya geçersiz. Geçerli bir Excel tarihi "
        "kullanın."
    ),
    "Order No must be unique. Duplicate value found in Excel rows: {rows}.": (
        "Sipariş No benzersiz olmalıdır. Excel satırlarında tekrarlanan değer "
        "bulundu: {rows}."
    ),
    # -- Calculation notes -------------------------------------------------
    "Historical reports do not include current open orders and do not produce "
    "order suggestions. Replenishment planning is supported only for the "
    "current report date.": (
        "Geçmiş dönem raporları mevcut açık siparişleri dahil etmez ve sipariş "
        "önerisi üretmez. İkmal planlaması yalnızca güncel rapor tarihi için "
        "desteklenir."
    ),
    # -- Application-level errors -----------------------------------------
    "The active dataset could not be calculated. Adjust the report date or "
    "reload the workbook. Details: {error}": (
        "Etkin veri seti hesaplanamadı. Rapor tarihini değiştirin veya çalışma "
        "kitabını yeniden yükleyin. Ayrıntı: {error}"
    ),
    "Something went wrong while rendering this screen. Reload the page or "
    "clear the workspace from the sidebar and try again.": (
        "Bu ekran oluşturulurken bir sorun oluştu. Sayfayı yenileyin veya kenar "
        "çubuğundan çalışma alanını temizleyip tekrar deneyin."
    ),
    # -- Chart chrome ------------------------------------------------------
    "Units": "Birim",
    "Units consumed": "Tüketilen birim",
    "Stock balance": "Stok bakiyesi",
    "Daily consumption": "Günlük tüketim",
    "Weekly consumption": "Haftalık tüketim",
    "No OUT movements in this consumption window": (
        "Bu tüketim penceresinde çıkış hareketi yok"
    ),
    "No consumption recorded in these weeks": (
        "Bu haftalarda tüketim kaydı yok"
    ),
    "Safety stock {value}": "Güvenlik stoğu {value}",
    "Reorder point {value}": "Yeniden sipariş noktası {value}",
    "Current stock {value}": "Mevcut stok {value}",
    "Balance: {value} units": "Bakiye: {value} birim",
    "Current stock<br>%{x|%d %b %Y}<br>%{y:,.0f} units": (
        "Mevcut stok<br>%{x|%d.%m.%Y}<br>%{y:,.0f} birim"
    ),
    "Week of %{x|%d %b %Y}<br>%{y:,.0f} units": (
        "%{x|%d.%m.%Y} haftası<br>%{y:,.0f} birim"
    ),
    "%{x|%d %b %Y}<br>%{y:,.0f} units consumed": (
        "%{x|%d.%m.%Y}<br>%{y:,.0f} birim tüketildi"
    ),
    "%{x|%d %b %Y}<br>Balance: %{y:,.0f} units": (
        "%{x|%d.%m.%Y}<br>Bakiye: %{y:,.0f} birim"
    ),
    "%{x|%d %b %Y}<br>%{y:,.0f} units": (
        "%{x|%d.%m.%Y}<br>%{y:,.0f} birim"
    ),
    # -- Replenishment and stock analysis additions -----------------------
    "Target stock": "Hedef stok",
    "{days} calendar days": "{days} takvim günü",
    "{days} days": "{days} gün",
    "Not evaluated for historical reports": (
        "Geçmiş dönem raporları için değerlendirilmez"
    ),
    "Lowest running balance: {balance} {unit}. The planning values below use "
    "the unclamped current stock.": (
        "En düşük bakiye: {balance} {unit}. Aşağıdaki planlama değerleri "
        "sıfıra sabitlenmemiş mevcut stoğu kullanır."
    ),
    "%{y}<br>%{x:,.0f} units": "%{y}<br>%{x:,.0f} birim",
    "units": "birim",
    "unit": "birim",
    # -- Welcome headline and remaining section helpers --------------------
    "Inventory Intelligence": "Inventory Intelligence",
    "Demo Data": "Demo Verisi",
    "A synthetic dataset you can explore safely": (
        "Güvenle inceleyebileceğiniz sentetik bir veri seti"
    ),
    "The bundled demo workbook is generated for demonstration only. It is not "
    "real company data and it is never mixed with your own uploads: loading the "
    "demo replaces any active upload, and uploading a file replaces the demo.": (
        "Paketle gelen demo çalışma kitabı yalnızca gösterim amacıyla "
        "üretilmiştir. Gerçek şirket verisi değildir ve kendi yüklediğiniz "
        "dosyalarla asla karışmaz: demoyu yüklemek etkin yüklemeyi, bir dosya "
        "yüklemek de demoyu değiştirir."
    ),
    "Version and release state": "Sürüm ve yayın durumu",
    "What the validator enforces": "Doğrulayıcının uyguladığı kurallar",
    # -- Quick Start and demo data -----------------------------------------
    "Quick Start & Demo Data": "Hızlı Başlangıç ve Örnek Veri",
    "Try the app and the AI without preparing a file": (
        "Dosya hazırlamadan uygulamayı ve AI'yı deneyin"
    ),
    "Load a realistic dataset straight into the workspace, or download a "
    "workbook to inspect and adapt. Nothing here touches your own files.": (
        "Gerçekçi bir veri setini doğrudan çalışma alanına yükleyin veya "
        "incelemek ve uyarlamak için bir çalışma kitabı indirin. Buradaki "
        "hiçbir işlem kendi dosyalarınıza dokunmaz."
    ),
    "Run the AI demo": "AI demosunu çalıştır",
    "Load a populated scenario and open the dashboard immediately. No "
    "download, no upload.": (
        "Doldurulmuş bir senaryoyu yükleyin ve paneli hemen açın. İndirme yok, "
        "yükleme yok."
    ),
    "Demo scenario": "Demo senaryosu",
    "🚀 Run the AI demo now": "🚀 AI demosunu hemen çalıştır",
    "Generates the selected scenario, validates it and opens the Overview "
    "Dashboard.": (
        "Seçilen senaryoyu üretir, doğrular ve Genel Bakış Panelini açar."
    ),
    "Blank data template": "Boş veri şablonu",
    "Start from a workbook with the exact required sheets and column headers, "
    "plus a Read Me guide.": (
        "Tam olarak gerekli sayfaları ve kolon başlıklarını içeren, ayrıca bir "
        "Beni Oku kılavuzu bulunan bir çalışma kitabıyla başlayın."
    ),
    "📥 Download blank template": "📥 Boş şablonu indir",
    "Empty sheets with the exact headers, a Read Me guide and a dropdown for "
    "Transaction Type.": (
        "Tam başlıklara sahip boş sayfalar, bir Beni Oku kılavuzu ve Hareket "
        "Türü için açılır liste."
    ),
    "Populated sample file": "Doldurulmuş örnek dosya",
    "Download the same dataset as an Excel file to inspect it, change it and "
    "upload it again.": (
        "Aynı veri setini Excel dosyası olarak indirip inceleyin, değiştirin ve "
        "yeniden yükleyin."
    ),
    "File to download": "İndirilecek dosya",
    "📊 Download sample data": "📊 Örnek veriyi indir",
    "The downloaded file validates against the same rules as your own upload.": (
        "İndirilen dosya, kendi yüklemenizle aynı kurallara göre doğrulanır."
    ),
    "Each scenario is built to trigger a different set of warnings.": (
        "Her senaryo farklı bir uyarı kümesini tetikleyecek şekilde "
        "oluşturulmuştur."
    ),
    "The blank template could not be generated.": (
        "Boş şablon oluşturulamadı."
    ),
    "The sample workbook could not be generated.": (
        "Örnek çalışma kitabı oluşturulamadı."
    ),
    "Dismiss": "Kapat",
    "Stockout risk": "Stok tükenme riski",
    "Dead stock": "Ölü stok",
    "Fast mover": "Hızlı devirli ürün",
    "Demand ramps up for a seasonal campaign while supply stays flat. Stock is "
    "far below safety stock, the position is under the reorder point and one "
    "purchase order is already overdue.": (
        "Sezon kampanyası için talep artarken tedarik sabit kalıyor. Stok "
        "güvenlik stoğunun çok altında, envanter pozisyonu yeniden sipariş "
        "noktasının altında ve bir satın alma siparişi zaten gecikmiş durumda."
    ),
    "A legacy part with almost no demand for two months. Several thousand "
    "units of working capital are tied up and days of supply runs into the "
    "thousands.": (
        "İki aydır neredeyse hiç talep görmeyen eski bir parça. Binlerce birim "
        "işletme sermayesi bağlı ve stokta kalma süresi binlerce güne çıkıyor."
    ),
    "A bulk project shipment is picked before its confirming receipt is "
    "posted. The running balance drops below zero and recovers, which exercises "
    "the negative stock alert and the data-quality caveat.": (
        "Toplu bir proje sevkiyatı, giriş kaydı işlenmeden önce toplanıyor. "
        "Yürüyen bakiye sıfırın altına düşüp yeniden toparlanıyor; bu da negatif "
        "stok uyarısını ve veri kalitesi uyarısını tetikliyor."
    ),
    "A high-velocity component with steady daily consumption, healthy cover "
    "above the reorder point and one scheduled delivery. The contrast to dead "
    "stock is what ABC classification would care about.": (
        "Günlük tüketimi istikrarlı, yeniden sipariş noktasının üzerinde "
        "sağlıklı bir stoğa ve planlanmış bir teslimata sahip hızlı devirli bir "
        "bileşen. Ölü stokla oluşturduğu karşıtlık, ABC sınıflandırmasının "
        "önemsediği ayrımdır."
    ),
    "The sample set ships one product per workbook, because V1 plans a single "
    "SKU at a time. The four scenarios contrast turnover patterns: stockout "
    "risk, dead stock, a negative balance and a fast mover.": (
        "V1 aynı anda tek SKU planladığı için örnek set her çalışma kitabında "
        "tek ürün içerir. Dört senaryo devir hızı desenlerini karşılaştırır: "
        "stok tükenme riski, ölü stok, negatif bakiye ve hızlı devir."
    ),
    "Every AI feature is exercised: the inventory overview, findings, risks "
    "and recommended actions, the consumption pattern analysis, the "
    "replenishment explanation and the natural-language analyst.": (
        "Her AI özelliği denenebilir: envanter özeti, bulgular, riskler ve "
        "önerilen eylemler, tüketim deseni analizi, ikmal açıklaması ve doğal "
        "dil analisti."
    ),
    "The deliberate outliers are real, not decoration: an overdue purchase "
    "order, a bulk shipment picked before its receipt, a seasonal demand "
    "surge and roughly 4,500 units of idle capital.": (
        "Kasıtlı uç değerler süs değil, gerçektir: gecikmiş bir satın alma "
        "siparişi, girişi işlenmeden toplanan toplu bir sevkiyat, mevsimsel bir "
        "talep sıçraması ve yaklaşık 4.500 birim atıl sermaye."
    ),
    "'{filename}' could not be read as an Excel workbook. Make sure the file is "
    "a valid .xlsx file and is not password protected.": (
        "'{filename}' bir Excel çalışma kitabı olarak okunamadı. Dosyanın "
        "geçerli bir .xlsx dosyası olduğundan ve parola korumalı olmadığından "
        "emin olun."
    ),
}
