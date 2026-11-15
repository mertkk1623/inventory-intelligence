"""Global design system for Inventory Intelligence.

Streamlit is styled through a single CSS layer so every page and component
shares the same spacing, colour and typography rules.
"""

from __future__ import annotations

import streamlit as st

from utils.i18n import get_language

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
    --ii-navy: #14243A;
    --ii-navy-soft: #1C3049;
    --ii-primary: #2563EB;
    --ii-primary-dark: #1D4ED8;
    --ii-bg: #F3F5F8;
    --ii-surface: #FFFFFF;
    --ii-success: #16A36A;
    --ii-warning: #D97706;
    --ii-critical: #DC4444;
    --ii-text: #0F172A;
    --ii-muted: #64748B;
    --ii-border: #E4E9F0;
    --ii-radius: 14px;
}

.stApp {
    background: var(--ii-bg);
    color: var(--ii-text);
}

.stApp p, .stApp li, .stApp label, .stApp h1, .stApp h2,
.stApp h3, .stApp h4, .stApp h5, .stApp h6,
.stApp input, .stApp textarea, .stApp button, .stApp select {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

header[data-testid="stHeader"] {
    background: transparent;
}

#MainMenu, footer {
    visibility: hidden;
}

/* The toolbar itself must stay in the layout, because it holds Streamlit's
   only "Expand sidebar" control once the sidebar is collapsed. Hiding the
   whole toolbar locked the navigation away; only the surplus items are
   hidden here so the original chrome stays clean. */
[data-testid="stToolbarActions"],
[data-testid="stAppDeployButton"] {
    display: none;
}

.block-container {
    max-width: 1200px;
    padding-top: 2.2rem;
    padding-bottom: 4rem;
    padding-left: 2.4rem;
    padding-right: 2.4rem;
}

h1, h2, h3, h4 {
    color: var(--ii-text);
    letter-spacing: -0.025em;
}

/* The language-sync helper is a script-only iframe. Keep it from ever painting
   a border, background or scrollbar, whichever rendering path is available. */
iframe[data-testid="stIFrame"],
[data-testid="stAppIframeResizerAnchor"] {
    border: 0 !important;
    background: transparent !important;
    overflow: hidden !important;
}

/* ------------------------------------------------------------------ */
/* Sidebar                                                             */
/* ------------------------------------------------------------------ */

[data-testid="stSidebar"] {
    background: var(--ii-navy);
    border-right: 1px solid rgba(255, 255, 255, 0.04);
}

[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
    padding: 1.35rem 1.05rem 1.2rem;
}

[data-testid="stSidebar"] p,
[data-testid="stSidebar"] li,
[data-testid="stSidebar"] label {
    color: #DCE6F2;
}

[data-testid="stSidebar"] hr {
    border-color: rgba(255, 255, 255, 0.08);
}

.ii-brand {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 2px 4px 20px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    margin-bottom: 20px;
}

.ii-logo {
    width: 42px;
    height: 42px;
    flex: 0 0 42px;
    border-radius: 12px;
    background: linear-gradient(135deg, #3B82F6, #1D4ED8);
    color: #FFFFFF;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 8px 18px rgba(37, 99, 235, 0.35);
}

.ii-brand-name {
    font-size: 14.5px;
    font-weight: 700;
    color: #FFFFFF;
    line-height: 1.25;
}

.ii-brand-sub {
    margin-top: 3px;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    color: #8FA3BC;
}

.ii-side-label {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #7E93AC;
    padding: 0 10px;
    margin-bottom: 8px;
}

[data-testid="stSidebar"] [data-testid="stRadioGroup"] {
    width: 100%;
    gap: 4px;
}

[data-testid="stSidebar"] [data-testid="stRadioGroup"] > div {
    width: 100%;
}

[data-testid="stSidebar"] [data-testid="stRadioOption"] {
    display: block;
    width: 100%;
    margin: 0;
    padding: 9px 11px;
    border-radius: 8px;
    transition: background 0.15s ease;
}

[data-testid="stSidebar"] [data-testid="stRadioOption"]:hover {
    background: rgba(255, 255, 255, 0.06);
}

[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] {
    background: rgba(37, 99, 235, 0.22);
    box-shadow: inset 2px 0 0 #3B82F6;
}

[data-testid="stSidebar"] [data-testid="stRadioOption"] > div > div:first-child {
    display: none;
}

[data-testid="stSidebar"] [data-testid="stRadioOption"] p {
    font-size: 13px;
    font-weight: 500;
    color: #C9D6E6;
}

[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] p {
    color: #FFFFFF;
    font-weight: 600;
}

.ii-side-card {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 10px;
    padding: 13px 14px;
    margin-top: 18px;
}

.ii-side-card-label {
    font-size: 9.5px;
    font-weight: 700;
    letter-spacing: 0.13em;
    text-transform: uppercase;
    color: #8FA3BC;
    margin-bottom: 7px;
}

.ii-side-card-title {
    font-size: 12.5px;
    font-weight: 600;
    color: #FFFFFF;
    line-height: 1.35;
}

.ii-side-card-meta {
    font-size: 10.5px;
    line-height: 1.5;
    color: #93A7BF;
    margin-top: 4px;
}

.ii-side-card.muted {
    background: rgba(255, 255, 255, 0.03);
}

[data-testid="stSidebar"] .stButton > button {
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.12);
    color: #DCE6F2;
    min-height: 36px;
    font-size: 12px;
    margin-top: 10px;
}

