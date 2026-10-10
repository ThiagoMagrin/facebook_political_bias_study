# Eight sensitivity checks starting from the exact FINAL specification.
# Run 01_build_dataset.py (cutoffs 50 and 25), then 11_prepare_robustness.py.
# No existing model outputs are overwritten; all results are checkpointed.
suppressPackageStartupMessages({
  library(readr); library(dplyr); library(glmmTMB)
  library(broom.mixed); library(performance)
})
.args <- commandArgs(trailingOnly = FALSE)
.file <- sub("^--file=", "", .args[grep("^--file=", .args)])
source(file.path(if (length(.file)) dirname(normalizePath(.file[1])) else getwd(),
                 "_common.R"))
OUT <- file.path(RES, "consolidated_robustness")
dir.create(OUT, showWarnings = FALSE, recursive = TRUE)
dir.create(file.path(OUT, "fits"), showWarnings = FALSE)
options(width = 130)
capture.output(sessionInfo(), file = file.path(OUT, "sessionInfo.txt"))

d <- read_csv(file.path(DATA, "analysis_dataset.csv"), show_col_types = FALSE)
dt <- read_csv(file.path(DATA, "analysis_dataset_timed.csv"), show_col_types = FALSE)
dl <- read_csv(file.path(DATA, "analysis_dataset_linkout.csv"), show_col_types = FALSE)
d25 <- read_csv(file.path(DATA, "analysis_dataset_min25.csv"), show_col_types = FALSE)
manifest <- read_csv(file.path(OUT, "sample_manifest.csv"), show_col_types = FALSE)
specs <- list(final = list(data = d, crp = TRUE),
              no_crp = list(data = d, crp = FALSE),
              bp2 = list(data = filter(d, author_bp_links >= 2), crp = TRUE),
              bp5 = list(data = filter(d, author_bp_links >= 5), crp = TRUE),
              window = list(data = filter(dt, within_twitter_window), crp = TRUE),
              linkout = list(data = dl, crp = TRUE),
              min25 = list(data = d25, crp = TRUE),
              min100 = list(data = filter(d, totalReactions >= 100), crp = TRUE))

cont <- c("content_leaning", "content_extremity", "publisher_leaning",
          "publisher_extremity", "rph_delta", "toxicity", "reaction_score",
          "log_total_reactions", "log_author_links", TOPICS)
coef_rows <- list(); fit_rows <- list(); random_rows <- list(); scale_rows <- list()
warning_rows <- list(); vif_rows <- list()

