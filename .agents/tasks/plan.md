# Implementation Plan

## Project context

- Branch: `master` (currently on `me` — coder must `git checkout master` first)
- Python: 3.11, no test framework, verify with `python -c "import main"`
- Commit with specific `git add <files>` only; English commit messages

---

## Commit 1 — main.py logic and config fixes (T7–T14)

- [ ] 1. Add `SIGNOS` list and `LOTTERIES` constant to `src/core/config.py`.
      Append `SIGNOS: list = ["ARI","TAU","GEM","CAN","LEO","VIR","LIB","ESC","SAG","CAP","ACU","PIS"]`
      and `LOTTERIES: list = ["ASTRO SOL", "ASTRO LUNA"]` as class attributes
      in the `Settings` class, inside the `# LOTTERY CONFIG` section.
      Update `get_training_profile()` to accept an optional `mode: str = None` parameter:
      use `mode` when provided, otherwise fall back to `os.getenv("TRAINING_MODE", "prod").lower()`.
      Files: `src/core/config.py`
      Verify: `python -c "from src.core.config import settings; print(settings.SIGNOS); print(settings.LOTTERIES)"`
      — both lists printed without error.

- [ ] 2. Fix T7 target alignment in `main.py`.
      In `ejecutar_entrenamiento`, change:
        `df_loteria = df_loteria.tail(len(X_df))`
      to:
        `df_loteria = df_loteria.loc[X_df.index]`
      (This is the line right after `X_df = X_df.replace([np.inf, -np.inf], np.nan).dropna()`.)
      Files: `main.py`
      Verify: `python -c "import main"` — no import error.

- [ ] 3. Fix T8 fixed-category encoding in `main.py`.
      In the preprocessing block of `ejecutar_entrenamiento`, replace:
        `df["series"] = df["series"].astype(str).str.upper().astype("category").cat.codes`
      with:
        `df["series"] = pd.Categorical(df["series"].astype(str).str.upper(), categories=settings.SIGNOS).codes`
      Files: `main.py`
      Verify: `python -c "import main"` — no import error.

- [ ] 4. Fix T9 double-sync in `main.py`.
      Add `sincronizar: bool = True` parameter to `ejecutar_entrenamiento`.
      Wrap the `synchronize_database` call block (the `try/except` that calls `synchronize_database`)
      with `if sincronizar:`.
      In `ejecutar_pipeline_completo`, change the lambda:
        `lambda: ejecutar_entrenamiento()`
      to:
        `lambda: ejecutar_entrenamiento(sincronizar=False)`
      Files: `main.py`
      Verify: `python -c "import main"` — no import error.

- [ ] 5. Fix T10 staleness warning in `main.py`.
      After the `df_loteria = df_loteria.sort_values("fecha").reset_index(drop=True)` line
      inside the per-lottery training loop, add:
      ```python
      ultima_fecha = df_loteria["fecha"].max()
      dias_sin_datos = (pd.Timestamp.now() - ultima_fecha).days
      if dias_sin_datos > 7:
          logger.warning(f"{nombre_loteria}: datos desactualizados — última fecha {ultima_fecha.date()} ({dias_sin_datos} días)")
      ```
      Files: `main.py`
      Verify: `python -c "import main"` — no import error.

- [ ] 6. Fix T11 `conn.close()` not in finally in `main.py`.
      In `ejecutar_entrenamiento`, refactor the Neon loading block so the
      `conn.close()` call is inside a `finally` block:
      ```python
      conn = NeonConnection()
      try:
          repository = LotteriaRepository(conn)
          # ... existing frames/concat logic ...
      finally:
          conn.close()
      ```
      Files: `main.py`
      Verify: `python -c "import main"` — no import error.

- [ ] 7. Fix T12 hardcoded lottery lists in `main.py`.
      Replace both occurrences of `loterias_neon = ["ASTRO SOL", "ASTRO LUNA"]`
      (one in the Neon loading block of `ejecutar_entrenamiento`) with:
        `loterias_neon = list(settings.LOTTERIES)`
      Files: `main.py`
      Verify: `python -c "import main"` — no import error.