[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255, 255, 255, 0.10);
    border-color: rgba(255, 255, 255, 0.22);
    color: #FFFFFF;
}

.ii-side-footer {
    margin-top: 26px;
    padding-top: 16px;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
    font-size: 10px;
    line-height: 1.65;
    color: #7288A1;
}

/* ------------------------------------------------------------------ */
/* Buttons                                                             */
/* ------------------------------------------------------------------ */

.stButton > button,
[data-testid="stDownloadButton"] > button {
    border-radius: 9px;
    font-weight: 600;
    font-size: 13px;
    min-height: 42px;
    padding: 0.5rem 1rem;
    transition: background 0.15s ease, border-color 0.15s ease,
        box-shadow 0.15s ease, transform 0.15s ease;
}

button[data-testid="stBaseButton-primary"],
.stButton > button[kind="primary"],
[data-testid="stDownloadButton"] > button[kind="primary"] {
    background: var(--ii-primary) !important;
    border: 1px solid var(--ii-primary) !important;
    color: #FFFFFF !important;
    box-shadow: 0 6px 16px rgba(37, 99, 235, 0.22);
}

button[data-testid="stBaseButton-primary"]:hover,
.stButton > button[kind="primary"]:hover,
[data-testid="stDownloadButton"] > button[kind="primary"]:hover {
    background: var(--ii-primary-dark) !important;
    border-color: var(--ii-primary-dark) !important;
    transform: translateY(-1px);
}

button[data-testid="stBaseButton-secondary"],
.stButton > button[kind="secondary"],
[data-testid="stDownloadButton"] > button[kind="secondary"] {
    background: var(--ii-surface) !important;
    border: 1px solid #D8E0EA !important;
    color: #1E293B !important;
}

button[data-testid="stBaseButton-secondary"]:hover,
.stButton > button[kind="secondary"]:hover,
[data-testid="stDownloadButton"] > button[kind="secondary"]:hover {
    border-color: #B9C7D8 !important;
    background: #F8FAFC !important;
}

/* ------------------------------------------------------------------ */
/* Cards and section headers                                           */
/* ------------------------------------------------------------------ */

div[data-testid="stVerticalBlock"]:has(.ii-action-icon):not(
        :has(div[data-testid="stVerticalBlock"])) {
    background: var(--ii-surface);
    border: 1px solid var(--ii-border) !important;
    border-radius: var(--ii-radius) !important;
    padding: 1.3rem 1.35rem 1.15rem !important;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    min-height: 320px;
}

.ii-section-head {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    gap: 1rem;
    margin: 2.5rem 0 1rem;
}

.ii-section-eyebrow {
    font-size: 10.5px;
    font-weight: 700;
    letter-spacing: 0.13em;
    text-transform: uppercase;
    color: var(--ii-primary);
    margin-bottom: 6px;
}

.ii-section-title {
    margin: 0;
    font-size: 23px;
    font-weight: 750;
    letter-spacing: -0.035em;
    color: var(--ii-text);
}

.ii-section-sub {
    margin: 7px 0 0;
    max-width: 700px;
    font-size: 13.5px;
    line-height: 1.6;
    color: var(--ii-muted);
}

/* ------------------------------------------------------------------ */
/* Hero                                                                */
/* ------------------------------------------------------------------ */

.ii-hero {
    position: relative;
    overflow: hidden;
    display: grid;
    grid-template-columns: minmax(0, 1.35fr) minmax(280px, 0.85fr);
    gap: 2.2rem;
    background: var(--ii-surface);
    border: 1px solid var(--ii-border);
    border-radius: 18px;
    padding: 2.5rem 2.6rem;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

.ii-hero::before {
    content: "";
    position: absolute;
    width: 460px;
    height: 460px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(37, 99, 235, 0.11), transparent 66%);
    top: -250px;
    right: -130px;
    pointer-events: none;
}

.ii-hero-copy {
    position: relative;
    z-index: 1;
}

.ii-eyebrow {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 6px 10px;
    border-radius: 999px;
    background: #EFF5FF;
    border: 1px solid #DCE8FF;
    color: var(--ii-primary);
    font-size: 10.5px;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
}

.ii-eyebrow .dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--ii-primary);
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.14);
}

