#!/bin/bash
set -e # Exit on error

# FIX: Ensure python tools can find the 'tools' module
export PYTHONPATH=$(pwd)

TICKER=$1
if [ -z "$TICKER" ]; then
    echo "Usage: ./orchestrator.sh <TICKER>"
    exit 1
fi

# Note: FINNHUB_API_KEY is loaded from .env by the python tool.

MODEL="flash"

echo "🚀 [System] Initializing TradingAgents 2.0 for $TICKER..."

# 0. Clean Workspace
rm -rf agency/data/* agency/reports/*
mkdir -p agency/data agency/reports

# ==============================================================================
# Phase 1: Professional Data Ingestion (Finnhub)
# ==============================================================================
echo "📊 [Phase 1] Fetching Real-Time Market Data (Finnhub API)..."
python3 tools/get_data_finnhub.py $TICKER

echo "✅ Data Ingestion Complete."

# ==============================================================================
# Phase 2: Distributed Analysis (Parallel)
# ==============================================================================
echo "🧠 [Phase 2] Launching Analyst Agents..."

COMMON_FLAGS="-m $MODEL --allowed-tools google_web_search web_fetch --approval-mode auto_edit"

# Tech Analyst
(cat .gemini/prompts/tech.md; echo; cat agency/data/market.json) | \
gemini $COMMON_FLAGS > agency/reports/tech.md &

# Fund Analyst
(cat .gemini/prompts/fund.md; echo; cat agency/data/financials.json) | \
gemini $COMMON_FLAGS > agency/reports/fund.md &

# Sent Analyst
(cat .gemini/prompts/sent.md; echo; cat agency/data/news.json) | \
gemini $COMMON_FLAGS > agency/reports/sent.md &

# Macro Analyst
(cat .gemini/prompts/macro.md; echo; cat agency/data/news.json) | \
gemini $COMMON_FLAGS > agency/reports/macro.md &

wait
echo "✅ Analyst Reports Generated."

# Combine Analyst Reports
cat agency/reports/tech.md agency/reports/fund.md agency/reports/sent.md agency/reports/macro.md > agency/reports/all_analyst_reports.md

# ==============================================================================
# Phase 3: Researcher Team (Parallel)
# ==============================================================================
echo "⚔️ [Phase 3] Launching Researcher Debate..."

# Dr. Bull
(cat .gemini/prompts/bull.md; echo; cat agency/reports/all_analyst_reports.md) | \
gemini $COMMON_FLAGS > agency/reports/bull_memo.md &

# Dr. Bear
(cat .gemini/prompts/bear.md; echo; cat agency/reports/all_analyst_reports.md) | \
gemini $COMMON_FLAGS > agency/reports/bear_memo.md &

wait
echo "✅ Research Memos Generated."

# ==============================================================================
# Phase 4: Decision Layer (Parallel)
# ==============================================================================
echo "⚖️ [Phase 4] Making Decisions..."

# CIO Debate
cat agency/reports/bull_memo.md agency/reports/bear_memo.md > agency/reports/debate_context.md
(cat .gemini/prompts/debate.md; echo; cat agency/reports/debate_context.md) | \
gemini $COMMON_FLAGS > agency/reports/signal.md &

# Risk Manager
(cat .gemini/prompts/risk.md; echo; cat agency/reports/tech.md agency/data/market.json) | \
gemini $COMMON_FLAGS > agency/reports/risk.md &

wait
echo "✅ Decisions Made."

# ==============================================================================
# Phase 5: Execution
# ==============================================================================
echo "📝 [Phase 5] Generating Trade Plan..."

(cat .gemini/prompts/trader.md; echo; cat agency/reports/signal.md agency/reports/risk.md) | \
gemini $COMMON_FLAGS > agency/reports/plan.md

# ==============================================================================
# Phase 6: Final Aggregation (Transfer to Master Gemini)
# ==============================================================================
echo "📦 [Final] Consolidating all reports for Fund Manager review..."

# Output all data to stdout with clear markers
echo -e "\n=== START OF DOSSIER ===\n"
echo "TARGET TICKER: $TICKER"
echo -e "\n--- TECHNICAL REPORT ---\n"
cat agency/reports/tech.md
echo -e "\n--- FUNDAMENTAL REPORT ---\n"
cat agency/reports/fund.md
echo -e "\n--- SENTIMENT REPORT ---\n"
cat agency/reports/sent.md
echo -e "\n--- MACRO REPORT ---\n"
cat agency/reports/macro.md
echo -e "\n--- BULL VS BEAR DEBATE ---\n"
cat agency/reports/signal.md
echo -e "\n--- RISK ASSESSMENT ---\n"
cat agency/reports/risk.md
echo -e "\n--- PROPOSED TRADE PLAN ---\n"
cat agency/reports/plan.md
echo -e "\n=== END OF DOSSIER ===\n"

echo "🏁 Backend process complete. Handing over to Fund Manager (Gemini Master)."