- [ ] 8. Fix T13 `os.environ` mutation in `main.py`.
      In `ejecutar_entrenamiento`, replace:
      ```python
      if modo:
          os.environ["TRAINING_MODE"] = modo.lower()
          settings.ensure_directories()
      modo_activo = os.getenv("TRAINING_MODE", "prod").upper()
      ```
      with:
      ```python
      modo_activo = (modo.lower() if modo else os.getenv("TRAINING_MODE", "prod")).upper()
      ```
      Then replace:
        `profile = settings.get_training_profile()`
      (inside `training_simple.py`'s `entrenar_modelos_por_loteria`) — that file
      reads env itself, so no change needed there.
      The only change in `main.py` for T13: remove the `os.environ` mutation.
      Files: `main.py`
      Verify: `python -c "import main"` — no import error.

- [ ] 9. Fix T14 — cleanup in `main.py`.
      a) Remove the unused import: `from src.api.superastro_scraper import SuperAstroScraper`
      b) Add a `log_y_mostrar(msg: str) -> None` helper right after the logger line:
         ```python
         def log_y_mostrar(msg: str) -> None:
             logger.info(msg)
             print(msg)
         ```
      c) Replace the duplicated `logger.info(…) + print(…)` pairs throughout
         `ejecutar_limpieza`, `ejecutar_actualizacion`, `ejecutar_entrenamiento`,
         `ejecutar_prediccion` with calls to `log_y_mostrar(…)` — only for the
         section header lines (the `"="*70` separator lines and the step title).
         Leave other prints (user-facing output like ✅/❌) as plain `print`.
      d) Update `mostrar_configuracion` to replace `settings.FIND_LOTERY` display
         with `settings.LOTTERIES` and change the label from `"Lotería:"` to
         `"Loterías:"`:
         ```python
         print(f"Loterías:       {settings.LOTTERIES}")
         ```
      Files: `main.py`
      Verify: `python -c "import main"` — no import error.

- [ ] 10. Fix T8 and T11 in `src/utils/prediction.py`.
       a) T8: In `predecir_para_loteria`, replace:
          ```python
          y_series = (
              df_loteria["series"]
              .astype(str).str.upper()
              .astype("category").cat.codes.values
          )
          ```
          with:
          ```python
          y_series = pd.Categorical(
              df_loteria["series"].astype(str).str.upper(),
              categories=settings.SIGNOS
          ).codes
          ```
       b) T7: Change `df_loteria = df_loteria.tail(len(X_train_df))` to
          `df_loteria = df_loteria.loc[X_train_df.index]`
       c) T11: In `main()`, wrap `conn.close()` in a `finally` block (same
          pattern as the fix in `main.py` item 6 above).
       d) T12: Replace `loterias_neon = ["ASTRO SOL", "ASTRO LUNA"]` with
          `loterias_neon = list(settings.LOTTERIES)`
       Files: `src/utils/prediction.py`
       Verify: `python -c "from src.utils.prediction import main"` — no import error.

- [ ] 11. Add `sign_mapping` to payload in `src/utils/save_training.py` (T8).
       In `guardar_modelo_si_mejora`, add `"sign_mapping": {i: s for i, s in enumerate(settings.SIGNOS)}`
       to the `payload` dict, right after `"feature_names": FEATURE_COLUMNS`.
       Also add the import at the top of the file if not already there.
       Files: `src/utils/save_training.py`
       Verify: `python -c "from src.utils.save_training import guardar_modelo_si_mejora"` — no import error.

- [ ] 12. Commit Group 1.
       ```
       git checkout master
       git add src/core/config.py main.py src/utils/prediction.py src/utils/save_training.py
       git commit -m "fix: T7-T14 main.py logic and config improvements"
       ```
       Verify: `python -c "import main"` — clean import; `python main.py --help` shows usage.

---

## Commit 2 — Training validation improvements (T15, T16)

- [ ] 13. Replace random split with chronological split in `src/utils/training_simple.py` (T15).
       In `_evaluar_individuo`, remove the `train_test_split` call and replace with:
       ```python
       n = len(X)
       split_idx = int(n * (1 - test_size))
       X_tr, X_te = X[:split_idx], X[split_idx:]
       ym_tr, ym_te = y_miles[:split_idx],    y_miles[split_idx:]
       yc_tr, yc_te = y_centenas[:split_idx], y_centenas[split_idx:]
       yd_tr, yd_te = y_decenas[:split_idx],  y_decenas[split_idx:]
       yu_tr, yu_te = y_unidades[:split_idx], y_unidades[split_idx:]
       ys_tr, ys_te = y_series[:split_idx],   y_series[split_idx:]
       ```
       Remove the `random_state=seed` parameter from this split (seed is no longer
       needed for the split itself, but keep `seed` in the individual for RF
       `random_state` in `_entrenar_rf`).
       Also remove the `from sklearn.model_selection import train_test_split` import
       if it is no longer used anywhere else in the file.
       Files: `src/utils/training_simple.py`
       Verify: `python -c "from src.utils.training_simple import entrenar_modelos_por_loteria"` — no import error.