.ii-hero h1 {
    max-width: 650px;
    margin: 18px 0 14px;
    font-size: 40px;
    line-height: 1.08;
    font-weight: 800;
    letter-spacing: -0.045em;
    color: #0B1729;
}

.ii-hero h1 .accent {
    color: var(--ii-primary);
}

.ii-hero p {
    max-width: 570px;
    margin: 0;
    font-size: 15px;
    line-height: 1.65;
    color: #5B6B80;
}

.ii-hero-sub {
    margin: 0 0 10px !important;
    font-size: 17px !important;
    font-weight: 650;
    line-height: 1.45 !important;
    color: #24344A !important;
}

.ii-hero-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 20px;
}

.ii-chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 10px;
    border-radius: 8px;
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    color: #334155;
    font-size: 11.5px;
    font-weight: 600;
}

.ii-chip svg {
    color: var(--ii-success);
}

.ii-hero-panel {
    position: relative;
    z-index: 1;
    align-self: center;
    background: var(--ii-navy);
    border-radius: 14px;
    padding: 18px;
    box-shadow: 0 18px 40px rgba(20, 36, 58, 0.22);
}

.ii-panel-title {
    margin-bottom: 13px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #8FA3BC;
}

.ii-file-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 9px 11px;
    margin-bottom: 7px;
    border-radius: 9px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.07);
}

.ii-file-row:last-child {
    margin-bottom: 0;
}

.ii-file-icon {
    width: 28px;
    height: 28px;
    flex: 0 0 28px;
    border-radius: 7px;
    background: rgba(37, 99, 235, 0.22);
    color: #7FB0FF;
    display: flex;
    align-items: center;
    justify-content: center;
}

.ii-file-name {
    font-size: 12px;
    font-weight: 600;
    color: #E7EDF6;
}

.ii-file-meta {
    margin-top: 2px;
    font-size: 10px;
    color: #8FA3BC;
}

.ii-file-check {
    margin-left: auto;
    color: #4ADE80;
}

/* ------------------------------------------------------------------ */
/* How it works                                                        */
/* ------------------------------------------------------------------ */

.ii-steps {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
}

.ii-step {
    background: var(--ii-surface);
    border: 1px solid var(--ii-border);
    border-radius: 12px;
    padding: 15px 15px 16px;
}

.ii-step-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.ii-step-num {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 27px;
    height: 22px;
    padding: 0 7px;
    border-radius: 6px;
    background: #EFF5FF;
    color: var(--ii-primary);
    font-size: 10.5px;
    font-weight: 800;
    letter-spacing: 0.04em;
}

.ii-step-icon {
    color: #94A3B8;
}

.ii-step h4 {
    margin: 13px 0 6px;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: -0.01em;
    color: var(--ii-text);
}

.ii-step p {
    margin: 0;
    font-size: 11.5px;
    line-height: 1.55;
    color: var(--ii-muted);
}

/* ------------------------------------------------------------------ */
/* Action cards                                                        */
/* ------------------------------------------------------------------ */

.ii-action-icon {
    width: 38px;
    height: 38px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 12px;
}

.ii-action-icon.blue {
    background: #EFF5FF;
    color: var(--ii-primary);
}

.ii-action-icon.green {
    background: #ECFDF5;
    color: var(--ii-success);
}

.ii-action-icon.amber {
    background: #FFF7ED;
    color: var(--ii-warning);
}

.ii-action-title {
    margin: 0 0 6px;
    font-size: 14.5px;
    font-weight: 700;
    color: var(--ii-text);
}

.ii-action-text {
    min-height: 58px;
    margin: 0 0 10px;
    font-size: 12px;
    line-height: 1.55;
    color: var(--ii-muted);
}

/* ------------------------------------------------------------------ */
/* Reports                                                             */
/* ------------------------------------------------------------------ */

.ii-report-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 18px;
    margin-bottom: 6px;
}

.ii-report-card {
    display: flex;
    flex-direction: column;
    background: var(--ii-surface);
    border: 1px solid var(--ii-border);
    border-radius: var(--ii-radius);
    padding: 20px 22px 18px;
}

.ii-report-top {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 12px;
}

.ii-report-icon {
    width: 40px;
    height: 40px;
    flex: 0 0 40px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #EFF5FF;
    color: var(--ii-primary);
}

.ii-report-icon.pdf {
    background: #FDF2F2;
    color: #C0392B;
}

.ii-report-kicker {
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    color: #94A3B8;
}

.ii-report-name {
    margin: 2px 0 0;
    font-size: 16px;
    font-weight: 750;
    letter-spacing: -0.02em;
    color: var(--ii-text);
}

.ii-report-ext {
    padding: 3px 8px;
    border-radius: 5px;
    background: #F1F5F9;
    color: #475569;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.04em;
}

.ii-report-desc {
    margin: 0 0 14px;
    font-size: 12px;
    line-height: 1.6;
    color: var(--ii-muted);
}

.ii-report-list-label {
    margin: 0 0 8px;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    color: #94A3B8;
}

