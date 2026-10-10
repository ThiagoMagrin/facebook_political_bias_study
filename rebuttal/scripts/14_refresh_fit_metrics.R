# Recalculate supplemental fit metrics from checkpointed models, without refits.
# Useful when performance/insight versions change. Invalid R2 is never reported.
suppressPackageStartupMessages({library(readr); library(dplyr); library(glmmTMB); library(performance)})
.args <- commandArgs(trailingOnly = FALSE)
.file <- sub("^--file=", "", .args[grep("^--file=", .args)])
source(file.path(if (length(.file)) dirname(normalizePath(.file[1])) else getwd(), "_common.R"))
OUT <- file.path(RES, "consolidated_robustness")
old <- read_csv(file.path(OUT, "model_diagnostics.csv"), show_col_types = FALSE)
legacy <- file.path(OUT, "model_diagnostics_before_metric_refresh.csv")
if (!file.exists(legacy)) write_csv(old, legacy)
old$R2_valid <- FALSE
warnings <- list()
for (id in old$id) {
  m <- readRDS(file.path(OUT, "fits", paste0(id, ".rds")))
  w <- character()
  r2 <- tryCatch(withCallingHandlers(
    performance::r2_nakagawa(m, approximation = "lognormal"),
    warning = function(x) {w <<- c(w, conditionMessage(x)); invokeRestart("muffleWarning")}),
    error = function(e) {w <<- c(w, conditionMessage(e)); NULL})
  vals <- if (!is.null(r2) && all(c("R2_marginal", "R2_conditional") %in% names(r2)))
    c(as.numeric(r2$R2_marginal), as.numeric(r2$R2_conditional)) else c(NA_real_, NA_real_)
  valid <- all(is.finite(vals)) && all(vals >= 0 & vals <= 1) &&
    !any(grepl("not reliable|negative", w))
  if (!valid) vals[] <- NA_real_
  idx <- which(old$id == id)
  old$R2_marginal[idx] <- vals[1]; old$R2_conditional[idx] <- vals[2]
  old$R2_valid[idx] <- valid
  warnings[[id]] <- tibble(id = rep(id, length(w)), warning = w)
  cat(sprintf("%s: R2_valid=%s; marginal=%.6f, conditional=%.6f\n", id, valid, vals[1], vals[2]))
}
write_csv(old, file.path(OUT, "model_diagnostics.csv"))
write_csv(bind_rows(warnings), file.path(OUT, "metric_refresh_warnings.csv"))
capture.output(sessionInfo(), file = file.path(OUT, "metric_refresh_sessionInfo.txt"))