for (id in names(specs)) {
  spec <- specs[[id]]
  dat <- spec$data
  n <- nrow(dat)
  expected <- manifest %>% filter(.data$id == .env$id)
  stopifnot(nrow(expected) == 1, n == expected$N,
            n_distinct(dat$account_name) == expected$pages,
            n_distinct(dat$collection_name) == expected$links)
  vars <- if (spec$crp) cont else setdiff(cont, "reaction_score")
  required <- c(vars, "consensus_index", "account_name", "collection_name")
  stopifnot(all(complete.cases(dat[, required])),
            all(dat$consensus_index >= 0 & dat$consensus_index <= 1))
  sds <- vapply(dat[vars], sd, numeric(1))
  means <- vapply(dat[vars], mean, numeric(1))
  stopifnot(all(is.finite(sds)), all(sds > 0))
  ds <- dat %>%
    mutate(ci = (consensus_index * (n - 1) + 0.5) / n) %>%
    mutate(across(all_of(vars), ~ as.numeric(scale(.))))
  rhs <- if (spec$crp) FINAL else sub(" + reaction_score", "", FINAL, fixed = TRUE)
  f <- as.formula(paste("ci ~", rhs, "+", TOPSTR, "+", RE))
  warnings <- character()
  started <- proc.time()[["elapsed"]]
  cat(sprintf("Fitting %s: %s; N=%d, pages=%d, links=%d\n", id,
              expected$specification, n, expected$pages, expected$links))
  flush.console()
  m <- withCallingHandlers(glmmTMB(f, data = ds, family = beta_family()),
                           warning = function(w) {
                             warnings <<- c(warnings, conditionMessage(w))
                             invokeRestart("muffleWarning")
                           })
  elapsed <- proc.time()[["elapsed"]] - started
  # Optimizer code and positive-definite Hessian are distinct checks.
  opt_ok <- identical(as.integer(m$fit$convergence), 0L)
  hess_ok <- isTRUE(m$sdr$pdHess)
  cf <- tidy(m, effects = "fixed", conf.int = TRUE, conf.method = "Wald")
  finite_ok <- all(is.finite(cf$estimate)) && all(is.finite(cf$std.error)) &&
    all(is.finite(cf$conf.low)) && all(is.finite(cf$conf.high))
  if (!opt_ok || !hess_ok || !finite_ok) {
    # Preserve the failed attempt; do not silently publish its coefficients.
    saveRDS(m, file.path(OUT, "fits", paste0(id, "_failed.rds")))
    stop(sprintf("%s failed diagnostics: optimizer=%s, pdHess=%s, finite=%s",
                 id, opt_ok, hess_ok, finite_ok))
  }
  saveRDS(m, file.path(OUT, "fits", paste0(id, ".rds")))
  cf <- cf %>% mutate(id = id, specification = expected$specification,
                      predictor_sd = unname(sds[term]),
                      raw_estimate = estimate / predictor_sd,
                      raw_conf_low = conf.low / predictor_sd,
                      raw_conf_high = conf.high / predictor_sd)
  coef_rows[[id]] <- cf
  scale_rows[[id]] <- tibble(id = id, term = vars, mean = unname(means),
                            sd = unname(sds))
  # The definition and approximation are explicit, and recorded with versions.
  r2_warnings <- character()
  r2 <- tryCatch(withCallingHandlers(
    performance::r2_nakagawa(m, approximation = "lognormal"),
    warning = function(w) {r2_warnings <<- c(r2_warnings, conditionMessage(w))
                          warnings <<- c(warnings, paste0("R2: ", conditionMessage(w)))
                          invokeRestart("muffleWarning")}), error = function(e) NULL)
  if (is.null(r2) || !all(c("R2_marginal", "R2_conditional") %in% names(r2))) {
    r2m <- r2c <- NA_real_
  } else {
    r2m <- as.numeric(r2$R2_marginal); r2c <- as.numeric(r2$R2_conditional)
  }
  r2_valid <- all(is.finite(c(r2m, r2c))) && all(c(r2m, r2c) >= 0) &&
    all(c(r2m, r2c) <= 1) && !any(grepl("not reliable|negative", r2_warnings))
  if (!r2_valid) r2m <- r2c <- NA_real_
  vc <- VarCorr(m)$cond
  re <- bind_rows(lapply(names(vc), function(g) {
    x <- vc[[g]]
    tibble(id = id, group = g, sd_intercept = sqrt(x[1, 1]),
           sd_toxicity = sqrt(x[2, 2]),
           intercept_slope_correlation = attr(x, "correlation")[1, 2])
  }))
  random_rows[[id]] <- re
  vifs <- tryCatch(as.data.frame(performance::check_collinearity(m)),
                   error = function(e) NULL)
  if (!is.null(vifs)) vif_rows[[id]] <- tibble(id = id, term = vifs$Term, VIF = vifs$VIF)
  grad <- tryCatch(max(abs(m$obj$gr(m$fit$par))), error = function(e) NA_real_)
  pearson <- residuals(m, type = "pearson")
  fit_rows[[id]] <- tibble(id = id, specification = expected$specification,
    N = nobs(m), pages = expected$pages, links = expected$links,
    optimizer_code = m$fit$convergence, optimizer_message = m$fit$message,
    pdHess = hess_ok, finite_coefficients_and_CIs = finite_ok,
    max_abs_gradient = grad, AIC = AIC(m), BIC = BIC(m), logLik = as.numeric(logLik(m)),
    R2_marginal = r2m, R2_conditional = r2c, R2_valid = r2_valid,
    pearson_residual_mean = mean(pearson), pearson_residual_sd = sd(pearson),
    min_random_effect_sd = min(c(re$sd_intercept, re$sd_toxicity)),
    max_abs_intercept_slope_correlation = max(abs(re$intercept_slope_correlation)),
    elapsed_seconds = elapsed, formula = paste(deparse(f), collapse = " "))
  warning_rows[[id]] <- tibble(id = rep(id, length(warnings)), warning = warnings)
  # Checkpoint after every successful fit; rerunning reproduces all rows.
  write_csv(bind_rows(coef_rows), file.path(OUT, "all_coefficients.csv"))
  write_csv(bind_rows(fit_rows), file.path(OUT, "model_diagnostics.csv"))
  write_csv(bind_rows(random_rows), file.path(OUT, "random_effects.csv"))
  write_csv(bind_rows(scale_rows), file.path(OUT, "predictor_scaling.csv"))
  write_csv(bind_rows(warning_rows), file.path(OUT, "warnings.csv"))
  write_csv(bind_rows(vif_rows), file.path(OUT, "vif.csv"))
  capture.output(summary(m), file = file.path(OUT, paste0("summary_", id, ".txt")))
  cat(sprintf("  OK: optimizer=%d, pdHess=%s, AIC=%.2f, elapsed=%.1fs\n",
              m$fit$convergence, hess_ok, AIC(m), elapsed))
  flush.console()
}