.ii-report-items {
    margin: 0 0 4px;
    padding: 0;
    list-style: none;
}

.ii-report-items li {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: 5px 0;
    font-size: 11.5px;
    line-height: 1.5;
    color: #475569;
    border-bottom: 1px solid #F1F5F9;
}

.ii-report-items li:last-child {
    border-bottom: none;
}

.ii-report-items .num {
    flex: 0 0 16px;
    font-size: 10px;
    font-weight: 700;
    color: var(--ii-primary);
    padding-top: 1px;
}

.ii-report-items .tick {
    flex: 0 0 auto;
    color: var(--ii-success);
    display: flex;
    padding-top: 2px;
}

.ii-report-items strong {
    color: var(--ii-text);
    font-weight: 650;
}

.ii-report-foot {
    margin-top: auto;
    padding-top: 14px;
    font-size: 10.5px;
    line-height: 1.5;
    color: #94A3B8;
}

.ii-report-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin: 0 0 16px;
}

.ii-report-meta span {
    padding: 4px 9px;
    border-radius: 6px;
    background: #F8FAFC;
    border: 1px solid #E8EDF3;
    font-size: 10.5px;
    font-weight: 600;
    color: #475569;
}

.ii-report-note {
    padding: 14px 16px;
    border-radius: 10px;
    background: #FFF8EA;
    border-left: 3px solid var(--ii-warning);
    font-size: 11.5px;
    line-height: 1.6;
    color: #7A5314;
}

/* ------------------------------------------------------------------ */
/* Excel requirements                                                  */
/* ------------------------------------------------------------------ */

.ii-sheet-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 14px;
}

.ii-sheet-card {
    background: var(--ii-surface);
    border: 1px solid var(--ii-border);
    border-radius: 12px;
    padding: 17px 18px;
}

.ii-sheet-head {
    display: flex;
    align-items: center;
    gap: 9px;
    margin-bottom: 7px;
}

.ii-sheet-icon {
    color: var(--ii-primary);
    display: flex;
}

.ii-sheet-name {
    font-size: 13.5px;
    font-weight: 700;
    color: var(--ii-text);
}

.ii-sheet-desc {
    min-height: 56px;
    margin: 0 0 12px;
    font-size: 11.5px;
    line-height: 1.55;
    color: var(--ii-muted);
}

.ii-col-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
}

.ii-col-tag {
    padding: 3px 7px;
    border-radius: 5px;
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    color: #475569;
    font-size: 10px;
    font-weight: 600;
}

.ii-rules {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px 26px;
    margin-top: 14px;
    padding: 18px 20px;
    background: var(--ii-surface);
    border: 1px solid var(--ii-border);
    border-radius: 12px;
}

.ii-rule {
    display: flex;
    align-items: flex-start;
    gap: 9px;
    font-size: 12px;
    line-height: 1.55;
    color: #475569;
}

.ii-rule svg {
    flex: 0 0 15px;
    margin-top: 2px;
    color: var(--ii-success);
}

.ii-privacy {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 18px;
    padding: 11px 14px;
    border-radius: 9px;
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    color: #64748B;
    font-size: 11px;
    line-height: 1.5;
}

.ii-privacy svg {
    flex: 0 0 15px;
    color: #64748B;
}

/* ------------------------------------------------------------------ */
/* Roadmap                                                             */
/* ------------------------------------------------------------------ */

.ii-road {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 16px;
    margin-top: 16px;
}

.ii-road-col {
    background: var(--ii-surface);
    border: 1px solid var(--ii-border);
    border-radius: 12px;
    padding: 16px 18px 14px;
}

.ii-road-head {
    display: flex;
    align-items: center;
    gap: 8px;
    padding-bottom: 11px;
    margin-bottom: 4px;
    border-bottom: 1px solid #EEF2F7;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    color: var(--ii-muted);
}

.ii-road-version {
    display: inline-flex;
    align-items: center;
    height: 20px;
    padding: 0 8px;
    border-radius: 6px;
    background: #EFF5FF;
    color: var(--ii-primary);
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 0.04em;
}

.ii-road-item {
    display: flex;
    align-items: center;
    gap: 9px;
    padding: 8px 0;
    font-size: 12.5px;
    line-height: 1.45;
    color: #334155;
}

.ii-road-item + .ii-road-item {
    border-top: 1px solid #F4F7FB;
}

.ii-road-item.planned {
    color: #64748B;
}

.ii-road-mark {
    display: flex;
    flex: 0 0 17px;
    align-items: center;
    justify-content: center;
    width: 17px;
    height: 17px;
    border-radius: 50%;
    background: #ECFDF5;
    color: var(--ii-success);
}

.ii-road-item.planned .ii-road-mark {
    background: #F1F5F9;
    color: #94A3B8;
}

.ii-road-tag {
    margin-left: auto;
    padding: 2px 7px;
    border-radius: 5px;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    white-space: nowrap;
}