- [ ] 14. Add baseline accuracy log in `src/utils/training_simple.py` (T16).
       After the `# ── Resultado final` block (just before the `# ── Guardar en memoria IA` block),
       add baseline calculation and logging:
       ```python
       from collections import Counter
       # Baseline: most-frequent-class accuracy for result digits
       baseline_result = max(Counter(y_result % 10).values()) / len(y_result)  # approx via units digit
       baseline_series = max(Counter(y_series).values()) / len(y_series)
       if verbose:
           print(f"  Modelo result: {mejor_acc_result:.2%} | Línea base: {baseline_result:.2%}")
           print(f"  Modelo series: {mejor_acc_series:.2%} | Línea base: {baseline_series:.2%}")
       ```
       Note: `y_result` and `y_series` are available in the function scope at that point.
       Files: `src/utils/training_simple.py`
       Verify: `python -c "from src.utils.training_simple import entrenar_modelos_por_loteria"` — no import error.

- [ ] 15. Commit Group 2.
       ```
       git add src/utils/training_simple.py
       git commit -m "fix: T15-T16 chronological split and baseline accuracy logging"
       ```
       Verify: `python -c "from src.utils.training_simple import entrenar_modelos_por_loteria"` — clean.

---

## Commit 3 — Documentation and dependencies (T17, T18, T19, T21, T22)

- [ ] 16. Update `Docs/ARCHITECTURE.md` (T17, T18).
       a) T18: In the "Flujo de datos" section, change `sincronizar_con_neon()` → `synchronize_database()`.
       b) T18: In the directory tree, the following files DO exist (confirmed in filesystem):
          `mutation.py`, `training.py`, `batch_prediction.py`, `training_visualizer.py`, `src/excel/`.
          Add a note after each of those lines: `# presente — uso interno / legacy`
          so it's clear they exist but are not part of the main pipeline.
       c) T17: In the `IA_models/` section of the directory tree and in the
          "Modelos guardados" section, add a note:
          `# Solo existen modelos para ASTRO LUNA. ASTRO SOL aún no tiene modelos entrenados.`
       Files: `Docs/ARCHITECTURE.md`
       Verify: visual review — no broken markdown.

- [ ] 17. Update `README.md` (T17, T19, T21).
       a) T19: After the `# Sistema de Predicción de Lotería` title line, add:
          ```markdown
          ## ⚠️ Aviso importante
          
          Los modelos entrenados actualmente (`IA_models/`) cubren **solo ASTRO LUNA**.
          ASTRO SOL no tiene modelos generados todavía; ejecutar `--predecir` o `--entrenar`
          sin filtro intentará ambas loterías, pero solo ASTRO LUNA producirá resultados válidos.
          ```
       b) T21: Add a `## Uso con Docker` section before `## Documentación`:
          ```markdown
          ## Uso con Docker
          
          ```bash
          # Construir la imagen
          docker build -t lotery-prediction .
          
          # Ejecutar el pipeline completo
          docker run --env-file .env lotery-prediction python main.py
          
          # Ejecutar solo sincronización
          docker run --env-file .env lotery-prediction python main.py --actualizar
          
          # Con docker-compose (incluye scheduler)
          docker-compose up lottery-system
          docker-compose up lottery-scheduler
          ```
          ```
       c) T17: In the `Resultados actuales` section, add a note below the table:
          `> Nota: solo ASTRO LUNA tiene modelos entrenados. ASTRO SOL aún no dispone de datos suficientes en `IA_models/`.`
       Files: `README.md`
       Verify: visual review — no broken markdown.

- [ ] 18. Pin all `requirements.txt` dependencies to exact installed versions (T22).
       Replace the file content with exact versions discovered from the environment
       (keep `>=` only for packages not installed: `scikit-optimize`, `schedule`, `APScheduler`
       — leave those with their current `>=` bound since they are not installed locally
       and are optional). Use these exact versions for installed packages:
       ```
       pandas==2.3.0
       numpy==2.2.4
       scikit-learn==1.7.0
       openpyxl==3.1.5
       joblib==1.5.1
       requests==2.32.3
       beautifulsoup4==4.13.4
       tqdm==4.67.1
       python-dotenv==1.2.1
       pydantic==2.12.5
       xgboost==3.2.0
       lightgbm==4.6.0
       psycopg2-binary==2.9.12
       # Optional — not installed in current environment
       scikit-optimize>=0.9.0
       schedule>=1.2.0
       APScheduler>=3.10.0
       ```
       Files: `requirements.txt`
       Verify: `python -c "import pandas, numpy, sklearn, openpyxl, joblib, requests, bs4, tqdm, dotenv, pydantic, xgboost, lightgbm, psycopg2"` — all import cleanly.

- [ ] 19. Commit Group 3.
       ```
       git add Docs/ARCHITECTURE.md README.md requirements.txt
       git commit -m "docs: T17-T19 T21-T22 update docs and pin dependencies"
       ```
       Verify: `git log --oneline -3` shows 3 new commits; `python main.py --help` still works.