coefs <- bind_rows(coef_rows)
fits <- bind_rows(fit_rows)
results <- bind_rows(lapply(names(specs), function(k) {
  delta <- coefs %>% filter(id == k, term == "rph_delta")
  tox <- coefs %>% filter(id == k, term == "toxicity")
  fit <- fits %>% filter(id == k)
  stopifnot(nrow(delta) == 1, nrow(tox) == 1)
  tibble(id = k, specification = fit$specification,
         beta_delta = delta$estimate, delta_low = delta$conf.low, delta_high = delta$conf.high,
         beta_tox = tox$estimate, tox_low = tox$conf.low, tox_high = tox$conf.high,
         p_delta = delta$p.value, p_tox = tox$p.value,
         delta_sd = delta$predictor_sd, tox_sd = tox$predictor_sd,
         raw_beta_delta = delta$raw_estimate, raw_beta_tox = tox$raw_estimate,
         N = fit$N, pages = fit$pages, links = fit$links,
         optimizer_code = fit$optimizer_code, pdHess = fit$pdHess)
}))
stopifnot(nrow(results) == 8)
write_csv(results, file.path(OUT, "consolidated_robustness.csv"))

# Verify reproduction of all 20 fixed-effect estimates and Wald CI endpoints.
old <- read_csv(file.path(RES, "model_coefficients.csv"), show_col_types = FALSE) %>%
  filter(model == "C") %>% select(term, old_estimate = estimate,
                                   old_low = conf.low, old_high = conf.high)
baseline <- coefs %>% filter(id == "final") %>%
  select(term, estimate, conf.low, conf.high) %>% inner_join(old, by = "term") %>%
  mutate(estimate_difference = estimate - old_estimate,
         low_difference = conf.low - old_low, high_difference = conf.high - old_high)
write_csv(baseline, file.path(OUT, "baseline_reproduction.csv"))
stopifnot(nrow(baseline) == nrow(old),
          max(abs(baseline$estimate_difference)) < 1e-3,
          max(abs(baseline$low_difference)) < 1e-3,
          max(abs(baseline$high_difference)) < 1e-3)
capture.output(sessionInfo(), file = file.path(OUT, "sessionInfo.txt"))
print(as.data.frame(results), row.names = FALSE, digits = 5)
cat("\nAll eight fits passed optimizer, Hessian and finite-coefficient checks.\n")