.ii-road-tag.done {
    background: #ECFDF5;
    border: 1px solid #C7F0DE;
    color: #15803D;
}

.ii-road-tag.planned {
    background: #F1F5F9;
    border: 1px solid #E2E8F0;
    color: #64748B;
}

.ii-road-note {
    margin-top: 12px;
    padding: 11px 14px;
    border-radius: 9px;
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    color: #64748B;
    font-size: 11px;
    line-height: 1.55;
}

/* ------------------------------------------------------------------ */
/* Version / status card                                               */
/* ------------------------------------------------------------------ */

.ii-status-card {
    margin-top: 16px;
    background: var(--ii-surface);
    border: 1px solid var(--ii-border);
    border-radius: 12px;
    padding: 16px 18px;
}

.ii-status-head {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 10px;
    margin-bottom: 4px;
    font-size: 12.5px;
    font-weight: 700;
    color: var(--ii-text);
}

.ii-status-pill {
    display: inline-flex;
    align-items: center;
    height: 22px;
    padding: 0 10px;
    border-radius: 999px;
    background: #EFF5FF;
    border: 1px solid #BFDBFE;
    color: var(--ii-primary-dark);
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}

.ii-status-note {
    margin-top: 12px;
    padding-top: 11px;
    border-top: 1px solid #EEF2F7;
    color: #94A3B8;
    font-size: 10.5px;
    line-height: 1.5;
}

/* ------------------------------------------------------------------ */
/* Banners                                                             */
/* ------------------------------------------------------------------ */

.ii-banner {
    display: flex;
    align-items: flex-start;
    gap: 11px;
    margin: 10px 0 16px;
    padding: 13px 15px;
    border-radius: 10px;
    border: 1px solid;
}

.ii-banner-icon {
    flex: 0 0 18px;
    margin-top: 1px;
}

.ii-banner-title {
    font-size: 12.5px;
    font-weight: 700;
    line-height: 1.4;
}

.ii-banner-text {
    margin-top: 2px;
    font-size: 11.5px;
    line-height: 1.5;
    opacity: 0.9;
}

.ii-banner.success {
    background: #F0FDF7;
    border-color: #BBF7D0;
    color: #166534;
}

.ii-banner.success .ii-banner-icon {
    color: var(--ii-success);
}

.ii-banner.warning {
    background: #FFFBEB;
    border-color: #FDE68A;
    color: #92400E;
}

.ii-banner.warning .ii-banner-icon {
    color: var(--ii-warning);
}

.ii-banner.error {
    background: #FEF2F2;
    border-color: #FECACA;
    color: #991B1B;
}

.ii-banner.error .ii-banner-icon {
    color: var(--ii-critical);
}

.ii-banner.info {
    background: #EFF6FF;
    border-color: #BFDBFE;
    color: #1E40AF;
}

.ii-banner.info .ii-banner-icon {
    color: var(--ii-primary);
}

/* ------------------------------------------------------------------ */
/* Page header and overview                                            */
/* ------------------------------------------------------------------ */

.ii-page-head {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 1.5rem;
    margin-bottom: 18px;
}

.ii-page-eyebrow {
    margin-bottom: 6px;
    font-size: 10.5px;
    font-weight: 700;
    letter-spacing: 0.13em;
    text-transform: uppercase;
    color: var(--ii-primary);
}

.ii-page-title {
    margin: 0;
    font-size: 30px;
    font-weight: 800;
    letter-spacing: -0.04em;
    color: var(--ii-text);
}

.ii-page-sub {
    margin: 7px 0 0;
    font-size: 13.5px;
    line-height: 1.55;
    color: var(--ii-muted);
}

.ii-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 5px 9px;
    border-radius: 999px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    white-space: nowrap;
}

.ii-badge.demo {
    background: #FFF7ED;
    border: 1px solid #FDE68A;
    color: #B45309;
}

.ii-badge.upload {
    background: #EFF6FF;
    border: 1px solid #BFDBFE;
    color: #1D4ED8;
}

.ii-metrics {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 14px;
    margin: 18px 0 8px;
}

.ii-metric {
    background: var(--ii-surface);
    border: 1px solid var(--ii-border);
    border-radius: 12px;
    padding: 15px 17px;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
}

.ii-metric-label {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    color: var(--ii-muted);
}

.ii-metric-value {
    margin-top: 7px;
    font-size: 23px;
    font-weight: 800;
    letter-spacing: -0.035em;
    color: var(--ii-text);
    line-height: 1.15;
}

.ii-metric-value.small {
    font-size: 15px;
    line-height: 1.35;
}

.ii-metric-meta {
    margin-top: 4px;
    font-size: 10.5px;
    line-height: 1.4;
    color: #94A3B8;
}

.ii-detail-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 14px;
    margin: 8px 0 6px;
}

.ii-detail {
    padding: 12px 14px;
    border-radius: 9px;
    background: #F8FAFC;
    border: 1px solid #E8EDF3;
}

