@echo off
rem Convert the Orca uncensored IQ3_XXS GGUF into a Strata pack (docs/ORCA.md, Windows version).
cd /d "C:\Users\kiyom\ai-models\Strata"
set "STRATA_GGUF_PY=C:\Users\kiyom\ai-models\Strata\third_party\llama.cpp\gguf-py"
set "SH1=C:\Users\kiyom\ai-models\Strata-data\orca\Qwen3.8-Flash-Next-Uncensored-IQ3_XXS-00001-of-00002.gguf"
set "SH2=C:\Users\kiyom\ai-models\Strata-data\orca\Qwen3.8-Flash-Next-Uncensored-IQ3_XXS-00002-of-00002.gguf"
if not exist "%SH1%" ( echo  [x] shard 1 not downloaded yet & exit /b 1 )
if not exist "%SH2%" ( echo  [x] shard 2 not downloaded yet & exit /b 1 )
if exist "C:\Users\kiyom\ai-models\Strata-data\packs\orca-iq3_xxs\tokenizer\vocab.json" ( echo  pack already converted & exit /b 0 )
echo  Converting (iq_pack --compat-bf16) ...
".venv\Scripts\python.exe" tools\iq_pack.py --gguf "%SH1%" --out "C:\Users\kiyom\ai-models\Strata-data\packs\orca-iq3_xxs" --compat-bf16
if errorlevel 1 ( echo  [x] conversion failed & exit /b 1 )
echo  [ok] converted