.ii-detail-label {
    font-size: 9.5px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #94A3B8;
}

.ii-detail-value {
    margin-top: 4px;
    font-size: 13px;
    font-weight: 650;
    color: #334155;
}

/* ------------------------------------------------------------------ */
/* Analytics                                                           */
/* ------------------------------------------------------------------ */

.ii-page-asof {
    margin-top: 8px;
    display: inline-flex;
    align-items: center;
    padding: 4px 9px;
    border-radius: 999px;
    background: #EFF6FF;
    border: 1px solid #BFDBFE;
    color: #1D4ED8;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}

.ii-metrics.cols-2 {
    grid-template-columns: repeat(2, minmax(0, 1fr));
}

.ii-metric.tone-critical .ii-metric-value {
    color: var(--ii-critical);
}

.ii-metric.tone-warning .ii-metric-value {
    color: var(--ii-warning);
}

.ii-metric.tone-success .ii-metric-value {
    color: var(--ii-success);
}

.ii-metric.tone-muted .ii-metric-value {
    color: #64748B;
}

.ii-card-head {
    margin: 2px 0 4px;
}

.ii-card-title {
    font-size: 14px;
    font-weight: 700;
    letter-spacing: -0.015em;
    color: var(--ii-text);
}

.ii-card-sub {
    margin-top: 2px;
    font-size: 11px;
    line-height: 1.45;
    color: var(--ii-muted);
}

.ii-empty {
    padding: 26px 18px;
    text-align: center;
    border: 1px dashed #D7DFEA;
    border-radius: 10px;
    background: #F8FAFC;
}

.ii-empty-title {
    font-size: 12.5px;
    font-weight: 700;
    color: #334155;
}

.ii-empty-text {
    margin-top: 4px;
    font-size: 11.5px;
    line-height: 1.5;
    color: #94A3B8;
}

/* Card surface for bordered Streamlit containers that start with a card header. */
[data-testid="stVerticalBlock"]:has(
        > [data-testid="stElementContainer"]:first-child .ii-card-head) {
    background: var(--ii-surface);
    border: 1px solid var(--ii-border);
    border-radius: 14px;
    padding: 15px 17px 13px;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
}

[data-testid="stPlotlyChart"] {
    margin-top: 2px;
}

[data-testid="stSidebar"] [data-testid="stDateInput"] {
    padding: 0 2px;
}

[data-testid="stSidebar"] [data-testid="stDateInput"] label p {
    color: #8FA3BC;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.13em;
    text-transform: uppercase;
}

[data-testid="stSidebar"] [data-testid="stDateInput"] div[data-baseweb="input"] {
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.14);
    border-radius: 8px;
}

[data-testid="stSidebar"] [data-testid="stDateInput"] input {
    color: #FFFFFF;
    font-size: 12px;
}

[data-testid="stSidebar"] [data-testid="stDateInput"] svg {
    fill: #93A7BF;
}

[data-testid="stSidebar"] [data-testid="stDateInput"] [data-testid="stWidgetLabel"] {
    margin-bottom: 2px;
}

.ii-side-date-note {
    padding: 5px 4px 0;
    font-size: 10px;
    line-height: 1.45;
    color: #8FA3BC;
}

/* ------------------------------------------------------------------ */
/* AI Analyst                                                          */
/* ------------------------------------------------------------------ */

.ii-ai-card {
    background: var(--ii-surface);
    border: 1px solid var(--ii-border);
    border-left: 3px solid var(--ii-primary);
    border-radius: var(--ii-radius);
    padding: 18px 20px;
    margin: 4px 0 14px;
}

.ii-ai-card-kicker {
    display: flex;
    align-items: center;
    gap: 7px;
    font-size: 10.5px;
    font-weight: 700;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    color: var(--ii-primary);
    margin-bottom: 10px;
}

.ii-ai-card-kicker svg {
    opacity: 0.85;
}

.ii-ai-prose {
    margin: 0;
    font-size: 13.5px;
    line-height: 1.65;
    color: var(--ii-text);
}

.ii-ai-decision {
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--ii-navy);
    margin-bottom: 8px;
}

.ii-ai-limits {
    margin-top: 14px;
    padding-top: 12px;
    border-top: 1px dashed var(--ii-border);
    font-size: 11.5px;
    color: var(--ii-muted);
    line-height: 1.6;
}

.ii-ai-limits strong {
    display: block;
    font-size: 10px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #94A3B8;
    margin-bottom: 5px;
}

.ii-ai-limits ul {
    margin: 0;
    padding-left: 16px;
}

.ii-ai-limits li {
    margin-bottom: 3px;
}

.ii-ai-note {
    margin-top: 8px;
    font-size: 12px;
    line-height: 1.6;
    color: var(--ii-text);
}

.ii-ai-note span {
    display: inline-block;
    min-width: 108px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #94A3B8;
}

.ii-ai-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin-bottom: 14px;
}

.ii-ai-finding,
.ii-ai-risk,
.ii-ai-action {
    background: var(--ii-surface);
    border: 1px solid var(--ii-border);
    border-radius: 12px;
    padding: 14px 16px;
}

.ii-ai-finding-title,
.ii-ai-risk-title,
.ii-ai-action-title {
    font-size: 12.5px;
    font-weight: 700;
    color: var(--ii-text);
}

.ii-ai-finding-text,
.ii-ai-risk-text {
    margin-top: 5px;
    font-size: 12px;
    line-height: 1.6;
    color: var(--ii-muted);
}

.ii-ai-risk-head,
.ii-ai-action-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 10px;
}

.ii-ai-sev {
    flex: 0 0 auto;
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 9.5px;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    background: #EEF2F7;
    color: var(--ii-muted);
}

.ii-ai-sev.high {
    background: #FEF2F2;
    color: var(--ii-critical);
}

.ii-ai-sev.medium {
    background: #FFF7ED;
    color: var(--ii-warning);
}

.ii-ai-sev.low {
    background: #ECFDF5;
    color: var(--ii-success);
}

.ii-ai-actions {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.ii-ai-fields {
    margin: 10px 0 0;
    display: grid;
    grid-template-columns: 132px 1fr;
    gap: 6px 12px;
    font-size: 11.5px;
    line-height: 1.55;
}

.ii-ai-fields dt {
    font-size: 9.5px;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #94A3B8;
    padding-top: 2px;
}

.ii-ai-fields dd {
    margin: 0;
    color: var(--ii-text);
}

.ii-ai-suggest-label {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #94A3B8;
    margin: 6px 0 6px;
}

.ii-ai-answer {
    background: var(--ii-surface);
    border: 1px solid var(--ii-border);
    border-left: 3px solid var(--ii-navy);
    border-radius: var(--ii-radius);
    padding: 16px 20px;
    margin-top: 14px;
}

.ii-ai-answer-q {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.02em;
    color: var(--ii-muted);
    margin-bottom: 9px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--ii-border);
}

/* ------------------------------------------------------------------ */
/* Streamlit widgets                                                   */
/* ------------------------------------------------------------------ */

[data-testid="stFileUploaderDropzone"] {
    background: #F8FAFC;
    border: 1.5px dashed #CBD5E1;
    border-radius: 10px;
    padding: 12px;
    transition: border-color 0.15s ease, background 0.15s ease;
}

[data-testid="stFileUploaderDropzone"]:hover {
    border-color: var(--ii-primary);
    background: #F5F9FF;
}

[data-testid="stFileUploaderDropzone"] button {
    min-height: 34px;
    font-size: 11.5px;
    padding: 0.3rem 0.75rem;
}

[data-testid="stFileUploaderDropzoneInstructions"] {
    font-size: 11px;
}

[data-testid="stFileUploaderDropzoneInstructions"] span {
    font-size: 11px;
    color: #64748B;
}

[data-testid="stDataFrame"] {
    border: 1px solid var(--ii-border);
    border-radius: 10px;
    overflow: hidden;
}

[data-testid="stExpander"] {
    background: var(--ii-surface);
    border: 1px solid var(--ii-border);
    border-radius: 10px;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    border-bottom: 1px solid var(--ii-border);
}

.stTabs [data-baseweb="tab"] {
    padding: 8px 14px;
    font-size: 12.5px;
    font-weight: 600;
    color: var(--ii-muted);
}

.stTabs [aria-selected="true"] {
    color: var(--ii-primary);
}

[data-testid="stCaptionContainer"] {
    color: #94A3B8;
}

[data-testid="stCaptionContainer"] p {
    font-size: 10.5px;
}

/* ------------------------------------------------------------------ */
/* Quick Start and demo data                                           */
/* ------------------------------------------------------------------ */

.ii-scenario-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 10px;
    margin: 0 0 18px;
}

.ii-scenario-card {
    background: #F8FAFC;
    border: 1px solid var(--ii-border);
    border-radius: 10px;
    padding: 12px 13px;
}

.ii-scenario-head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 8px;
    margin-bottom: 5px;
}

.ii-scenario-name {
    font-size: 12px;
    font-weight: 700;
    color: var(--ii-text);
}

.ii-scenario-code {
    flex: 0 0 auto;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.04em;
    color: #94A3B8;
    white-space: nowrap;
}

.ii-scenario-text {
    margin: 0;
    font-size: 11px;
    line-height: 1.5;
    color: var(--ii-muted);
}

.ii-demo-notes {
    display: grid;
    grid-template-columns: 1fr;
    gap: 7px;
    margin-top: 16px;
    padding: 14px 16px;
    border-radius: 10px;
    background: #EFF6FF;
    border: 1px solid #BFDBFE;
}

.ii-demo-note {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    font-size: 11.5px;
    line-height: 1.55;
    color: #1E40AF;
}

.ii-demo-note svg {
    flex: 0 0 14px;
    margin-top: 2px;
    color: var(--ii-primary);
}

/* ------------------------------------------------------------------ */
/* Responsive                                                          */
/* ------------------------------------------------------------------ */

@media (max-width: 1100px) {
    .ii-hero {
        grid-template-columns: 1fr;
        padding: 2rem;
    }

    .ii-hero h1 {
        font-size: 34px;
    }

    .ii-hero-panel {
        max-width: 460px;
    }

    .ii-steps {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .ii-road {
        grid-template-columns: 1fr;
    }
}

@media (max-width: 1000px) {
    .ii-report-grid {
        grid-template-columns: 1fr;
    }

    .ii-sheet-grid,
    .ii-detail-grid {
        grid-template-columns: 1fr;
    }

    .ii-scenario-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .ii-metrics {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
}

@media (max-width: 900px) {
    [data-testid="stHorizontalBlock"]:has(.ii-action-icon) {
        flex-direction: column;
        gap: 1rem;
    }

    [data-testid="stHorizontalBlock"]:has(.ii-action-icon)
        > [data-testid="stColumn"] {
        width: 100% !important;
        flex: 1 1 100% !important;
    }
}

@media (max-width: 700px) {
    .block-container {
        padding-left: 1.1rem;
        padding-right: 1.1rem;
        padding-top: 1.3rem;
    }

    .ii-hero {
        padding: 1.5rem;
    }

    .ii-hero h1 {
        font-size: 29px;
    }

    .ii-steps,
    .ii-rules,
    .ii-road,
    .ii-scenario-grid,
    .ii-metrics {
        grid-template-columns: 1fr;
    }

    div[data-testid="stVerticalBlock"]:has(.ii-action-icon):not(
            :has(div[data-testid="stVerticalBlock"])) {
        min-height: 0;
    }

    .ii-page-head {
        flex-direction: column;
    }
}
</style>
"""


def inject_global_styles() -> None:
    """Inject the shared stylesheet once per script run."""

    st.markdown(_CSS, unsafe_allow_html=True)


def sync_document_language() -> None:
    """Mirror the active language onto ``<html lang>``.

    Several design-system labels are rendered with ``text-transform: uppercase``
    (eyebrows, badges, KPI labels). CSS upper-casing is locale-sensitive: it uses
    the element's language, which Streamlit hard-codes to ``lang="en"`` on the
    document element. In English that is harmless, but Turkish has a dotted and a
    dotless i, so ``Örnek Veri`` was displayed as ``ÖRNEK VERI`` instead of
    ``ÖRNEK VERİ``.

    The fix is to keep the design exactly as it is and tell the browser which
    language the text is actually in. Setting ``document.documentElement.lang``
    makes every existing ``text-transform: uppercase`` rule apply Turkish casing
    rules, so no selector has to be touched and the English rendering is
    unchanged (``en`` and ``tr`` differ only for i/ı).

    Streamlit renders HTML through React, which drops ``<script>`` tags injected
    via ``st.markdown``/``st.html``, so the attribute is set from a script-only,
    same-origin iframe that reaches into the parent document. The iframe is used
    only for this side effect and renders no visible content.
    """

    _render_html_frame(_language_sync_script(get_language()))


def _language_sync_script(language: str) -> str:
    """Return the script that mirrors ``language`` onto ``<html lang>``."""

    return (
        '<script>\n'
        "    (function () {\n"
        "        try {\n"
        '            var doc = window.parent.document;\n'
        f'            if (doc.documentElement.getAttribute("lang") !== "{language}") {{\n'
        f'                doc.documentElement.setAttribute("lang", "{language}");\n'
        "            }\n"
        "        } catch (error) {\n"
        "            /* The parent is cross-origin in some deployments; the UI must\n"
        "               never break just because the attribute could not be set. */\n"
        "        }\n"
        "    })();\n"
        "</script>"
    )


def _render_html_frame(html: str) -> None:
    """Render script-only HTML without depending on the Streamlit version.

    ``st.iframe`` only exists from Streamlit 1.56 onwards. The project supports
    ``streamlit>=1.53`` (verified on 1.53 and 1.67), so a deployment can resolve
    an older release where calling ``st.iframe`` would raise ``AttributeError``.
    Streamlit Cloud has also failed on this call, so the older, still-supported
    ``st.components.v1.html`` is kept as a fallback.

    Both paths are invisible: ``st.iframe`` rejects a height of ``0``, so the
    smallest accepted value is used there, while the components API accepts
    ``0``. The CSS layer also removes any border or background from the frame.
    """

    iframe = getattr(st, "iframe", None)
    if callable(iframe):
        iframe(html, height=1)
        return

    import streamlit.components.v1 as components  # noqa: PLC0415 - version fallback

    components.html(html, height=0, scrolling=False)
